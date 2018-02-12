#!/usr/bin/env python
# #############################################################################
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# #############################################################################

import os
import re
import sys
import time
import copy
import ConfigParser
import json
import libcloud
from optparse import OptionParser, HelpFormatter
from collections import OrderedDict

from libcloud.dns.base import Zone, Record
from libcloud.dns.providers import get_driver as get_driver_dns
from libcloud.dns.types import Provider as Provider_DNS, RecordType

from libcloud.compute.deployment import MultiStepDeployment, ScriptDeployment, SSHKeyDeployment
from libcloud.compute.providers import get_driver as get_driver_compute
from libcloud.compute.types import Provider as Provider_Compute, NodeState

from libcloud.common.openstack_identity import OpenStackIdentityTokenScope

import libcloud.security


class Skynet(object):
    """
    lc is a libcloud python cli tool

    Usage: %prog <command> [options|arguments] ...

    Commands:
        [GENERAL]
        help <command>                    Returns detailed help on command

        [COMPUTE]
        find-node                         Finds an existing node by name
        find-floatingip                   Finds a floating ip from the ip
        list-locations                    Lists supported cloud locations
        list-flavors                      Lists all valid server flavors
        list-images                       Lists all available server images
        list-nodes                        Lists all existing nodes
        list-floatingips                  Lists all floating ips
        list-floatingip-pools             Lists all floating ip pools
        list-volumes                      List of all volumes
        create-node                       Creates a new node
        deploy-node                       Creates, deploys and bootstraps a new node with custom ssh key
        destroy-node                      Destroys an existing node
        create-volume                     Creates a new volume
        destroy-volume                    Destroys an existing volume
        attach-volume                     Attaches a volume to an existing node

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
        -u, --unmapped                        Returns only unmmapped floating ips
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
    """

    # MAP for cloud resources

    record_type_map = {
        RecordType.A: 'a',
        RecordType.AAAA: 'aaaa',
        RecordType.MX: 'mx',
        RecordType.NS: 'ns',
        RecordType.CNAME: 'cname',
        RecordType.DNAME: 'dname',
        RecordType.TXT: 'txt',
        RecordType.PTR: 'ptr',
        RecordType.SOA: 'soa',
        RecordType.SPF: 'spf',
        RecordType.SRV: 'srv',
        RecordType.PTR: 'ptr',
        RecordType.NAPTR: 'naptr',
        RecordType.REDIRECT: 'redirect'
    }

    compute_state_map = {
        NodeState.RUNNING: 'running',
        NodeState.REBOOTING: 'rebooting',
        NodeState.TERMINATED: 'terminated',
        NodeState.PENDING: 'pending',
        NodeState.UNKNOWN: 'unknown',
        NodeState.STOPPED: 'stopped'
    }

    # COMPUTE: dynamic compute methods
    def cmd_find_node(self, options, arguments):
        """
        Finds a single node by id and prints its details.

        Usage: %prog [options] find-node -n <id>
        """
        if options.id is None:
            self.fail("find-node requires the id of the node")

        if self.options.wait:
            node = self.wait_for_running_node(
                options.id, timeout=self.options.wait)
        else:
            node = self.find_node(options.id)

        if node:
            self.succeed(data=node, data_type='node')
        else:
            self.succeed(data=None, message="No node found with id \"%s\"" % options.id)

    def cmd_find_floatingip(self, options, arguments):
        """
        Finds a floating ip by ip and prints its details.

        Usage: %prog [options] find-floatingip - <id>
        """
        if options.addressip is None:
            self.fail("find-floatingip requires the ip of the floatingip")

        floatingip = self.find_floatingip(options.addressip)

        if floatingip:
            self.succeed(data=floatingip, data_type='floatingip')
        else:
            self.succeed(data=None, message="No floatingip found with ip \"%s\"" % options.addressip)

    def cmd_list_locations(self, options, arguments):
        """
        Fetches a list of locations.

        Usage: %prog [options] list-locations
        """
        try:
            locations = self.connection_compute.list_locations()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=locations)

    def cmd_list_flavors(self, options, arguments):
        """
        Fetches a list of all available server sizes.

        Usage: %prog [options] list-flavors
        """
        try:
            sizes = self.connection_compute.list_sizes()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=sizes, data_type='size')

    def cmd_list_images(self, options, arguments):
        """
        Fetches a list of all available server images.

        Usage: %prog [options] list-images
        """
        try:
            images = self.connection_compute.list_images()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=images, data_type='image')

    def cmd_list_networks(self, options, arguments):
        """
        Fetches a list of all available networks.

        Usage: %prog [options] list-netorks
        """
        try:
            networks = self.connection_compute.ex_list_networks()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=networks, data_type='network')

    def cmd_list_nodes(self, options, arguments):
        """
        Fetches a list of all registered nodes.

        Usage: %prog [options] list-nodes
        """
        try:
            nodes = self.connection_compute.list_nodes()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=nodes, data_type='node')

    def cmd_list_floatingips(self, options, arguments):
        """
        Fetches a list of all floating ips.

        Usage: %prog [options] list-floatingips
        """
        floatingips = self.list_floatingips(options.unmapped)

        self.succeed(data=floatingips, data_type='floatingip')

    def list_floatingips(self, unmapped):
        try:
            # all floating ip
            floatingips = self.connection_compute.ex_list_floating_ips()

            # if unmapped flag is selected, filter all floating ips that are
            # not associated to a node
            if unmapped:
                def returnIp(x): return x.ip_address
                listOfFloatingIps = map(returnIp, floatingips)
                try:
                    nodes = self.connection_compute.list_nodes()
                    for node in nodes:
                        for public_ip in node.public_ips:
                            if public_ip in listOfFloatingIps:
                                floatingips = filter(lambda x: x.ip_address!=public_ip, floatingips)
                except Exception as e:
                    self.fail("Exception: %s" % e)
            return floatingips
        except Exception as e:
            self.fail("Exception: %s" % e)

    def cmd_list_floatingip_pools(self, options, arguments):
        """
        Fetches a list of all floating ip pools available.

        Usage: %prog [options] list-floatingip_pools

        """
        try:
            floatingip_pools = self.connection_compute.ex_list_floating_ip_pools()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=floatingip_pools, data_type='floatingippool')

    def cmd_list_volumes(self, options, arguments):
        """
        Fetches a list of all volumes available.

        Usage: %prog [options] list-volumes

        """
        try:
            volumes = self.connection_compute.list_volumes()
        except Exception as e:
            self.fail("Exception: %s" % e)

        self.succeed(data=volumes, data_type='volume')

    def cmd_create_volume(self, options, arguments):
        """
        Creates a new volume and prints its details.

        Usage: %prog [options] create-volume --size --name --location --snapshot --ex_volume_type
        """
        if options.name is None:
            self.fail("create-volume requires the name of the volume to create")

        if options.type is None:
            self.fail("create-volume requires the type of the volume to create")

        if options.size is None:
            self.fail("create-volume requires the size of the volume to create")

        volume = self.connection_compute.create_volume(options.size,options.name,ex_volume_type=options.type)

        self.succeed(data=volume, data_type='volume')

    def cmd_attach_volume(self, options, arguments):

        if options.id is None:
            self.fail("attach-volume requires the id of the node to attach")

        if options.volumeId is None:
            self.fail("attach-volume requires the name of the volume to attach")

        if options.device is None:
            self.fail("attach-volume requires the device of the volume to attach")

        # retriving node
        if self.options.wait:
            node = self.wait_for_running_node(
                options.id, timeout=self.options.wait)
        else:
            node = self.find_node(options.id)

        if node is  None:
            self.fail("Missing or invalid node id provided.")

        # retrieving volume
        volume = self.find_volume(options.volumeId)
        if volume is  None:
            self.fail("Missing or invalid volume id provided.")

        try:
            success = self.connection_compute.attach_volume(node,volume,device=options.device)
        except Exception as e:
            self.fail("Exception: %s" % e)

        if not success:
            self.fail("An error occured while attaching the volume " + volume.id + " to node " + node.id)

    def cmd_find_volume(self, options, arguments):
        if options.volumeId is None:
            self.fail("volume id required")
        try:
            volume = self.find_volume(options.volumeId)
            if volume is None:
                self.fail("Missing or invalid volume id provided.")
            self.succeed(data=volume, data_type='volume')
        except Exception as e:
            self.fail("Exception: %s" % e)

    def find_volume(self, volumeId):
        volumes = self.connection_compute.list_volumes()
        for volume in volumes:
            if volume.id == volumeId:
                return volume
        return None

    def cmd_create_node(self, options, arguments):
        """
        Creates a new node and prints its details. If a node with the same name already existed, prints its details instead.

        Usage: %prog [options] create-node --name <fqdn>
        """
        if options.name is None:
            self.fail("create-node requires the name of the node to create")

        options.name
        node = self.find_node_by_name(options.name)
        if (node):
            self.fail(message="Node \"%s\" already exists!" % options.name)

        image = self.find_image(options.image)
        if (not image):
            print options.image
            self.fail("Missing or invalid image id provided.")

        flavorId = self.find_flavor(options.flavorId)
        if (not flavorId):
            print options.flavorId
            self.fail("Missing or invalid flavor id provided.")

        network_objects = []
        if (not self.options.networks):
            self.fail("Missing networks.")
        else:
            for networkId in self.options.networks:
                try:
                    network = self.find_network(networkId)
                    if (not network):
                        print networkId
                        self.fail("Missing or invalid network id provided.")
                    network_objects.append(network)
                except Exception as e:
                    self.fail("Failed to retrieve networks")

        try:
            node = self.connection_compute.create_node(
                name=options.name, image=image, size=flavorId, networks= network_objects)
        except Exception as e:
            self.fail("Exception: %s" % e)

        if self.options.wait:
            #print "checking if running " + str(node.id)
            running_node = self.wait_for_running_node(
                node.id, timeout=self.options.wait)
        else:
            running_node = None

        if self.options.floatingippool:
            # retrieving all available floating ips
            self.options.unmapped = "true"
            availableFloatingIps = self.list_floatingips(self.options.unmapped)

            # if there are available floating ips, use the first one, else create a new one
            if availableFloatingIps:
                floatingip = availableFloatingIps[0]
            else:
                floatingip = self.connection_compute.ex_create_floating_ip(self.options.floatingippool)

            # attach the floating ip to the node
            # sometimes the ip cannot be attached immediately. If we didn't
            # retry, we'd obtain:
            # "400 Bad Request No nw_info cache associated with instance"
            cont = 0
            retries = 5
            delay = 5
            attached = False

            while not attached and cont < retries:
                try:
                    self.connection_compute.ex_attach_floating_ip_to_node(node, floatingip)
                    attached = True
                except Exception as atex:
                    self.log_warn("Error attaching a Floating IP to the node: %s" % str(atex))
                    cont += 1
                    if cont < retries:
                        time.sleep(delay)

        if (node):
            if (running_node):
                node = self.find_node(node.id)
                #node.state = running_node.state
            self.succeed(message="Node \"%s\" created!" %
                options.name, data=node, data_type='node')

    def cmd_deploy_node(self, options, arguments):
        """
        Creates, deploys and bootstraps a new node and prints its details. If a node with the same name already existed, prints its details instead.

        Usage: %prog [options] deploy-node --name <fqdn>
        """
        if options.name is None:
            self.fail("deploy-node requires the name of the node to create")

        options.name
        node = self.find_node(options.name)
        if (node):
            self.succeed(message="Node \"%s\" already exists!" %
                         options.name, data=node)

        image = self.find_image(options.image)
        if (not image):
            print options.image
            self.fail("Missing or invalid image id provided.")

        flavorId = self.find_flavor(options.flavorId)
        if (not flavorId):
            print options.flavorId
            self.fail("Missing or invalid flavor id provided.")

        network_objects = []
        if (not self.options.networks):
            self.fail("Missing networks.")
        else:
            for networkId in self.options.networks:
                try:
                    network = self.find_network(networkId)
                    if (not network):
                        print networkId
                        self.fail("Missing or invalid network id provided.")
                    network_objects.append(network)
                except Exception as e:
                    self.fail("Failed to retrieve networks")

        # read your public key in
        # Note: This key will be added to root's authorized_keys
        # (/root/.ssh/authorized_keys)
        sd = SSHKeyDeployment(
            open(os.path.expanduser(options.public_key)).read())

        # a simple script to install puppet post boot, can be much more
        # complicated.
        script = ScriptDeployment(options.script)

        # a task that first installs the ssh key, and then runs the script
        msd = MultiStepDeployment([sd, script])

        try:
            # deploy our node using multistep deployment strategy
            node = self.connection_compute.deploy_node(
                name=options.name, image=image, size=flavorId, deploy=msd, networks= network_objects)
            print "deploy success"
            # gets the hostname and domainname from fqdn
            hostname, domainname = options.name.split('.', 1)

            # see if zone already exists
            zone = self.find_zone(domainname)

            # if zone instance does not exist, create it
            if (not zone):
                zone = self.connection_dns.create_zone(domain=domainname)

            # create an A record type wth the public ip of the created node for
            # our zone
            record = zone.create_record(
                name=hostname, type=RecordType.A, data=node.public_ips[0])
        except Exception as e:
            self.fail("Exception: %s" % e)

        # decide if we wanted to wait for a reference of the running node
        if self.options.wait:
            running_node = self.wait_for_running_node(
                node.id, timeout=self.options.wait)
        else:
            running_node = None

        # if the node was created
        if (node):
            # if the running node exists set the node state to running
            if (running_node):
                node.state = running_node.state
            self.succeed(message="Node \"%s\" deployed!" %
                         options.name, data=node, data_type='node')

    def cmd_destroy_node(self, options, arguments):
        """
        Destroys a single node by name.

        Usage: %prog [options] destroy-node --name <fqdn>
        """
        if options.id is None:
            self.fail("destroy-node requires the id of the node to destroy")

        node = self.wait_for_running_node(options.id)

        if not node:
            self.fail("No running node found with id \"%s\"" % options.id)
        elif node.destroy():
            self.succeed(message="Node \"%s\" destroyed!" % options.id)
        else:
            self.fail("Could not destroy node \"%s\"" % options.id)

    def cmd_destroy_volume(self, options, arguments):
        """
        Destroys a volume by volumeId.

        Usage: %prog [options] destroy-volume --volumeId <fqdn>
        """
        if options.volumeId is None:
            self.fail("destroy-volume requires the id of the volume to destroy")

        try:
            volume = self.find_volume(options.volumeId)
            if not volume:
                self.fail("No volume found with id \"%s\"" % options.volumeId)
            success = self.connection_compute.destroy_volume(volume)
        except Exception as e:
            self.fail("Exception: %s" % e)

        if not success:
            self.fail("No volume found with id \"%s\"" % options.volumeId)
        else:
            self.succeed(message="Volume \"%s\" destroyed!" % options.volumeId)

    def cmd_help(self, options, arguments):
        """
        Returns more detailed help on command

        Usage: %prog [options] help <command>
        """
        help_command = arguments.pop(0) if arguments else None
        method = self.get_command_method(help_command)

        if method:
            self.parser.usage = method.__doc__
        else:
            self.parser.usage = self.__doc__

        self.parser.print_help()

    # HELPER: helper methods
    
    def find_size(self, ram):
        """
        Finds a node size object based on its ram.
        """
        try:
            sizes = self.connection_compute.list_sizes()
        except Exception as e:
            self.fail("Exception: %s" % e)

        ram = int(ram)
        return next((size for size in sizes if size.ram == ram), None)

    def find_flavor(self, flavorId):
        """
        Finds a flavor based on its id.
        """
        try:
            flavor = self.connection_compute.ex_get_size(flavorId)
        except Exception as e:
            self.fail("Exception: %s" % e)

        return flavor

    def find_network(self, networkid):
        """
        Finds network object based on its id.
        """
        try:
            networks = self.connection_compute.ex_list_networks()
        except Exception as e:
            self.fail("Exception: %s" % e)

        return next((network for network in networks if networkid == network.id), None)

    def find_image(self, id):
        """
        Finds an image type object based on its name.
        """
        try:
            image = self.connection_compute.get_image(id)
        except Exception as e:
            self.fail("Missing or invalid image id provided.")

        return image

    def find_image_by_name(self, name):
        """
        Finds an image type object based on its name.
        """
        try:
            images = self.connection_compute.list_images()
        except Exception as e:
            self.fail("Exception: %s" % e)

        return next((image for image in images if name == image.name), None)

    def find_node_by_name(self, name):
        """
        Finds a node object based on its name.
        """
        try:
            nodes = self.connection_compute.list_nodes()
        except Exception as e:
            self.fail("Exception: %s" % e)

        return next((node for node in nodes if name == node.name), None)

    def find_node(self, id):
        """
        Finds a node object based on its name.
        """
        try:
            node = self.connection_compute.ex_get_node_details(id)
        except Exception as e:
            self.fail("Missing or invalid node id provided.")

        return node

    def find_floatingip(self, ip):
        """
        Finds a floatingip object based on its ip.
        """
        try:
            floatingip = self.connection_compute.ex_get_floating_ip(ip)
        except Exception as e:
            self.fail("Missing or invalid ip provided.")

        return floatingip

    def wait_for_running_node(self, id, poll_period=2, timeout=30):
        """
        Find a node object based on its id, waiting for it to be running.

        This method blocks up to timeout seconds until the node object is
        confirmed to be running.  After the timeout, it may return a non-running
        node, so you still need to check the state before performing
        further operations on the node.
        """
        elapsed_time = 0
        while elapsed_time < timeout:
            node = self.find_node(id)
            if not node:
                return None
            if node.state == 0:
                return node
            time.sleep(poll_period)
            elapsed_time = elapsed_time + poll_period
        return node

    # OUTPUT

    def fail(self, message):
        """
        Prints an error message and stops execution with an error code.
        """
        output = self.get_output(message=message)
        self.print_formatted_output(output)
        sys.exit(1)

    def succeed(self, message=None, data=None, data_type="default"):
        """
        Prints a success message and any provided data, then stops execution.
        """
        output = self.get_output(
            message=message, data=data, data_type=data_type)
        self.print_formatted_output(output)
        sys.exit(0)

    def get_output(self, message=None, data=None, data_type="default"):
        """
        Returns a dictionary to be used as a content source for output.
        """
        output = {}
        if message:
            output['message'] = message

        if data:
            output['data'] = []
        if is_dict_like(data):
            data = [data]

        if is_list_like(data):
            for item in data:
                output['data'].append(
                    self.prepare_output_item(item, data_type))

        return output

    # MAPPING: format result

    def prepare_output_item(self, item, data_type):
        """
        Converts a single data item into a dictionary for our output dictionary.
        """
        format_method_name = 'get_output_for_' + data_type
        method = getattr(self, format_method_name)
        if (method):
            return method(item)
        else:
            return None

    def get_output_for_default(self, obj):
        """
        Default list.
        """
        result = OrderedDict()
        result['key'] = obj
        return result

    def get_output_for_record_type(self, record_type):
        """
        Converts a single 'record_type' data item into a dictionary for our output dictionary.
        """
        result = OrderedDict()
        result['key'] = self.record_type_map[record_type]
        return result

    def get_output_for_size(self, size):
        """
        Converts a single 'size' data item into a dictionary for our output dictionary.
        """
        result = OrderedDict()
        result["id"] = size.id
        result["name"] = size.name
        result["ram"] = size.ram
        result["disk"] = size.disk
        result["bandwidth"] = size.bandwidth
        result["price"] = size.price
        return result

    def get_output_for_image(self, image):
        """
        Converts a single 'image' data item into a dictionary for our output dictionary.
        """
        result = OrderedDict()
        result["id"] = image.id
        result["name"] = image.name
        return result

    def get_output_for_network(self, network):
        """
        Converts a single 'network' data item into a dictionary for our output dictionary.
        """
        result = OrderedDict()
        result["id"] = network.id
        result["name"] = network.name
        result["cidr"] = network.cidr
        return result

    def get_output_for_node(self, node):
        """
        Converts a single 'node' data item into a dictionary for our output dictionary.
        """
        values = node.__dict__.copy()

        result = OrderedDict()
        #result['uuid'] = node.uuid
        result['id'] = values['id']
        result['name'] = values['name']
        result['flavor_id'] = node.extra['flavorId']
        result['image_id'] = node.extra['imageId']
        result['state'] = self.compute_state_map[values['state']]
        result['private_ips'] = values['private_ips']
        result['public_ips'] = values['public_ips']
        result['extra'] = values['extra']
        return result

    def get_output_for_floatingip(self, floatingip):
        """
        Converts a single 'floatingip' data item into a dictionary for our output dictionary.
        """
        values = floatingip.__dict__.copy()

        result = OrderedDict()
        result['id'] =  values['id']
        result['ip_address'] =  values['ip_address']
        return result

    def get_output_for_volume(self, volume):
        """
        Converts a single 'volume' data item into a dictionary for our output dictionary.
        """
        values = volume.__dict__.copy()

        result = OrderedDict()
        result['id'] =  values['id']
        result['size'] =  values['size']
        result['extra'] = values['extra']
        return result

    def get_output_for_floatingippool(self, floatingippool):
        """
        Converts a single 'floatingippool' data item into a dictionary for our output dictionary.
        """
        values = floatingippool.__dict__.copy()
        result = OrderedDict()
        result['name'] =  values['name']
        return result

    # PRINT: output

    def print_formatted_output(self, output):
        """
        Formats and prints our output dictionary.
        """
        if self.options.human:
            self.print_text_output(output)
        elif self.options.json:
            self.print_json_output(output)
        else:
            self.print_simple_output(output)

    def print_simple_output(self, output):
        """
        Prints an output dictionary as text.
        """
        if 'message' in output:
            print output['message']

        if 'data' in output and output['data']:
            for item in output['data']:
                self.print_line_item(item)

    def print_json_output(self, output):
        """
        Prints an output dictionary as json.
        """
        print json.dumps(output, indent=2, sort_keys=True)

    def print_text_output(self, output):
        """
        Prints an output dictionary as text.
        """
        if 'message' in output:
            print output['message']

        if 'data' in output and output['data']:
            print "-----"
            for item in output['data']:
                self.print_item(item)

    def print_line_item(self, item):
        """
        Prints a single data item from an output dictionary as text.
        """
        print item.values()

    def print_item(self, item):
        """
        Prints a single data item from an output dictionary as text.
        """
        for key in item.keys():
            print "%s: %s" % (key, item[key])
        print "-----"

    # INIT

    def __init__(self):
        self.options, self.arguments = self.parse_args()
        self.process_ini_files()
        self.set_defaults_from_ini()

    # INIT: args

    def parse_args(self):
        """
        Set up the cli options
        """
        formatter = DocstringHelpFormatter()
        self.parser = OptionParser(
            usage='', version="%prog 1.10.1", formatter=formatter)

        self.parser.add_option("--id", "-I",
                               help="ID for compute node"
                               )

        self.parser.add_option("--name", "-n",
                               help="Name for compute node"
                               )

        self.parser.add_option("--type", "-t",
                               help="Type of zone/volume"
                               )

        self.parser.add_option("--ttl", "-l",
                               type="int",
                               help="TTL of zone"
                               )

        self.parser.add_option("--extra", "-e",
                               help="Extra attributes of zone"
                               )

        self.parser.add_option("--member", "-m",
                               help="Node name of member"
                               )

        self.parser.add_option("--flavorId", "-f",
                               type="int",
                               help="Id of flavor to use"
                               )

        self.parser.add_option("--volumeId", "-v",
                               help="Id of volume to use"
                               )

        self.parser.add_option("--device", "-d",
                               help=" Where the device is exposed, e.g. '/dev/sdb'"
                               )

        self.parser.add_option("--image", "-i",
                               help="Name of image to use"
                               )

        self.parser.add_option("--size", "-s",
                               type="int",
                               help="Size of the volume to create"
                               )

        self.parser.add_option("--addressip", "-a",
                               help="Ip address for finding a floating ip"
                               )

        self.parser.add_option("--wait", "-w",
                               metavar="SECONDS",
                               type="int",
                               help="When creating or finding nodes, waits up to WAIT seconds until the node is running before returning"
                               )

        self.parser.add_option("--human",
                               action="store_true",
                               dest="human",
                               help="Returns results in human readable format"
                               )

        self.parser.add_option("--json",
                               action="store_true",
                               dest="json",
                               help="Returns results in json format"
                               )

        self.parser.add_option("--unmapped", "-u",
                               action="store_true",
                               dest="unmapped",
                               help="Returns only unmmapped floating ips"
                               )

        self.parser.add_option("--floatingippool", "-p",
                               help="When creating a new node, it attaches a floating ip. If there are no available ones, it creates a news one and attaches it."
                               )

        self.parser.add_option("--provider",
                               help="Cloud provider to use"
                               )
                                                           
        self.parser.add_option("--networks",
                                type='string',
                                action='callback',
                                callback=self.parse_array_callback,
                                dest="networks")

        self.parser.add_option("--user",
                               help="API username or id"
                               )

        self.parser.add_option("--key",
                               help="API key"
                               )

        self.parser.add_option("--public_key",
                               help="Public key to deploy [default: %default]"
                               )

        self.parser.add_option("--script",
                               help="Script to run for deployment"
                               )

        self.parser.add_option("--config-file",
                               help="Path to a custom configuration file in ini format [default: %default]"
                               )

        self.parser.set_defaults(
            config_file='~/.libcloudrc',
            public_key='~/.ssh/id_rsa.pub'
        )

        # new params
        self.parser.add_option("--ex_force_auth_version")

        self.parser.add_option("--ex_force_auth_url")

        self.parser.add_option("--ex_force_base_url")

        self.parser.add_option("--ex_domain_name")

        self.parser.add_option("--ex_token_scope")

        self.parser.add_option("--ex_tenant_name")

        return self.parser.parse_args()
        
    def parse_array_callback(self,option, opt, value, parser):
        setattr(parser.values, option.dest, value.split(',') )

    # INIT: config

    def get_config_path(self):
        """
        Retrieves the path to the config file.
        """
        return os.path.expanduser(self.options.config_file)

    def process_ini_files(self):
        """
        Loads any config files into our settings property.
        """
        try:
            config_path = self.get_config_path()
            config = ConfigParser.RawConfigParser()
            config.read(config_path)
        except Exception as e:
            self.fail("Failed to parse configuration file: %s" % e)

        self.settings = {}

        for section in config.sections():
            self.settings[section] = {}
            for item in config.items(section):
                self.settings[section][item[0]] = item[1]

    def set_defaults_from_ini(self):
        """
        Applies defaults from our config files over any missing options.
        """

        if not self.options.provider:
            if 'default' in self.settings and 'provider' in self.settings['default']:
                self.options.provider = self.settings['default']['provider']
            else:
                self.fail("No cloud provider setting was defined.")

        provider_lc = self.options.provider.lower()

        if not self.options.user:
            if provider_lc in self.settings and 'user' in self.settings[provider_lc]:
                self.options.user = self.settings[provider_lc]['user']
            else:
                self.fail("No user was defined for the cloud provider.")

        if not self.options.key:
            if provider_lc in self.settings and 'key' in self.settings[provider_lc]:
                self.options.key = self.settings[provider_lc]['key']
            else:
                self.fail("No key was defined for the cloud provider.")

        if not self.options.flavorId:
            if provider_lc in self.settings and 'default_flavor' in self.settings[provider_lc]:
                self.options.flavorId = self.settings[provider_lc]['default_flavor']

        if not self.options.image:
            if provider_lc in self.settings and 'default_image' in self.settings[provider_lc]:
                self.options.image = self.settings[provider_lc]['default_image']

        if not self.options.public_key:
            if provider_lc in self.settings and 'default_public_key' in self.settings[provider_lc]:
                self.options.public_key = self.settings[provider_lc]['default_public_key']

        if not self.options.script:
            if provider_lc in self.settings and 'default_deploy_script' in self.settings[provider_lc]:
                self.options.script = self.settings[provider_lc]['default_deploy_script']

        # new param
        if not self.options.ex_force_auth_version:
            if provider_lc in self.settings and 'ex_force_auth_version' in self.settings[provider_lc]:
                self.options.ex_force_auth_version = self.settings[provider_lc]['ex_force_auth_version']

        if not self.options.ex_force_auth_url:
            if provider_lc in self.settings and 'ex_force_auth_url' in self.settings[provider_lc]:
                self.options.ex_force_auth_url = self.settings[provider_lc]['ex_force_auth_url']

        if not self.options.ex_force_base_url:
            if provider_lc in self.settings and 'ex_force_base_url' in self.settings[provider_lc]:
                self.options.ex_force_base_url = self.settings[provider_lc]['ex_force_base_url']

        if not self.options.ex_domain_name:
            if provider_lc in self.settings and 'ex_domain_name' in self.settings[provider_lc]:
                self.options.ex_domain_name = self.settings[provider_lc]['ex_domain_name']

        if not self.options.ex_token_scope:
            if provider_lc in self.settings and 'ex_token_scope' in self.settings[provider_lc]:
                self.options.ex_token_scope = self.settings[provider_lc]['ex_token_scope']

        if not self.options.ex_tenant_name:
            if provider_lc in self.settings and 'ex_tenant_name' in self.settings[provider_lc]:
                self.options.ex_tenant_name = self.settings[provider_lc]['ex_tenant_name']

    # INIT: drivers

    def get_driver_compute(self):
        """
        Gets the libcloud driver based on the provider option.
        """
        if hasattr(Provider_Compute, self.options.provider.upper()):
            return get_driver_compute(getattr(Provider_Compute, self.options.provider.upper()))
        else:
            self.fail("Could not find cloud provider with name \"%s\"." %
                      self.options.provider)

    def init_connection(self):
        """
        Initializes connection to cloud provider.
        """
        libcloud.security.VERIFY_SSL_CERT = False
        try:
            self.driver_compute = libcloud.compute.providers.get_driver(self.options.provider)
            self.connection_compute = self.driver_compute(self.options.user,
                                                          self.options.key,
                                                          ex_force_auth_version=self.options.ex_force_auth_version,
                                                          ex_force_auth_url=self.options.ex_force_auth_url,
                                                          ex_force_base_url=self.options.ex_force_base_url,
                                                          ex_domain_name=self.options.ex_domain_name,
                                                          ex_token_scope=self.options.ex_token_scope,
                                                          ex_tenant_name=self.options.ex_tenant_name)

        except libcloud.types.InvalidCredsException:
            self.fail("Invalid or missing credentials for cloud provider.")

    # DISPATCHER

    def dispatch(self):
        """
        Finds and executes the command method.
        """
        arguments = copy.copy(self.arguments)
        options = copy.copy(self.options)

        command = arguments.pop(0) if arguments else 'help'
        method = self.get_command_method(command)
        if not method:
            method = self.cmd_help

        if (method != self.cmd_help):
            self.init_connection()

        return method(options, arguments)

    def get_command_method(self, command):
        """
        Given a command name, returns the command method.
        """
        if not command:
            return None
        cmd_formatted = 'cmd_' + command.replace('-', '_')
        return getattr(self, cmd_formatted, None)

