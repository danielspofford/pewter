# """
# Entrypoint for the Puter CLI.
# """

import datetime
import os
import time
import uuid
from pathlib import Path

import boto3
import click
import dateutil.parser
from botocore.exceptions import ClientError

data_path = os.getenv("XDG_DATA_HOME") or "$HOME/.local/share"
data_path = Path(os.path.expandvars(data_path))
meta = {}


@click.command()
@click.option(
    "-i", "--instance-type", default="t2.micro", help="AWS instance type to use for EC2"
)
@click.option("-p", "--profile", help="AWS profile to use for all requests.")
@click.option("-p", "--profile", help="AWS profile to use for all requests.")
@click.option(
    "-r", "--region", default="us-east-1", help="The AWS region for EC2 operations."
)
@click.option(
    "-s",
    "--security-group-name",
    default="puter-v1",
    help="The AWS EC2 security group name. If it does not exist it will be created allowing tcp ingress on port 22 for SSH.",
)
@click.option(
    "-k",
    "--key-name",
    default="puter-v1",
    help="""The AWS EC2 keypair name.
    If the key does not yet exist:
        - locally and remotely: it will be created via AWS.
        - locally: the script will fail (if possible cp/mv the private key to Puters `private_keys` folder).
        - remotely: it will be imported into AWS.
""",
)
@click.option(
    "-a",
    "--ami",
    help="The AMI image ID to use. Defaults to the latest AWS Linux 2 AMI in the respective region. If the choosen AMI does not support Cloud-init, the EC2 user data may not be executed which will preevent the instance from self-terminating.",
)
@click.option(
    "-t",
    "--tag",
    default="puter",
    help="A tag applied to the EC2 instance. Used for uniquely identifying the instance internally.",
    required=True,
)
def cli(ami, security_group_name, instance_type, tag, key_name, region, profile):
    meta["tag"] = tag
    session_opts = profile and {"profile_name": profile, "region_name": region} or {}
    session = boto3.Session(**session_opts)
    ec2 = session.client("ec2")
    private_key_path = ensure_key_pair_exists(key_name, ec2)
    security_group_id = ensure_security_group_exists(security_group_name, ec2)
    instance_id = ensure_instance_exists(
        tag, instance_type, key_name, security_group_id, ami, ec2
    )
    public_dns_name = ensure_instance_connectable(instance_id, ec2)
    ssh_text = click.style(
        f"ssh \\\n" f"  -i {private_key_path} \\\n" f"  ec2-user@{public_dns_name}",
        fg="green",
    )
    rsync_text = click.style(
        f"rsync \\\n"
        f"  -Paq \\\n"
        f"  --exclude .git \\\n"
        f'  -e "ssh -i {private_key_path}" \\\n'
        f"  ~/SOME-PATH.txt \\\n"
        f"  ec2-user@{public_dns_name}:/tmp",
        fg="green",
    )
    click.echo(f"rsync command:\n{rsync_text}")
    click.echo(f"connect command:\n{ssh_text}")


def ensure_instance_connectable(instance_id, ec2):
    instances = ec2.describe_instances(InstanceIds=[instance_id])
    public_dns_name = instances["Reservations"][0]["Instances"][0]["PublicDnsName"]
    if public_dns_name == "":
        click.echo(f"polling for instance connectivity in 5 seconds")
        time.sleep(5)
        return ensure_instance_connectable(instance_id, ec2)
    else:
        return public_dns_name


def ensure_key_pair_exists(key_name, ec2):
    private_key_path = resolve_private_key_path(key_name)
    if private_key_path.is_file():
        quit()
        # TODO: ensure key_pair exists in aws
    else:
        create_key_pair(key_name, private_key_path, ec2)
    return private_key_path

def import_keypair(key_name):

def keypair_exists(key_name):
    ec2.describe_keypairs(KeyNames=[key_name])['KeyPairs'][0]['KeyFingerprint']




