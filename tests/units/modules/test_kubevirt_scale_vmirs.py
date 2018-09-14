import json
import sys
import pytest

from ansible.compat.tests.mock import patch
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

from openshift.dynamic import ResourceContainer, ResourceInstance

# FIXME: paths/imports should be fixed before submitting a PR to Ansible
sys.path.append('lib/ansible/modules/cloud/kubevirt')

import kubevirt_scale_vmirs as mymodule


def set_module_args(args):
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught
    by the test case"""
    pass


def exit_json(*args, **kwargs):
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


class TestKubeVirtScaleVMIRSModule(object):
    @pytest.fixture(autouse=True)
    def setup_class(cls, monkeypatch):
        monkeypatch.setattr(
            mymodule.KubeVirtScaleVMIRS, "exit_json", exit_json)
        args = dict(name='freyja', namespace='vms', replicas=2, wait=False)
        set_module_args(args)

    @patch('ansible.module_utils.k8s.raw.KubernetesRawModule.patch_resource')
    @patch('ansible.module_utils.k8s.common.K8sAnsibleMixin.find_resource')
    @patch('openshift.dynamic.ResourceContainer.get')
    def test_scale_vmirs_main(
        self, mock_get_resource, mock_find_resource, mock_patch_resource
    ):
        mock_find_resource.return_value = ResourceContainer({})
        mock_get_resource.return_value = ResourceInstance('', {'metadata': {'name': 'freyja'}, 'spec': {'replicas': 1}})
        mock_patch_resource.return_value = ({}, None)
        with pytest.raises(AnsibleExitJson) as result:
            mymodule.KubeVirtScaleVMIRS().execute_module()
        assert result.value[0]['changed']

    @patch('ansible.module_utils.k8s.raw.KubernetesRawModule.patch_resource')
    @patch('ansible.module_utils.k8s.common.K8sAnsibleMixin.find_resource')
    @patch('openshift.dynamic.ResourceContainer.get')
    def test_scale_vmirs_same_replica_number(
        self, mock_get_resource, mock_find_resource, mock_patch_resource
    ):
        mock_find_resource.return_value = ResourceContainer({})
        mock_get_resource.return_value = ResourceInstance('', {'metadata': {'name': 'freyja'}, 'spec': {'replicas': 2}})
        mock_patch_resource.return_value = ({}, None)
        with pytest.raises(AnsibleExitJson) as result:
            mymodule.KubeVirtScaleVMIRS().execute_module()
        assert not result.value[0]['changed']