# FORMATTER: docstring

class DocstringHelpFormatter (HelpFormatter):
    """
    Format help based on docstrings.
    """

    def __init__(self, indent_increment=2, max_help_position=40, width=None, short_first=1):
        HelpFormatter.__init__(self, indent_increment,
                               max_help_position, width, short_first)

    def format_usage(self, usage):
        return ("%s\n") % self.trim(usage)

    def format_heading(self, heading):
        return "%*s%s:\n" % (self.current_indent, "", heading)

    def trim(self, docstring):
        """
        Trims a doctring to remove indendation, as per PEP 257
        """
        if not docstring:
            return ''
        lines = docstring.expandtabs().splitlines()
        indent = sys.maxint
        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))
        trimmed = [lines[0].strip()]
        if indent < sys.maxint:
            for line in lines[1:]:
                trimmed.append(line[indent:].rstrip())
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        return '\n'.join(trimmed)

# GLOBAL METHODS

def is_dict_like(obj):
    """
    Checks if the object appears to be dictionary-like.
    """
    if obj and (hasattr(obj, '__dict__') or (hasattr(obj, 'keys') and hasattr(obj, '__getitem__'))):
        return True
    else:
        return False

def is_list_like(obj):
    """
    Checks if the object appears to be list-like.
    """
    if obj and (not hasattr(obj, 'keys')) and hasattr(obj, '__getitem__'):
        return True
    else:
        return False

# MAIN

def main(argv=None):
    bc = Skynet()
    return bc.dispatch()

if __name__ == "__main__":
    sys.exit(main())