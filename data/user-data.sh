#!/bin/bash
yum update -y
amazon-linux-extras install docker
sudo usermod -a -G docker ec2-user
service docker start
echo "sudo halt" | at now + 60 minutes
