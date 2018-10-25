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
module: os_sfc_port_chain
short_description: Add/Update/Delete port chains from OpenStack networking-sfc.
extends_documentation_fragment: openstack
author: "Gregory Thiemonge <gregory.thiemonge@enea.com>"
version_added: "2.5"
description:
  - Add, Update or Remove port chains from OpenStack networking-sfc.
options:
  name:
    description:
      - Name that has to be given to the port chain.
    required: false
    default: None
  port_pair_groups:
    description:
      - List of port pair groups.
    required: true
  flow_classifiers:
    description:
      - List of flow classifiers.
    required: False
    default: None
  chain_parameters:
    description:
      - Dictionary of parameters ('correlation': string).
    required: false
    default: { 'correlation': 'mpls' }
  chain_id:
    description:
      - Data-plane chain path ID.
    required: false
    default: None
'''

EXAMPLES = '''
# Create a port chain with NSH correlation:
- os_sfc_port_chain:
    state: present
    auth_url: https://identity.example.com
    username: admin
    password: admin
    project_name: admin
    name: pc1
    port_pair_groups
    - 56859f1d-b801-4316-888f-a2fad2959b5e
    flow_classifiers:
    - 98cf1406-1e0e-4980-8f3e-98dfc4ba561c
    chain_id: 1
    chain_parameters:
        correlation: nsh
'''

RETURN = '''
id:
    description: Unique UUID.
    returned: success
    type: string
name:
    description: Name given to the port chain.
    returned: success
    type: string
port_pair_groups:
    description: List of port pair groups.
    returned: success
    type: list
flow_classifiers:
    description: List of flow classifiers.
    returned: success
    type: list
chain_parameters:
    description: Dictionary of parameters ('correlation': string).
    returned: success
    type: dict
chain_id:
    description: Data-plane chain path ID.
    returned: success
    type: integer
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec, openstack_module_kwargs, openstack_cloud_from_module


def _needs_update(module, pc, pc_ids, cloud):
    """Check for differences in the updatable values.

    NOTE: We don't currently allow name updates.
    """
    compare_simple = ['chain_id']
    compare_list = ['port_pair_groups',
                    'flow_classifiers']
    compare_dict = ['chain_parameters']

    for key in compare_simple:
        value = pc_ids.get(key, pc[key])
        if module.params[key] is not None and module.params[key] != value:
            return True
    for key in compare_list:
        value = pc_ids.get(key, pc[key])
        if module.params[key] is not None and (set(module.param[key]) !=
                                               set(value)):
            return True
    for key in compare_dict:
        if module.params[key] is not None and module.params[key] != value:
            return True

    return False


def _system_state_change(module, pc, pc_ids, cloud):
    state = module.params['state']
    if state == 'present':
        if not pc:
            return True
        return _needs_update(module, pc, pc_ids, cloud)
    if state == 'absent' and pc:
        return True
    return False


def _compose_port_chain_args(module, pc_ids, cloud):
    pc_kwargs = {}
    optional_parameters = ['name',
                           'port_pair_groups',
                           'flow_classifiers',
                           'chain_parameters',
                           'chain_id']
    for optional_param in optional_parameters:
        if module.params[optional_param] is not None:
            value = pc_ids.get(optional_param,
                               module.params[optional_param])
            pc_kwargs[optional_param] = value

    return pc_kwargs


def _port_chains_get_ids(module, cloud, fail_on_error=True):
    pc_ids = {
        'port_pair_groups': [],
        'flow_classifiers': [],
    }

    ppg_names = module.params['port_pair_groups']
    if not ppg_names:
        if fail_on_error:
            module.fail_json(
                msg="Parameter 'port_pair_groups' is required in Sfc Port Chain Create"
            )
        return None

    for ppg_name in ppg_names:
        ppg = cloud.get_sfc_port_pair_group(ppg_name)
        if ppg is None:
            if fail_on_error:
                module.fail_json(
                    msg="Specified port pair group `%s' wat not found." % (ppg_name)
                )
            return None
        pc_ids['port_pair_groups'].append(ppg['id'])

    fc_names = module.params['flow_classifiers']
    if not fc_names:
        if fail_on_error:
            module.fail_json(
                msg="Parameter 'flow_classifiers' is required in Sfc Port Chain Create"
            )
        return None

    for fc_name in fc_names:
        fc = cloud.get_sfc_flow_classifier(fc_name)
        if fc is None:
            if fail_on_error:
                module.fail_json(
                    msg="Specified port pair group `%s' wat not found." % (fc_name)
                )
            return None
        pc_ids['flow_classifiers'].append(fc['id'])

    return pc_ids


def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=False),
        port_pair_groups=dict(type='list', default=None),
        flow_classifiers=dict(type='list', default=None),
        chain_parameters=dict(type='dict', default=None),
        chain_id=dict(default=None),
        state=dict(default='present', choices=['absent', 'present']),
    )

    module = AnsibleModule(argument_spec,
                           supports_check_mode=True)

    name = module.params['name']
    state = module.params['state']

    shade, cloud = openstack_cloud_from_module(module)
    shade.simple_logging(debug=True)
    try:
        pc = None
        if name:
            pc = cloud.get_sfc_port_chain(name)

        if module.check_mode:
            pc_ids = _port_chains_get_ids(module, cloud, fail_on_error=False)
            module.exit_json(changed=_system_state_change(module, pc, pc_ids, cloud))

        changed = False
        if state == 'present':
            pc_ids = _port_chains_get_ids(module, cloud)

            if not pc:
                pc_kwargs = _compose_port_chain_args(module, pc_ids, cloud)

                pc = cloud.create_sfc_port_chain(**pc_kwargs)
                changed = True
            else:
                if _needs_update(module, pc, pc_ids, cloud):
                    pc_kwargs = _compose_port_chain_args(module, pc_ids, cloud)
                    pc = cloud.update_sfc_port_chain(pc['id'], **pc_kwargs)
                    changed = True
            module.exit_json(changed=changed, id=pc['id'], port_chain=pc)

        if state == 'absent':
            if pc:
                cloud.delete_sfc_port_chain(pc['id'])
                changed = True
            module.exit_json(changed=changed)

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
