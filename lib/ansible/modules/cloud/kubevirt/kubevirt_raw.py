#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2018, KubeVirt Team <@kubevirt>
# Apache License, Version 2.0
# (see LICENSE or http://www.apache.org/licenses/LICENSE-2.0)

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''

module: kubevirt_raw

short_description: Manage KubeVirt objects

description:
    - Use KubeVirt Python SDK to perform CRUD operations on KubeVirt objects.
    - Pass the object definition from a source file or inline.
    - Authenticate using either a config file, certificates, password or token.

version_added: "2.8"

author: KubeVirt Team (@kubevirt)

extends_documentation_fragment:
  - k8s_state_options
  - k8s_name_options
  - k8s_resource_options
  - k8s_auth_options

options:
  merge_type:
    description:
    - Whether to override the default patch merge approach with a specific type. By the default, the strategic
      merge will typically be used.
    - For example, Custom Resource Definitions typically aren't updatable by the usual strategic merge. You may
      want to use C(merge) if you see "strategic merge patch format is not supported"
    - See U(https://kubernetes.io/docs/tasks/run-application/update-api-object-kubectl-patch/#use-a-json-merge-patch-to-update-a-deployment)
    - Requires openshift >= 0.6.2
    - If more than one merge_type is given, the merge_types will be tried in order
    choices:
    - json
    - merge
    - strategic-merge
    type: list
    version_added: "2.7"
    state:

requirements:
  - python >= 2.7
  - openshift >= 0.6.2
'''

EXAMPLES = '''
- name: Create a VM from a source file
  kubevirt_raw:
      state: present
      src: /testing/vm.yml

- name: Create VM defined inline
  kubevirt_raw:
      state: present
      name: testvm
      namespace: vms
      verify_ssl: no
      inline:
          apiVersion: kubevirt.io/v1alpha2
          kind: VirtualMachine
          metadata:
            name: testvm
          spec:
            running: false
            selector:
              matchLabels:
                guest: testvm
            template:
              metadata:
                labels:
                  guest: testvm
                  kubevirt.io/size: small
              spec:
                domain:
                  resources:
                    requests:
                      memory: 64M
                  devices:
                    disks:
                      - name: registrydisk
                        volumeName: registryvolume
                        disk:
                          bus: virtio
                      - name: cloudinitdisk
                        volumeName: cloudinitvolume
                        disk:
                          bus: virtio
                volumes:
                  - name: registryvolume
                    registryDisk:
                      image: kubevirt/cirros-registry-disk-demo
                  - name: cloudinitvolume
                    cloudInitNoCloud:
                      userDataBase64: SGkuXG4=
'''

RETURN = '''
result:
    description:
        - When creating or updating a resource. Otherwise empty.
    returned: success
    type: complex
    contains:
        api_version:
            description: "Version of the schema being used for managing
                          the defined resource."
            returned: success
            type: str
        kind:
            description: The resource type being managed.
            returned: success
            type: str
        metadata:
            description: Standard resource metadata, e.g. name, namespace, etc.
            returned: success
            type: complex
        spec:
            description: "Set of resource attributes, can vary based
                          on the I(api_version) and I(kind)."
            returned: success
            type: complex
        status:
            description: Current status details for the resource.
            returned: success
            type: complex
        wait:
           description: Set to 'true' or 'yes' to block on the action
                        till it completes.
           returned: success
           type: bool
        timeout:
           description: Specifies how much time in seconds to wait for an
                        action to compelte if 'wait' option is enabled.
           returned: success
           type: int
'''

from ansible.module_utils.k8s.raw import KubernetesRawModule

from ansible.module_utils.kubevirt.common import KubeVirtStreamHandler

RAW_ARG_SPEC = {
    'wait': {'type': 'bool', 'default': True},
    'wait_timeout': {'type': 'int', 'default': 20}
}

class KubeVirtVM(KubernetesRawModule):
    def __init__(self, *args, **kwargs):
        super(KubeVirtVM, self).__init__(*args, **kwargs)

    @property
    def argspec(self):
        argspec = copy.deepcopy(NAME_ARG_SPEC)
        argspec.update(copy.deepcopy(RAW_ARG_SPEC))
        return argspec

    def execute_module(self):
        changed = False
        results = []
        self.client = self.get_api_client()
        wait = self.params.get('wait')
        wait_time = self.params.get('wait_timeout')
        for definition in self.resource_definitions:
            kind = definition.get('kind', self.kind)
            search_kind = kind
            if kind.lower().endswith('list'):
                search_kind = kind[:-4]
            api_version = definition.get('apiVersion', self.api_version)
            resource = self.find_resource(search_kind, api_version, fail=True)
            definition = self.set_defaults(resource, definition)
            result = self.perform_action(resource, definition)
            changed = changed or result['changed']
            if wait and state == 'present' and kind == 'persistent_volume_claim':
                w, stream = self._create_stream(resource, namespace, wait_time)
                result = self._read_stream(resource, w, stream, name, replicas)
            results.append(result)

        if len(results) == 1:
            self.exit_json(**results[0])

        self.exit_json(**{
            'changed': changed,
            'result': {
                'results': results
            }
        })

    def _read_stream(self, resource, watcher, stream, name, replicas):
        """ Wait for ready_replicas to equal the requested number of replicas. """
        return_obj = None
        for event in stream:
            if event.get('object'):
                entity = ResourceInstance(resource, event['object'])
                metadata = entity.metadata
                if entity.status.phase == 'Bound':
                    annotations = metadata.annotations if \
                        metadata.annotations else {}
                    IMPORT_STATUS_KEY = 'cdi.kubevirt.io/storage.import.pod.phase'
                    import_status = annotations.get(IMPORT_STATUS_KEY)
                    labels = metadata.labels if metadata.labels else {}
                    if (not self._use_cdi(annotations, labels) or
                            import_status == 'Succeeded'):
                        w.stop()
                        return entity
                    elif entity.status.phase == 'Failed':
                        w.stop()
                        self.fail_json(msg="Failed to import PersistentVolumeClaim")

    def _use_cdi(self, annotations, labels):
        IMPORT_ENDPOINT_KEY = 'cdi.kubevirt.io/storage.import.endpoint'
        endpoint = annotations.get(IMPORT_ENDPOINT_KEY)
        app_label = labels.get('app')
        return endpoint and app_label == 'containerized-data-importer'


def main():
    '''Entry point.'''
    KubernetesRawModule().execute_module()


if __name__ == '__main__':
    main()
