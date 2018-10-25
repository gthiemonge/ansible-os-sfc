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
module: os_sfc_port_pair_group
short_description: Add/Update/Delete port pair groups from OpenStack networking-sfc.
extends_documentation_fragment: openstack
author: "Gregory Thiemonge <gregory.thiemonge@enea.com>"
version_added: "2.5"
description:
  - Add, Update or Remove port pair groups from OpenStack networking-sfc.
options:
  name:
    description:
      - Name that has to be given to the port pair group.
    required: false
    default: None
  port_pairs:
    description:
      - List of service function port pairs.
    required: true
  port_pair_group_parameters:
    description:
      - Dictionary of port pair group parameters.
    required: false
    default: None
'''

EXAMPLES = '''
# Create a port pair group with two named port pairs
- os_sfc_port_pair_group:
    state: present
    auth_url: https://identity.example.com
    username: admin
    password: admin
    project_name: admin
    name: ppg1
    port_pairs:
    - pp1
    - pp2

# Create a port pair group with port pairs' IDs
- os_sfc_port_pair_group:
    state: present
    auth_url: https://identity.example.com
    username: admin
    password: admin
    project_name: admin
    name: ppg2
    port_pairs:
    - ff4983af-fd05-4057-b93d-00fb6e295e81
    - a4dd748a-832c-487f-839e-314f8e950872
'''

RETURN = '''
id:
    description: Unique UUID.
    returned: success
    type: string
name:
    description: Name given to the port pair group.
    returned: success
    type: string
port_pairs:
    description: List of service function port pairs.
    returned: success
    type: list
port_pair_group_parameters:
    description: Dictionary of port pair group parameters.
    returned: success
    type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec, openstack_module_kwargs, openstack_cloud_from_module


def _needs_update(module, ppg, port_pairs, cloud):
    """Check for differences in the updatable values.

    NOTE: We don't currently allow name updates.
    """
    compare_dict = ['port_pair_group_parameters']

    if set(port_pairs) != set(ppg['port_pairs']):
        return True
    for key in compare_dict:
        if module.params[key] is not None and module.params[key] != ppg[key]:
            return True

    return False


def _system_state_change(module, ppg, port_pairs, cloud):
    state = module.params['state']
    if state == 'present':
        if not ppg:
            return True
        return _needs_update(module, ppg, port_pairs, cloud)
    if state == 'absent' and ppg:
        return True
    return False


def _compose_port_pair_group_args(module, cloud, port_pairs):
    ppg_kwargs = {}
    optional_parameters = ['name',
                           'port_pair_group_parameters']
    for optional_param in optional_parameters:
        if module.params[optional_param] is not None:
            ppg_kwargs[optional_param] = module.params[optional_param]
    ppg_kwargs['port_pairs'] = port_pairs

    return ppg_kwargs


def _port_pairs_get_ids(module, cloud, fail_on_error=True):
    port_pair_ids = module.params['port_pairs']
    if not port_pair_ids:
        if fail_on_error:
            module.fail_json(
                msg="Parameter 'port_pairs' is required in Sfc Port Pair Group Create"
            )
        return None

    port_pairs = []
    for pp_name in port_pair_ids:
        pp = cloud.get_sfc_port_pair(pp_name)
        if pp is None:
            if fail_on_error:
                module.fail_json(
                    msg="Specified port pair `%s' was not found." % (pp_name)
                )
        port_pairs.append(pp['id'])

    return port_pairs


def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=False),
        port_pairs=dict(type='list', default=None),
        port_pair_group_parameters=dict(type='dict', default=None),
        state=dict(default='present', choices=['absent', 'present']),
    )

    module = AnsibleModule(argument_spec,
                           supports_check_mode=True)

    name = module.params['name']
    state = module.params['state']

    shade, cloud = openstack_cloud_from_module(module)
    shade.simple_logging(debug=True)
    try:
        ppg = None
        if name:
            ppg = cloud.get_sfc_port_pair_group(name)

        if module.check_mode:
            port_pairs_ids = _port_pairs_get_ids(module, cloud, fail_on_error=False)
            module.exit_json(changed=_system_state_change(module, ppg, port_pairs_ids, cloud))

        changed = False
        if state == 'present':
            port_pairs_ids = _port_pairs_get_ids(module, cloud)

            if not ppg:
                ppg_kwargs = _compose_port_pair_group_args(module, cloud, port_pairs_ids)

                ppg = cloud.create_sfc_port_pair_group(**ppg_kwargs)
                changed = True
            else:
                if _needs_update(module, ppg, port_pairs_ids, cloud):
                    ppg_kwargs = _compose_port_pair_groups_args(module, cloud, port_pairs_ids)
                    ppg = cloud.update_sfc_port_pair(ppg['id'], **ppg_kwargs)
                    changed = True
            module.exit_json(changed=changed, id=ppg['id'], port_pair_group=ppg)

        if state == 'absent':
            if ppg:
                cloud.delete_sfc_port_pair_group(ppg['id'])
                changed = True
            module.exit_json(changed=changed)

    except shade.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
