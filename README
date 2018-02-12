# libcloud-cli

It is a modified version of https://github.com/bluenerv/libcloud-cli that works with the OpenStack provider only.

## Requirements

* cloud provider account supported by libcloud
* python2.7 or newer
* miniconda

## Installation with Miniconda

* Type:

```
sudo conda install -c terradue libcloudcli
```

* Create and tailor ~/.libcloud for your own environment.

## Manual installation

* Copy lc.py to a location in your $PATH
* Create and tailor ~/.libcloud for your own environment.


## Usage

lc is a libcloud python CLI tool.

```
Usage: lc <command> [options|arguments] ...

Commands:
 [GENERAL]
   help <command>           Returns detailed help on command

 [COMPUTE]
   find-node                Finds an existing node by name
   find-floatingip	        Finds a floating ip by ip and prints its details
   list-locations           Lists supported cloud locations
   list-sizes               Lists all valid server sizes
   list-images              Lists all available server images
   list-nodes               Lists all existing nodes
   list-floatingips	        Lists all floating ips.
   list-floatingip-pools    List of all floating ip pools available
   list-volumes		        List of all volumes
   create-node              Creates a new node
   deploy-node              Creates, deploys and bootstraps a new node with custom ssh key
   destroy-node             Destroys an existing node
   create-volume	        Creates a new volume
   destroy-volume	        Destroys an existing volume
   attach-volume            Attaches a volume to an existing node
   

Options:
  --version                            shows program's version number and exit
  -h, --help                           shows this help message and exit
  -I ID, --id=ID                       ID for zone|balancer|compute node
  -n NAME, --name=NAME                 Name for zone|balancer|compute node
  -t TYPE, --type=TYPE                 Type of zone
  -l TTL, --ttl=TTL                    TTL of zone
  -e EXTRA, --extra=EXTRA              Extra attributes of zone
  -p PORT, --port=PORT                 Port of balancer
  -m MEMBER, --member=MEMBER           Node name of member
  -P PROTOCOL, --protocol=PROTOCOL     Protocol of balancer [default: http]
  -a ALGORITHM, --algorithm=ALGORITHM  Algorithm of balancer [default: round-
                                       robin]
  -i FLAVOR, --flavorId=FLAVOR         Id of flavor to use
  -v VOLUMEID, --volumeId=VOLUMEID     Id of volume to use
  -i IMAGE, --image=IMAGE              Name of image to use
  -w SECONDS, --wait=SECONDS           When creating or finding nodes, wait up
                                       to WAIT seconds until the node is running before returning
  -u, --unmapped                       Returns only unmmapped floating ips
  -p FLOATINGIPPOOL, --floatingippool=FLOATINGIPPOOL
                                       When creating a new node, it attaches
                                       a floating ip. If there are no
                                       available ones, it creates a news one
                                       and attaches it.
  --human                              Return results in human readable format
  --json                               Return results in json format
  --provider=PROVIDER                  Cloud provider to use
  --user=USER                          API username or id
  --key=KEY                            API key
  --public_key=PUBLIC_KEY              Public key to deploy [default:
                                       ~/.ssh/id_rsa.pub]
  --script=SCRIPT                      Script to run for deployment
  --config-file=CONFIG_FILE            Path to a custom configuration file in 
                                       ini format [default: ~/.libcloudrc]

  --ex_force_auth_version=EX_FORCE_AUTH_VERSION
  --ex_force_auth_url=EX_FORCE_AUTH_URL
  --ex_force_base_url=EX_FORCE_BASE_URL
  --ex_domain_name=EX_DOMAIN_NAME
  --ex_token_scope=EX_TOKEN_SCOPE
  --ex_tenant_name=EX_TENANT_NAME
```