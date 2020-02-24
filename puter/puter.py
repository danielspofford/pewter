# """
# Entrypoint for the Puter CLI.
# """

import os
import uuid
from pathlib import Path

import boto3
import click
import dateutil.parser

import aws
import log


@click.command(context_settings=dict(max_content_width=120))
@click.option(
    "-i", "--instance-type", default="t2.micro", help="AWS instance type to use for EC2"
)
@click.option("-p", "--profile", help="AWS profile to use for all requests.")
@click.option(
    "-r", "--region", default="us-east-1", help="The AWS region for EC2 operations."
)
@click.option(
    "-s",
    "--security-group-name",
    default="puter-v1",
    help="The AWS EC2 security group name. If it does not exist it will be created allowing tcp ingress on port 22.",
)
@click.option(
    "-k",
    "--key-name",
    default="puter-v1",
    help="The AWS EC2 key pair name. The key pair will be created if it does not yet exist.",
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
    session_opts = profile and {"profile_name": profile, "region_name": region} or {}
    session = boto3.Session(**session_opts)
    ec2 = session.client("ec2")
    private_key_path = resolve_private_key_path(key_name)
    aws.ensure_key_pair_exists(key_name, private_key_path, ec2)
    security_group_id = aws.ensure_security_group_exists(security_group_name, ec2)
    instance = aws.ensure_instance_exists(
        tag, instance_type, key_name, security_group_id, ami, ec2
    )
    aws.ensure_instance_has_security_group(instance, security_group_id, ec2)
    public_dns_name = aws.poll_for_public_dns_name(instance["InstanceId"], ec2)
    log_rsync_and_connect_commands(key_name, private_key_path, public_dns_name)


def resolve_private_key_path(key_name):
    """
    Return the path of the private key `key_name`.

    A file may not exist at the returned path, however the parent directories of the potential
    file will be created with permission 0700 if they do not exist.
    """
    private_keys_dir = data_dir() / f"private_keys"
    os.makedirs(private_keys_dir, mode=0o700, exist_ok=True)
    return private_keys_dir / f"ec2-keypair-{key_name}.pem"


def log_rsync_and_connect_commands(key_name, private_key_path, public_dns_name):
    """Logs rsync and ssh commands prefilled with relevant arguments and placeholders."""
    if not private_key_path.is_file():
        private_key_path = "PATH-TO-PRIVATE-KEY"
    user = "USER"
    ssh_text = click.style(
        f"ssh \\\n" f"  -i {private_key_path} \\\n" f"  {user}@{public_dns_name}",
        fg="green",
    )
    rsync_text = click.style(
        f"rsync \\\n"
        f"  -Paq \\\n"
        f"  --exclude .git \\\n"
        f'  -e "ssh -i {private_key_path}" \\\n'
        f"  ~/SOME-PATH.txt \\\n"
        f"  {user}@{public_dns_name}:/tmp",
        fg="green",
    )
    log.text(f"rsync command:\n{rsync_text}")
    log.text(f"connect command:\n{ssh_text}")
    log.text(
        'The USER depends on the AMI. Amazon Linux 2 uses "ec2-user", Ubunutu uses "ubuntu", etc.'
    )


def data_dir():
    """
    Return the directory in which to store data as a pathlib.Path.

    Complies with https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html.
    """
    return (
        Path(os.path.expandvars(os.getenv("XDG_DATA_HOME") or "$HOME/.local/share"))
        / "puter"
    )


if __name__ == "__main__":
    try:
        os.makedirs(data_dir(), mode=0o700, exist_ok=True)
        cli()
    except Exception as e:
        log.exception(e)
