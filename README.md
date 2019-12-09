# Puter

A fast and simple means of running EC2 instances for one-off work loads.

## Features

- Instances will self-terminate (can be disabled).
- Namespaces / idempotent resource creation. Facilitates multi-user AWS accounts and prevents the
  "same" resources from being created multiple times.
- Tagged AWS resources and local logs ensure you don't need to worry about losing a needle in a
  haystack.
- Convenient SSH and Rsync command suggestion.
- Resolves latest AWS Linux 2 AMI for whatever region is specified.
- Docker pre-installed on instances.

## Installation

TODO: installation with pip instead

- `git clone git@github.com:danielspofford/puter.git`

## Usage

TODO: NOTE: this is what usage will look like post-pip which is not possible yet

Now:

- `python puter/puter.py --profile=aws-profile --tag my-tag`

Soon:

```shell
puter \
  --profile=aws-profile \
  --tag bettys-puter
```

## How It Works

Puter uses these boto3 functions:

- `describe_instances`
- `create_key_pair`
- `run_instances`
- `describe_images`
- `create_security_group`
- `authorize_security_group_ingress`
- `describe_security_groups`
- `modify_instance_attribute`

On run, Puter:

- Ensures a keypair exists, by default this is `puter-v1`, but the user may
  provide their own.
- Ensures a `puter-v1` security group exists.
- Ensures an instance tagged with the value of the user provided `--tag` exists.

Puter never deletes anything itself. It achieves self-terminating EC2 instances
by indicating upon creation that they should terminate on shutdown. Puter's
default EC2 user data script schedules the system to shutdown 60 minutes from
execution.

The scheduled job can be viewed via `at -l`. Self-termination can be canceled
at the time of running the command via `--no-shutdown` and from within the
instance itself via `atrm JOBNUMBER`
where the job number is found via `at -l`.

### EC2 User Data Script

Automatic self-termination and Docker pre-install both rely on the EC2 user data script being
executed. This happens automatically on boot of any Cloud-init-enabled AMI (including Puter's
default AMIs).

## Development

Before interacting with anything, one should read through all of the following:

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Bootstrapping](BOOTSTRAPPING.md)
- [Contributing](CONTRIBUTING.md)
- [Deploy](DEPLOY.md)
