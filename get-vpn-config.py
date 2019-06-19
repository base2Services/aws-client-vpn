#!/usr/bin/env python
import argparse
import subprocess
import boto3
import logging
import os
import random
import string
import re

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

parser = argparse.ArgumentParser()
parser.add_argument("--verbose", help="increase output verbosity",
                    action="store_true")

parser.add_argument("--name", help="stack and environment name the vpn",
                    action="store", required=True)

parser.add_argument("--region", help="aws region the vpn exists",
                    action="store", required=False)

args = parser.parse_args()

if not args.region:
    try:
        args.region = os.environ['AWS_REGION']
    except KeyError as ex:
        log.error('Set the aws region using --region or environment variable AWS_REGION')
        exit(1)

if args.verbose:
    log.setLevel(logging.DEBUG)
    log.debug('set log level to verbose')

client = boto3.client('ec2')

server_name = f"{args.name}-ClientVpn"
server = client.describe_client_vpn_endpoints(
    MaxResults=5,
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [server_name]
        }
    ]
)

if server['ClientVpnEndpoints']:
    id = server['ClientVpnEndpoints'][0]['ClientVpnEndpointId']
else:
    log.error(f"Unable to find client vpn {args.name}")
    exit(1)

vpn_config = client.export_client_vpn_client_configuration(
    ClientVpnEndpointId=id
)

config = vpn_config['ClientConfiguration']
config = re.sub(rf"{id}.*",rf"{randomString()}.{id}.prod.clientvpn.{args.region}.amazonaws.com 443",config)
config = config + f"\n\ncert /path/client1.domain.tld.crt"
config = config + f"\nkey /path/client1.domain.tld.key\n"

config_file = f"output/{id}.ovpn"

file = open(config_file, 'w')
file.write(config)
file.close()

log.info(f"Created config file {config_file}")
log.info("Please copy the config along with the client certificate a key to a secure location in your computer")
log.info("Modify cert and key values of the new certificate and key file locations")
log.info(f"Run `open {config_file}` from the config file location to import the config tunnelblick or openvpn client")
