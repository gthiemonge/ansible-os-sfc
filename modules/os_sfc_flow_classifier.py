#!/usr/bin/python

# Copyright (c) 2018 Enea
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: os_sfc_flow_classifier
short_description: Add/Update/Delete flow classifiers from OpenStack networking-sfc.
extends_documentation_fragment: openstack
author: "Gregory Thiemonge <gregory.thiemonge@enea.com>"
version_added: "2.5"
description:
  - Add, Update or Remove flow classifiers from OpenStack networking-sfc.
options:
  name:
    description:
      - Name that has to be given to the flow classifier.
    required: false
    default: None
  ethertype:
    description:
      - L2 ethertype. Can be 'IPv4' or 'IPv6' only.
    required: false
    default: IPv4
  protocol:
    description:
      - IP protocol name
    required: false
    default: None
  source_port_range_min:
    description:
      - Minimum source protocol port.
    required: false
    default: None
  source_port_range_max:
    description:
      - Maximum source protocol port.
    required: false
    default: None
  destination_port_range_min:
    description:
      - Minimum destination protocol port.
    required: false
    default: None
  destination_port_range_max:
    description:
      - Maximum destination protocol port.
    required: false
    default: None
  source_ip_prefix:
    description:
      - Source IPv4 or IPv6 prefix.
    required: false
    default: None
  destination_ip_prefix:
    description:
      - Destination IPv4 or IPv6 prefix.
    required: false
    default: None
  logical_source_port:
    description:
      - Neutron source port.
    required: false
    default: None
  logical_destination_port:
    description:
      - Neutron destination port.
    required: false
    default: None
  l7_parameters:
    description:
      - Dictionary of L7 parameters.
    required: true
    default: None
'''

EXAMPLES = '''
# Create a simple flow classifier
- os_sfc_flow_classifier:
    state: present
    auth_url: https://identity.example.com
    username: admin
    password: admin
    project_name: admin
    name: fc1
    source_ip_prefix: 10.20.0.0/24
    destination_ip_prefix: 10.22.2.0/24
'''

RETURN = '''
id:
    description: Unique UUID.
    returned: success
    type: string
ethertype:
    description: L2 ethertype. Can be 'IPv4' or 'IPv6' only.
    returned: success
    type: string
protocol:
    description: IP protocol name
    returned: success
    type: string
source_port_range_min:
    description: Minimum source protocol port.
    returned: success
    type: integer
source_port_range_max:
    description: Maximum source protocol port.
    returned: success
    type: integer
destination_port_range_min:
    description: Minimum destination protocol port.
    returned: success
    type: integer
destination_port_range_max:
    description: Maximum destination protocol port.
    returned: success
    type: integer
source_ip_prefix:
    description: Source IPv4 or IPv6 prefix.
    returned: success
    type: string
destination_ip_prefix:
    description: Destination IPv4 or IPv6 prefix.
    returned: success
    type: string
logical_source_port:
    description: Neutron source port.
    returned: success
    type: string
logical_destination_port:
    description: Neutron destination port.
    returned: success
    type: string
l7_parameters:
    description: Dictionary of L7 parameters.
    returned: success
    type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec, openstack_module_kwargs, openstack_cloud_from_module


def _needs_update(module, fc, ports, cloud):
    """Check for differences in the updatable values.

    NOTE: We don't currently allow name updates.
    """
    compare_simple = ['ethertype',
                      'protocol',
                      'source_port_range_min',
                      'source_port_range_max',
                      'destination_port_range_min',
                      'destination_port_range_max',
                      'source_ip_prefix',
                      'destination_ip_prefix',
                      'logical_source_port',
                      'logical_destination_port']
    compare_dict = ['l7_parameters']

    for key in compare_simple:
        value = ports.get(key, fc[key])
        if module.params[key] is not None and module.params[key] != value:
            return True
    for key in compare_dict:
        if module.params[key] is not None and module.params[key] != fc[key]:
            return True

    return False


def _system_state_change(module, fc, ports, cloud):
    state = module.params['state']
    if state == 'present':
        if not fc:
            return True
        return _needs_update(module, fc, ports, cloud)
    if state == 'absent' and fc:
        return True
    return False


def _compose_flow_classifier_args(module, cloud, ports):
    fc_kwargs = {}
    optional_parameters = ['name',
                           'ethertype',
                           'protocol',
                           'source_port_range_min',
                           'source_port_range_max',
                           'destination_port_range_min',
                           'destination_port_range_max',
                           'source_ip_prefix',
                           'destination_ip_prefix',
                           'l7_parameters']
    for optional_param in optional_parameters:
        if module.params[optional_param] is not None:
            fc_kwargs[optional_param] = module.params[optional_param]

    if 'logical_source_port' in ports:
        fc_kwargs['logical_source_port'] = ports['logical_source_port']
    if 'logical_destination_port' in ports:
        fc_kwargs['logical_destination_port'] = ports['logical_destination_port']

    return fc_kwargs


def _ports_get_ids(module, cloud, fail_on_error=False):
    ports_ids = {}

    logical_source_port = module.params['logical_source_port']
    if logical_source_port is not None:
        src_port = cloud.get_port(logical_source_port)
        if src_port is None:
            if fail_on_error:
                module.fail_json(
                    msg="Specified logical source port was not found."
                )
        else:
            ports_ids['logical_source_port'] = src_port['id']

    logical_destination_port = module.params['logical_destination_port']
    if logical_destination_port is not None:
        dst_port = cloud.get_port(logical_destination_port)
        if dst_port is None:
            if fail_on_error:
                module.fail_json(
                    msg="Specified logical destination port was not found."
                )
        else:
            ports_ids['logical_destination_port'] = dst_port['id']

    return ports_ids


def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=False),
        ethertype=dict(default=None),
        protocol=dict(default=None),
        source_port_range_min=dict(default=None),
        source_port_range_max=dict(default=None),
        destination_port_range_min=dict(default=None),
        destination_port_range_max=dict(default=None),
        source_ip_prefix=dict(default=None),
        destination_ip_prefix=dict(default=None),
        logical_source_port=dict(default=None),
        logical_destination_port=dict(default=None),
        l7_parameters=dict(type='dict', default=None),
        state=dict(default='present', choices=['absent', 'present']),
    )

    module = AnsibleModule(argument_spec,
                           supports_check_mode=True)

    name = module.params['name']
    state = module.params['state']

    shade, cloud = openstack_cloud_from_module(module)
    shade.simple_logging(debug=True)
    try:
        fc = None
        if name:
            fc = cloud.get_sfc_flow_classifier(name)

        if module.check_mode:
            ports = _ports_get_ids(module, cloud, fail_on_error=False)
            module.exit_json(changed=_system_state_change(module, fc, ports, cloud))

        changed = False
        if state == 'present':
            ports = _ports_get_ids(module, cloud)

            if not fc:
                fc_kwargs = _compose_flow_classifier_args(module, cloud, ports)

                fc = cloud.create_sfc_flow_classifier(**fc_kwargs)
                changed = True
            else:
                if _needs_update(module, fc, ports, cloud):
                    fc_kwargs = _compose_flow_classifier_args(module, cloud, ports)
                    fc = cloud.update_sfc_flow_classifier(fc['id'], **fc_kwargs)
                    changed = True
            module.exit_json(changed=changed, id=fc['id'], flow_classifier=fc)

        if state == 'absent':
            if fc:
                cloud.delete_sfc_flow_classifier(fc['id'])
                changed = True
            module.exit_json(changed=changed)

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
