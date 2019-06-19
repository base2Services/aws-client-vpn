#!/usr/bin/env python
import argparse
import subprocess
import boto3
import logging
import os

from botocore import exceptions

def load_byte_file(filename):
    return open(filename, "rb").read()

def import_certificate(cert,key,ca):
    acm = boto3.client('acm')
    response = acm.import_certificate(
        Certificate=load_byte_file(cert),
        PrivateKey=load_byte_file(key),
        CertificateChain=load_byte_file(ca)
    )
    return response['CertificateArn']

def tag_certificate(arn,tags=[]):
    acm = boto3.client('acm')
    response = acm.add_tags_to_certificate(
        CertificateArn=arn,
        Tags=tags
    )

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

parser = argparse.ArgumentParser()
parser.add_argument("--verbose", help="increase output verbosity",
                    action="store_true")

parser.add_argument("--server-cn", help="common name for the server certificate",
                    action="store", required=True)

parser.add_argument("--client-cn", help="common name for the server certificate",
                    action="store", required=False)

parser.add_argument("--name", help="stack and environment name the vpn",
                    action="store", required=True)

parser.add_argument("--subnet-id", help="SubnetId to which the vpn will assocate with",
                    action="store", required=True)

parser.add_argument("--cidr", help="CIDR the vpn will give to the clients",
                    action="store", required=False)

args = parser.parse_args()

if not args.client_cn:
    args.client_cn = f"{args.name}.{args.server_cn}"

if args.verbose:
    log.setLevel(logging.DEBUG)
    log.debug('set log level to verbose')

docker_exists = subprocess.call(['which', 'docker'])

if docker_exists != 0:
    log.error("docker command does not exist in your path. Please start or install docker to use this script!")
    exit(1)

docker_run = ["docker", "run", "-it", "--rm"]
docker_run.append(f"-e EASYRSA_REQ_CN={args.server_cn}")
docker_run.append(f"-e EASYRSA_CLIENT_CN={args.client_cn}")
docker_run.append("-v $PWD/output:/easy-rsa/output")
docker_run.append("base2/aws-client-vpn")

log.info("Generating openvpn certificates using easy-rsa")

os.system(' '.join(docker_run))

output = os.system("ls output")
log.info(f"created certificates in output directory")


log.debug("importing server certificate into ACM")
server_certificate_arn = import_certificate(cert='output/server.crt',
                                            key='output/server.key',
                                            ca='output/ca.crt')
tag_certificate(arn=server_certificate_arn,tags=[{ 'Key': 'Name', 'Value': args.server_cn }])
log.info(f"Creted ACM server certificate {server_certificate_arn}")


log.debug("importing client certificate into ACM")
client_certificate_arn = import_certificate(cert=f"output/{args.client_cn}.crt",
                                            key=f"output/{args.client_cn}.key",
                                            ca='output/ca.crt')
tag_certificate(arn=client_certificate_arn,tags=[{ 'Key': 'Name', 'Value': args.client_cn }])
log.info(f"Creted ACM client certificate {client_certificate_arn}")


tags = []
tags.append({ 'Key': 'Name', 'Value': args.name })

parameters = []
parameters.append({'ParameterKey': 'EnvironmentName', 'ParameterValue': args.name})
parameters.append({'ParameterKey': 'ClientCertificateArn', 'ParameterValue': client_certificate_arn})
parameters.append({'ParameterKey': 'ServerCertificateArn', 'ParameterValue': server_certificate_arn})
parameters.append({'ParameterKey': 'AssociationSubnetId', 'ParameterValue': args.subnet_id})

if args.cidr:
    parameters.append({'ParameterKey': 'ClientCidrBlock', 'ParameterValue': args.cidr})

with open('template.yaml', 'r') as file:
    template = file.read()

cloudformation = boto3.client('cloudformation')
stack_name = f"{args.name}-vpn"

log.info(f"Creating cloudformation stack {stack_name}")

response = cloudformation.create_stack(
    StackName=stack_name,
    TemplateBody=template,
    Parameters=parameters,
    TimeoutInMinutes=15,
    OnFailure='DELETE',
    Tags=tags
)

log.info(f"Waiting for cloudformation stack {stack_name} to complete")

waiter = cloudformation.get_waiter('stack_create_complete')
waiter_config = {'Delay': 5,'MaxAttempts': 720}
try:
    waiter.wait(StackName=stack_name, WaiterConfig=waiter_config)
except botocore.exceptions.WaiterError as ex:
    log.error(f"failed to create stack {stack_name}", exc_info=ex)

log.info(f"Cloudformation stack {stack_name} has successfully completed")
log.info("Run ./get-vpn-config.py to download your client config file")
