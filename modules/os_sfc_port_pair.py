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
module: os_sfc_port_pair
short_description: Add/Update/Delete port pairs from OpenStack networking-sfc.
extends_documentation_fragment: openstack
author: "Gregory Thiemonge <gregory.thiemonge@enea.com>"
version_added: "2.5"
description:
  - Add, Update or Remove port pairs from OpenStack networking-sfc.
options:
  name:
    description:
      - Name that has to be given to the port pair.
    required: false
    default: None
  ingress:
    description:
      - ID or name of the ingress port.
    required: true
  egress:
    description:
      - ID or name of the egress port.
    required: false
    default: None
  service_function_parameters:
    description:
      - Parameters of the port pair with dictionary structure.
    required: false
    default: None
'''

EXAMPLES = '''
# Create a port pair
- os_sfc_port_pair:
    state: present
    auth_url: https://identity.example.com
    username: admin
    password: admin
    project_name: admin
    name: pp1
    ingress: port1
    egress: port2

# Create a port pair with NSH correlation
- os_sfc_port_pair:
    state: present
    auth_url: https://identity.example.com
    username: admin
    password: admin
    project_name: admin
    name: pp1
    ingress: b1f02d59-f2b6-4604-befc-f5290dbb27d3
    egress: 837ef6d9-5582-4f51-a2fc-a561bcaf30c7
    service_function_parameters:
        correlation: nsh
'''

RETURN = '''
id:
    description: Unique UUID.
    returned: success
    type: string
name:
    description: Name given to the port pair.
    returned: success
    type: string
ingress:
    description: ID or name of the ingress port.
    returned: success
    type: string
egress:
    description: ID or name of the egress port.
    returned: success
    type: string
service_function_parameters:
    description: Parameters of the port pair with dictionary structure.
    returned: success
    type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec, openstack_module_kwargs, openstack_cloud_from_module


def _needs_update(module, pp, ports, cloud):
    """Check for differences in the updatable values.

    NOTE: We don't currently allow name updates.
    """
    compare_simple = ['ingress',
                      'egress']
    compare_dict = ['service_function_parameters']

    for key in compare_simple:
        value = ports.get(key, pp[key])
        if module.params[key] is not None and module.params[key] != value:
            return True
    for key in compare_dict:
        if module.params[key] is not None and module.params[key] != pp[key]:
            return True

    return False


def _system_state_change(module, pp, ports, cloud):
    state = module.params['state']
    if state == 'present':
        if not pp:
            return True
        return _needs_update(module, pp, ports, cloud)
    if state == 'absent' and pp:
        return True
    return False


def _compose_port_pair_args(module, cloud):
    pp_kwargs = {}
    optional_parameters = ['name',
                           'ingress',
                           'egress',
                           'service_function_parameters']
    for optional_param in optional_parameters:
        if module.params[optional_param] is not None:
            pp_kwargs[optional_param] = module.params[optional_param]

    return pp_kwargs


def _ports_get_ids(module, cloud, fail_on_error=True):
    ports_ids = {}

    ingress = module.params['ingress']
    if not ingress:
        if fail_on_error:
            module.fail_json(
                msg="Parameter 'ingress' is required in Sfc Port Pair Create"
            )
        return port_ids

    egress = module.params['egress']
    if not egress:
        if fail_on_error:
            module.fail_json(
                msg="Parameter 'egress' is required in Sfc Port Pair Create"
            )
        return port_ids

    ingress_port = cloud.get_port(ingress)
    if ingress_port is None:
        if fail_on_error:
            module.fail_json(
                msg="Specified ingress port was not found."
            )
    else:
        ports_ids['ingress'] = ingress_port['id']

    egress_port = cloud.get_port(egress)
    if egress_port is None:
        if fail_on_error:
            module.fail_json(
                msg="Specified egress port was not found."
            )
    else:
        ports_ids['egress'] = egress_port['id']

    return ports_ids


def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=False),
        ingress=dict(default=None),
        egress=dict(default=None),
        service_function_parameters=dict(type='dict', default=None),
        state=dict(default='present', choices=['absent', 'present']),
    )

    module = AnsibleModule(argument_spec,
                           supports_check_mode=True)

    name = module.params['name']
    state = module.params['state']

    shade, cloud = openstack_cloud_from_module(module)
    shade.simple_logging(debug=True)
    try:
        pp = None
        if name:
            pp = cloud.get_sfc_port_pair(name)

        if module.check_mode:
            ports = _ports_get_ids(module, cloud, fail_on_error=False)
            module.exit_json(changed=_system_state_change(module, pp, ports, cloud))

        changed = False
        if state == 'present':
            ports = _ports_get_ids(module, cloud)
            if not pp:

                pp_kwargs = _compose_port_pair_args(module, cloud)
                pp_kwargs['ingress'] = ports['ingress']
                pp_kwargs['egress'] = ports['egress']

                pp = cloud.create_sfc_port_pair(**pp_kwargs)
                changed = True
            else:
                if _needs_update(module, pp, ports, cloud):
                    pp_kwargs = _compose_port_pair_args(module, cloud)
                    pp = cloud.update_sfc_port_pair(pp['id'], **pp_kwargs)
                    changed = True
            module.exit_json(changed=changed, id=pp['id'], port_pair=pp)

        if state == 'absent':
            if pp:
                cloud.delete_sfc_port_pair(pp['id'])
                changed = True
            module.exit_json(changed=changed)

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
