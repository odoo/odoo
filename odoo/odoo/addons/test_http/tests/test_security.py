import json
from .test_common import TestHttpBase


class TestHttpSecurity(TestHttpBase):
    def test_httprequest_attrs(self):
        res = self.db_url_open('/test_http/httprequest_attrs')
        result = json.loads(res.content)
        self.assertNotIn('user_agent_class', result)
        self.assertNotIn('parameter_storage_class', result)

    def test_httprequest_environ(self):
        res = self.db_url_open('/test_http/httprequest_environ')
        result = json.loads(res.content)
        self.assertNotIn('wsgi.input', result)
        self.assertNotIn('werkzeug.socket', result)
        self.assertNotIn('socket', result)
