# aws-client-vpn

## Requirements

- python 3
- boto3
- docker

## Scripts

### client-vpn.py

- generate the certicates using OpenVPN easy-rsa in the output directory
- uploads the certificates to ACM and tags them
- creates the vpn endpoint required resources using cloudformation

```bash
usage: client-vpn.py [-h] [--verbose] --server-cn SERVER_CN
                     [--client-cn CLIENT_CN] --name NAME --subnet-id SUBNET_ID
                     [--cidr CIDR]

optional arguments:
  -h, --help            show this help message and exit
  --verbose             increase output verbosity
  --server-cn SERVER_CN
                        common name for the server certificate
  --client-cn CLIENT_CN
                        common name for the server certificate
  --name NAME           stack and environment name the vpn
  --subnet-id SUBNET_ID
                        SubnetId to which the vpn will assocate with
  --cidr CIDR           CIDR the vpn will give to the clients
```

### get-vpn-config.py

- gets the id of the client vpn endpoint
- downloads the client config file into the output directory
- alters the hostname in the config with a random string

```bash
usage: get-vpn-config.py [-h] [--verbose] --name NAME [--region REGION]

optional arguments:
  -h, --help       show this help message and exit
  --verbose        increase output verbosity
  --name NAME      stack and environment name the vpn
  --region REGION  aws region the vpn exists
```

## Setup

1. Clone the repo

2. Get the id of the subnet you wish to associate the vpn with

3. Run the `client-vpn.py` script with the following required options

  ```bash
  ./client-vpn.py --server-cn=vpn.domain.tld --name ciinabox --subnet-id ${SubnetId}
  ```

4. Run the `get-vpn-config.py` script to download the config file

5. copy the config file and the client certificate and key to a local secure directory

6. modify the config paths for the `cert` and `key`

7. open the config in your favourite vpn client
