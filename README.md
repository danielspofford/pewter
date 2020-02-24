# Puter

A fast and simple means of running connectable EC2 instances for one-off work loads.

## Features

- Instances will self-terminate in 60 minutes (can be disabled).
- Easy connection.
- Tagged AWS resources and local logs ensure you don't need to worry about losing a needle in a
  haystack.
- Configurable alongside smart defaults.

## Installation

```shell
git clone git@github.com:danielspofford/puter.git
```

## Usage

Puter will ensure an EC2 instance exists and print its connection info.

```shell
python puter/puter.py --help
```

## Internals

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

- Ensures a keypair exists.
- Ensures a security group exists.
- Ensures an EC2 instance exists with the tag key `puter` and value equal to the `--tag` option.

Puter never deletes anything itself. It achieves self-terminating EC2 instances by indicating upon
creation that they should terminate on shutdown. Puter's default EC2 user data script schedules
the system to shutdown 60 minutes from execution.

The scheduled job can be viewed via `sudo at -l`. Self-termination can be canceled with
`sudo atrm JOBNUMBER`. The job number is found via `sudo at -l`.

### EC2 User Data Script

Automatic self-termination relies on the EC2 user data script being executed. This happens
automatically on boot of any Cloud-init-enabled AMI.

## Development

Before interacting with anything, one should read through all of the following:

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Bootstrapping](BOOTSTRAPPING.md)
- [Contributing](CONTRIBUTING.md)
- [Deploy](DEPLOY.md)
