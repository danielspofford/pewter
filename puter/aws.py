import os
import time

import dateutil.parser
from botocore.exceptions import ClientError

from . import log


def authorize_security_group_ingress(group_id, ec2):
    ec2.authorize_security_group_ingress(
        GroupId=group_id,
        IpPermissions=[
            {
                "FromPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "140.186.196.118/32"}],
            }
        ],
    )
    log.data(
        {
            "type": "aws",
            "sub_type": "authorized security group ingress",
            "group_id": group_id,
        }
    )


def ensure_instance_has_security_group(instance, security_group_id, ec2):
    if not any(sg["GroupId"] == security_group_id for sg in instance["SecurityGroups"]):
        add_security_group_to_instance(instance["InstanceId"], security_group_id, ec2)
    return True


def add_security_group_to_instance(instance_id, security_group_id, ec2):
    groups = [security_group_id]
    ec2.modify_instance_attribute(InstanceId=instance_id, Groups=groups)
    log.data(
        {
            "type": "aws",
            "sub_type": "modified instance attribute",
            "instance_id": instance_id,
            "groups": groups,
        }
    )


def ensure_key_pair_exists(key_name, path, ec2):
    if not key_pair_exists(key_name, ec2):
        create_key_pair(key_name, path, ec2)


def key_pair_exists(key_name, ec2):
    try:
        ec2.describe_key_pairs(KeyNames=[key_name])
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidKeyPair.NotFound":
            return False
        else:
            log.exception(e)


def create_key_pair(key_name, path, ec2):
    key_pair = ec2.create_key_pair(KeyName=key_name)
    log.data({"type": "aws", "sub_type": "created key pair", "key_name": key_name})
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_EXCL, 0o600), "w") as outfile:
        key_material = str(key_pair["KeyMaterial"])
        outfile.write(key_material)
        log.data({"type": "local", "sub_type": "wrote key pair", "path": f"{path}"})


# TODO treat an instance that "exists" but is not in "running" as an exceptional case
def ensure_instance_exists(tag, instance_type, key_name, security_group_id, ami, ec2):
    instance = instance_exists(tag, ec2)
    if not instance:
        instance = create_instance(
            tag, instance_type, key_name, security_group_id, ami, ec2
        )
    return instance


def instance_exists(tag, ec2):
    custom_filter = [{"Name": "tag:puter", "Values": [tag]}]
    instances = ec2.describe_instances(Filters=custom_filter)
    length = len(instances["Reservations"])
    if length == 1:
        return instances["Reservations"][0]["Instances"][0]
    return False


def create_instance(tag, instance_type, key_name, security_group_id, ami, ec2):
    user_data_file_name = os.path.join(
        os.path.dirname(__file__), "..", "data", "user-data.sh"
    )
    with open(user_data_file_name, "r") as file:
        image_id = ami or aws_linux_2_ami(ec2)
        instance = ec2.run_instances(
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
        )["Instances"][0]
        log.data(
            {
                "type": "aws",
                "sub_type": "created instance",
                "instance_id": instance["InstanceId"],
            }
        )
        return instance


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


def poll_for_public_dns_name(instance_id, ec2):
    instances = ec2.describe_instances(InstanceIds=[instance_id])
    public_dns_name = instances["Reservations"][0]["Instances"][0]["PublicDnsName"]
    if public_dns_name == "":
        log.text(f"polling for instance connectivity in 5 seconds")
        time.sleep(5)
        return poll_for_public_dns_name(instance_id, ec2)
    else:
        return public_dns_name


def ensure_security_group_exists(security_group_name, ec2):
    try:
        return ec2.describe_security_groups(GroupNames=[security_group_name])[
            "SecurityGroups"
        ][0]["GroupId"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidGroup.NotFound":
            return create_security_group(security_group_name, ec2)
        else:
            raise e


def create_security_group(security_group_name, ec2):
    group_id = ec2.create_security_group(
        Description="Puter SSH access", GroupName=security_group_name
    )["GroupId"]
    log.data(
        {"type": "aws", "sub_type": "created security group", "group_id": group_id}
    )
    authorize_security_group_ingress(group_id, ec2)
    return group_id
