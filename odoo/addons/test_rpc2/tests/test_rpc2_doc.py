import os
import os.path
import platform
import resource
import subprocess as sp
import tempfile
import xmlrpc.client

from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import urlparse

import odoo
from odoo.tests.common import (
    get_db_name, tagged, Transport, HttpCase, RecordCapturer
)
from odoo.tools import jsonrpc_client
from odoo.tools.which import which_files

from odoo.addons.base.controllers.rpc import Rpc2


failure_message__please_sync_doc = """\
This test file covers all the JSON-RPC and XML-RPC examples from the \
External API documentation. Either (1) your code contains mistakes that \
must be solved, or (2) the documentation is not up to date. In the later \
case, please update the test files for the other languages too. They are \
located in the same folder as this python test file.
"""

is_linux_like = (os.name == 'posix' and platform.system() != 'Darwin')

# We only run test_rpc2.{ext} in subprocesses
# in case we find a tool for the job
node_path = next(which_files('node'), None)
ruby_path = next(which_files('ruby'), None)
php_path = next(which_files('php'), None)
javac_path = next(which_files('javac'), None)
java_path = next(which_files('java'), None)
bash_path = next(which_files('bash'), None)
curl_path = next(which_files('curl'), None)
jq_path = next(which_files('jq'), None)


@tagged('-at_install', 'post_install')
class _RpcDocCase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base_url = urlparse(cls.base_url())
        cls.scheme, cls.domain, cls.database, cls.username, cls.password = \
        cls.argv = [
            base_url.scheme, base_url.netloc, get_db_name(), 'admin', 'admin'
        ]