def create_key_pair(key_name, private_key_path, ec2):
    # TODO: fix key name
    try:
        with os.fdopen(
            os.open(private_key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
        ) as handle:
            outfile = open(private_key_path, "w")
            log({"type": "attempt_create_key_pair"})
            key_pair = ec2.create_key_pair(KeyName=key_name)
            click.ehcho(f"{key_pair}")
            log({"type": "create_key_pair_success"})
            click.secho("key pair created")
            KeyPairOut = str(key_pair["KeyMaterial"])
            outfile.write(KeyPairOut)
    except ClientError as e:
        if not e.response["Error"]["Code"] == "InvalidKeyPair.Duplicate":
            log({"type": "create_key_pair_failure"})
            click.secho(
                "failed creating keypair: %s" % e.response["Error"]["Code"], fg="red"
            )
            raise
        log({"type": f"create_key_pair_duplicate {e}"})


def resolve_private_key_path(key_name):
    private_keys_dir = data_path / f"puter/private_keys"
    os.makedirs(private_keys_dir, mode=0o700, exist_ok=True)
    return private_keys_dir / f"ec2-keypair-{key_name}.pem"


def ensure_instance_exists(tag, instance_type, key_name, security_group_id, ami, ec2):
    instance_id = instance_exists(tag, ec2)
    if not instance_id:
        instance_id = create_instance(
            tag, instance_type, key_name, security_group_id, ami, ec2
        )
    ensure_instance_has_security_group(instance_id, security_group_id, ec2)
    return instance_id


def create_instance(tag, instance_type, key_name, security_group_id, ami, ec2):
    log({"type": "attempt_run_instance"})
    user_data_file_name = os.path.join(
        os.path.dirname(__file__), "..", "data", "user-data.sh"
    )
    with open(user_data_file_name, "r") as file:
        image_id = ami or aws_linux_2_ami(ec2)
        instance_id = ec2.run_instances(
            ImageId=image_id,
            InstanceInitiatedShutdownBehavior="terminate",
            InstanceType=instance_type,
            KeyName=key_name,
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[security_group_id],
            TagSpecifications=[
                {"ResourceType": "instance", "Tags": [{"Key": "puter", "Value": tag}]}
            ],
            UserData=file.read(),
        )["Instances"][0]["InstanceId"]
        log({"type": "run_instance_success", "instance ID": instance_id})
        click.echo(f'instance created: {click.style(instance_id, fg="green")}')
        return instance_id


def aws_linux_2_ami(ec2):
    images = ec2.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["amzn2-ami-hvm-2.0.????????.?-x86_64-gp2"]},
            {"Name": "state", "Values": ["available"]},
        ],
    )["Images"]
    return max(images, key=lambda x: dateutil.parser.parse(x["CreationDate"]))[
        "ImageId"
    ]


def ensure_security_group_exists(security_group_name, ec2):
    try:
        log({"type": "attempt_create_security_group"})
        group_id = ec2.create_security_group(
            Description="puter SSH access", GroupName=security_group_name
        )["GroupId"]
        log({"type": "create_security_group success", "groupId": group_id})
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    "FromPort": 22,
                    "IpProtocol": "tcp",
                    "IpRanges": [{"CidrIp": "140.186.196.118/32"}],
                    "ToPort": 22,
                }
            ],
        )
        return group_id
    except ClientError as e:
        if not e.response["Error"]["Code"] == "InvalidGroup.Duplicate":
            log({"type": "create_security_group_failure"})
            click.secho(
                "failed creating security group: %s" % e.response["Error"], fg="red"
            )
            quit()
        log({"type": "create_security_group_duplicate"})
        ret = ec2.describe_security_groups(GroupNames=[security_group_name])
        return ret["SecurityGroups"][0]["GroupId"]


def instance_exists(tag, ec2):
    custom_filter = [{"Name": "tag:puter", "Values": [tag]}]
    instances = ec2.describe_instances(Filters=custom_filter)
    length = len(instances["Reservations"])
    if length > 0:
        return instances["Reservations"][0]["Instances"][0]["InstanceId"]
    return False


def ensure_instance_has_security_group(instance_id, security_group_id, ec2):
    instances = ec2.describe_instances(InstanceIds=[instance_id])
    length = len(instances["Reservations"])
    has_security_group = False
    if length > 0:
        security_groups = instances["Reservations"][0]["Instances"][0]["SecurityGroups"]
        for security_group in security_groups:
            if security_group["GroupId"] == security_group_id:
                log({"type": "instance_has_security_group"})
                has_security_group = True
                return True
    if not has_security_group:
        add_security_group_to_instance(instance_id, security_group_id, ec2)
        return True
    return False


def add_security_group_to_instance(instance_id, security_group_id, ec2):
    try:
        log({"type": "attempt_modify_instance_attribute"})
        ec2.modify_instance_attribute(
            InstanceId=instance_id, Groups=[security_group_id]
        )
        log({"type": "modify_instance_attribute_success"})
    except ClientError as e:
        click.secho("%s" % e.response["Error"], fg="red")


def log(data):
    log_dir = Path(data_path / "puter")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_path = log_dir / "log.txt"
    log_path.touch(mode=0o600)
    with open(log_path, "a") as file:
        meta["datetime"] = datetime.datetime.now().isoformat()
        d = {**data, **meta}
        file.write(f"{d}\n")


if __name__ == "__main__":
    cli()
