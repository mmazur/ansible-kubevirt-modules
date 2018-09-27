#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2018, KubeVirt Team <@kubevirt>
# Apache License, Version 2.0
# (see LICENSE or http://www.apache.org/licenses/LICENSE-2.0)


class KubeVirtStreamHandler():
    def _create_stream(self, resource, namespace, wait_time):
        """ Create a stream of events for the object """
        w = None
        stream = None
        try:
            w = watch.Watch()
            w._api_client = self.client.client
            stream = w.stream(resource.get, serialize=False, namespace=namespace, timeout_seconds=wait_time)
        except KubernetesException as exc:
            self.fail_json(msg='Failed to initialize watch: {0}'.format(exc.message))
        return w, stream