class _RpcDocMixin:
    # pylint: disable=bad-whitespace

    def test_rpc2_doc_00_common(self):
        self.assertEqual(self.common.version(), {
            "server_version": odoo.release.version,
            "server_version_info": list(odoo.release.version_info),
            "server_serie": odoo.release.serie,
            "protocol_version": 1
        }, failure_message__please_sync_doc)

    def test_rpc2_doc_01_models(self):
        self.assertIsNone(
            self.models.system.noop(),
            failure_message__please_sync_doc
        )

    def test_rpc2_doc_02_check_access_rights(self):
        models = self.models

        #<a id=check_access_rights>
        partners = models.res.partner
        can_access = partners.check_access_rights({
            'args': ['read'],
            'kwargs': {
                'raise_exception': False,
            },
        })
        #</a>

        self.assertTrue(can_access, failure_message__please_sync_doc)

    def test_rpc2_doc_03_list(self):
        models = self.models

        #<a id=list>
        partners = models.res.partner
        record_ids = partners.search({
            'kwargs': {
                'domain': [('is_company', '=', False)],
            },
        })
        #</a>

        self.assertEqual(
            record_ids,
            self.env['res.partner'].search(
                [('is_company', '=', False)]
            ).ids,
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_04_pagination(self):
        models = self.models

        #<a id=pagination>
        partners = models.res.partner
        record_ids = partners.search({
            'kwargs': {
                'domain': [('is_company', '=', False)],
                'offset': 10,
                'limit': 5,
            },
        })
        #</a>

        self.assertEqual(
            record_ids,
            self.env['res.partner'].search(
                [('is_company', '=', False)],
                offset=10, limit=5,
            ).ids,
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_05_count(self):
        models = self.models

        #<a id=count>
        partners = models.res.partner
        count = partners.search_count({
            'kwargs': {
                'domain': [('is_company', '=', False)],
            },
        })
        #</a>

        self.assertEqual(
            count,
            self.env['res.partner'].search_count(
                [('is_company', '=', False)]
            ),
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_06_search_read(self):
        models = self.models

        #<a id=search_read>
        partners = models.res.partner
        [record_data] = partners.search_read({
            'kwargs': {
                'domain': [('is_company', '=', False)],
                'fields': ['name', 'title', 'parent_name'],
                'limit': 1,
            }
        })
        #</a>

        self.assertEqual(
            record_data,
            self.env['res.partner'].search_read(
                [('is_company', '=', False)],
                ['name', 'title', 'parent_name'],
                limit=1,
            )[0],
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_07_read(self):
        models = self.models

        # The documentation states "using the first record we fetched in
        # the search example", hence this weird code.
        records = self.env['res.partner'].search(
            [('is_company', '=', False)], limit=1)
        record_ids = records.ids

        #<a id=read>
        partners = models.res.partner
        [record_data] = partners.read({
            'records': record_ids,
            'kwargs': {
                'fields': ['name', 'title', 'parent_name'],
            }
        })
        #</a>

        self.assertEqual(
            record_data,
            records.read(['name', 'title', 'parent_name'])[0],
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_08_fields_get(self):
        models = self.models

        #<a id=fields_get>
        banks = models.res.bank
        fields = banks.fields_get({
            'kwargs': {'attributes': ['type', 'string']}
        })
        #</a>

        self.assertEqual(
            fields,
            self.env['res.bank'].fields_get(attributes=['type', 'string']),
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_09_create(self):
        models = self.models

        with RecordCapturer(self.env['res.partner'], []) as capture:
            #<a id=create>
            partners = models.res.partner
            new_record_ids = partners.create({
                'args': [ [{'name': "New Partner"}] ],
            })
            #</a>

        self.assertEqual(len(capture.records), 1)
        self.assertEqual(
            capture.records.ids, new_record_ids,
            failure_message__please_sync_doc,
        )
        self.assertEqual(
            capture.records.name, "New Partner",
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_10_write(self):
        models = self.models

        new_record = self.env['res.partner'].create({
            'name': "New Partner"
        })
        new_record_ids = new_record.ids

        #<a id=write>
        partners = models.res.partner
        partners.write({
            'records': new_record_ids,
            'args': [{'name': "Newer Partner"}],
        })
        # get record name after having changed it
        records_name = partners.name_get({'records': new_record_ids})
        #</a>

        self.assertEqual(
            records_name, [[new_record_ids[0], "Newer Partner"]],
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_11_unlink(self):
        models = self.models

        new_record = self.env['res.partner'].create({
            'name': "New Partner"
        })
        new_record_ids = new_record.ids

        #<a id=unlink>
        partners = models.res.partner
        partners.unlink({'records': new_record_ids})
        # check if the deleted record is still in the database
        records = partners.exists({'records': new_record_ids})
        #</a>

        self.assertEqual(records, [], failure_message__please_sync_doc)

    def test_rpc2_doc_12_ir_model(self):
        models = self.models

        #<a id=ir.model>
        # create the model
        [x_custom_model_id] = models.ir.model.create({
            'args': [ [{
                'name': "Custom Model",
                'model': 'x_custom_model',
                'state': 'manual',
            }] ],
        })

        # grant the admin CRUD operations
        system_group_id = models.ir.model.data.check_object_reference({
            'args': ['base', 'group_system']
        })[1]
        models.ir.model.access.create({
            'args': [ [{
                'name': 'access_x_custom_model_admin',
                'model_id': x_custom_model_id,
                'group_id': system_group_id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': True,
            }] ],
        })

        # get the fields
        x_custom_model_fields = models.x_custom_model.fields_get({
            'kwargs': {'attributes': ['type', 'string']},
        })
        #</a>

        self.assertEqual(
            x_custom_model_fields,
            {
                "create_date":   {"type": "datetime", "string": "Created on"},
                "create_uid":    {"type": "many2one", "string": "Created by"},
                "display_name":  {"type": "char",     "string": "Display Name"},
                "id":            {"type": "integer",  "string": "ID"},
                "write_date":    {"type": "datetime", "string": "Last Updated on"},
                "write_uid":     {"type": "many2one", "string": "Last Updated by"},
                "x_name":        {"type": "char",     "string": "Name"},
            },
            failure_message__please_sync_doc,
        )

    def test_rpc2_doc_13_ir_model_fields(self):
        models = self.models

        x_custom_model_id = self.env['ir.model'].create([{
            'name': "Custom Model",
            'model': 'x_custom_model',
            'state': 'manual'
        }]).id
        self.env['ir.model.access'].create([{
            'name': 'access_x_custom_model_admin',
            'model_id': x_custom_model_id,
            'group_id': self.env.ref('base.group_system').id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        }])

        #<a id=ir.model.fields>
        # add a new field "x_foo" on "x_custom_model"
        models.ir.model.fields.create({
            'args': [ [{
                'model_id': x_custom_model_id,  # above example
                'name': 'x_foo',
                'ttype': 'char',
                'state': 'manual',
            }] ]
        })

        # create a new record and read it
        x_record_ids = models.x_custom_model.create({
            'args': [ [{'x_foo': "test record"}] ],
        })
        [x_record_data] = models.x_custom_model.read({
            'records': x_record_ids,
            'kwargs': {
                'fields': ['x_foo']
            }
        })
        #</a>

        self.assertEqual(
            x_record_data, {'id': x_record_ids[0], 'x_foo': "test record"},
            failure_message__please_sync_doc
        )

class TestXmlRpcDocumentation(_RpcDocCase, _RpcDocMixin):

    # pylint: disable=pointless-string-statement
    def setUp(self):
        super().setUp()

        """<a id=xmlcommon>
        common = xmlrpc.client.ServerProxy(
            f'{scheme}://{domain}/RPC2',
            allow_none=True,
        )
        version = common.version()
        </a>"""
        self.common = xmlrpc.client.ServerProxy(
            f'{self.scheme}://{self.domain}/RPC2',
            transport=Transport(self.cr),
            allow_none=True,
        )

        """<a id=xmlmodels>
        models = xmlrpc.client.ServerProxy(
            f'{scheme}://{username}:{password}@{domain}/RPC2/{database}',
            allow_none=True,
        )
        models.system.noop()
        </a>"""
        self.models = xmlrpc.client.ServerProxy(
            (f'{self.scheme}://{self.username}:{self.password}@'
             f'{self.domain}/RPC2?db={self.database}'),
            transport=Transport(self.cr),
            allow_none=True,
        )

class TestJsonRpcDocumentation(_RpcDocCase, _RpcDocMixin):

    # pylint: disable=pointless-string-statement
    def setUp(self):
        super().setUp()

        """<a id=jsoncommon>
        common = jsonrpc_client.proxy(scheme, domain)
        common.version()
        </a>"""
        self.common = jsonrpc_client.proxy(
            self.scheme, self.domain, requests=self.opener)

        """<a id=jsonmodels>
        models = jsonrpc_client.proxy(
            scheme, domain, database, username, password
        )
        models.system.noop()
        </a>"""
        self.models = jsonrpc_client.proxy(
            self.scheme, self.domain,
            self.database, self.username, self.password,
            requests=self.opener
        )

class TestManyLangsRpcDocumentation(_RpcDocCase):
    def setUp(self):
        super().setUp()
        real_rpc2_endpoint = Rpc2.rpc2.original_endpoint
        patcher = patch.object(Rpc2.rpc2, 'original_endpoint')
        self.rpc2_endpoint = patcher.start()
        self.rpc2_endpoint.side_effect = real_rpc2_endpoint
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.assertEqual(self.rpc2_endpoint.call_count, 21,
            "Not all examples have been run.")
        super().tearDown()

    @skipUnless(node_path, "Missing NodeJS")
    def test_rpc2_doc_node(self):
        script = __file__.removesuffix('.py') + '.js'
        with open('result2.json', 'w') as f:
            proc = sp.run(
                [node_path, '--unhandled-rejections=strict', script, *self.argv],
                stdout=f, stderr=sp.PIPE, check=False, text=True,
                env={'NODE_PATH': '/tmp/node_modules'}
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    @skipUnless(ruby_path, "Missing Ruby")
    def test_rpc2_doc_ruby(self):
        script = __file__.removesuffix('.py') + '.rb'
        proc = sp.run(
            [ruby_path, script, *self.argv],
            stderr=sp.PIPE, check=False, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    @skipUnless(php_path, "Missing PHP")
    def test_rpc2_doc_php(self):
        script = __file__.removesuffix('.py') + '.php'
        proc = sp.run(
            [php_path, script, *self.argv],
            stderr=sp.PIPE, check=False, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    @skipUnless(javac_path and java_path, "Missing java or javac")
    def test_rpc2_doc_java(self):

        def unlimit_virtual_memory():
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))

        sourcepath = os.path.dirname(__file__)
        classname = os.path.basename(__file__).removesuffix('.py')
        classpath = [
            '.',
            '/tmp/apache-xmlrpc-3.1.3/lib/ws-commons-util-1.0.2.jar',
            '/tmp/apache-xmlrpc-3.1.3/lib/xmlrpc-client-3.1.3.jar',
            '/tmp/apache-xmlrpc-3.1.3/lib/xmlrpc-common-3.1.3.jar',
        ]
        with tempfile.TemporaryDirectory(prefix='odoo-rpc2') as buildpath:

            proc_build = sp.run(
                [
                    javac_path,
                    '-d', buildpath,
                    '-classpath', ':'.join(classpath),
                    f'{classname}.java'
                ],
                check=False, cwd=sourcepath,
                stdout=sp.PIPE, stderr=sp.STDOUT, text=True,
                preexec_fn=unlimit_virtual_memory if is_linux_like else None,
            )
            self.assertEqual(
                proc_build.returncode, 0,
                "Compilation failed!\n" + proc_build.stdout
            )

            proc_run = sp.run(
                [
                    java_path,
                    '-classpath', ':'.join(classpath),
                    classname, *self.argv
                ],
                check=False, cwd=buildpath,
                stdout=sp.PIPE, stderr=sp.STDOUT, text=True,
                preexec_fn=unlimit_virtual_memory if is_linux_like else None,
            )
            self.assertEqual(
                proc_run.returncode, 0,
                "Execution failed!\n" + proc_run.stdout
            )

    @skipUnless(bash_path and curl_path and jq_path, "Missing bash, curl or jq")
    def test_rpc2_doc_curl(self):
        script = __file__.removesuffix('.py') + '.sh'
        proc = sp.run(
            [bash_path, script, *self.argv],
            stdout=sp.DEVNULL, stderr=sp.PIPE, check=False, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
