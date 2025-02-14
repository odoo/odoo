import textwrap
from http import HTTPStatus

from werkzeug.http import parse_options_header

from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestDoc(HttpCaseWithUserDemo):
    def test_doc_web_client(self):
        self.authenticate('demo', 'demo')
        res = self.url_open('/doc', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'text/html; charset=utf-8')
        self.assertTrue(res.content, "There must be a rich web client")

    def test_doc_index(self):
        self.authenticate('demo', 'demo')
        res = self.url_open('/doc/index.json', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

        json = res.json()
        self.assertEqual(set(json), {'models', 'modules'})

        self.assertGreater(set(json['modules']), {'base', 'web'})
        # if we ever enable module sorting
        # self.assertLess(
        #     json['modules'].index('base'),
        #     json['modules'].index('web'),
        #     "verify that both base and web are installed, and that "
        #     "they are ordered according to the dependency graph",
        # )

        res_partner = next(
            (model for model in json['models'] if model['model'] == 'res.partner'),
            None,
        )
        self.assertTrue(res_partner, "res.partner not found in json['models']")
        res_partner_fields = res_partner.pop('fields')
        res_partner_methods = res_partner.pop('methods')
        self.assertEqual(res_partner, {'name': "Contact", 'model': 'res.partner'})
        self.assertGreater(set(res_partner_methods), {'search', 'create_company'})
        self.assertGreater(set(res_partner_fields), {'id', 'create_uid', 'lang', 'tz'})

    def test_doc_model(self):
        self.authenticate('demo', 'demo')
        res = self.url_open('/doc/res.partner.json', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'application/json; charset=utf-8')

        json = res.json()
        fields = json.pop('fields', None)
        methods = json.pop('methods', None)
        self.maxDiff = None
        self.assertEqual(json, {
            'model': 'res.partner',
            'name': 'Contact',
            'doc': None,
        })
        self.assertGreater(set(fields), {'id', 'create_uid', 'lang', 'tz'})
        self.assertEqual(fields['id'], {
            'change_default': False,
            'company_dependent': False,
            'default_export_compatible': False,
            'depends': [],
            'exportable': True,
            'groupable': True,
            'manual': False,
            'module': None,
            'name': 'id',
            'readonly': True,
            'required': False,
            'searchable': True,
            'sortable': True,
            'store': True,
            'string': 'ID',
            'type': 'integer',
        })
        self.assertGreater(set(methods), {'search', 'create_company'})
        self.assertEqual(methods['search'], {
            'model': 'core',
            'module': 'core',
            'signature': '(domain, offset=0, limit=None, order=None) -> list[int]',
            'parameters': {
                'domain': {
                    'annotation': 'DomainType',
                    'doc': textwrap.dedent("""\
                        <p><tt class="docutils literal">A search domain &lt;reference/orm/domains&gt;</tt>. Use an empty
                        list to match all records.</p>""",
                    ),
                },
                'offset': {
                    'default': 0,
                    'annotation': 'int',
                    'doc': """<p>number of results to ignore (default: none)</p>""",
                },
                'limit': {
                    'default': None,
                    'annotation': 'int | None',
                    'doc': """<p>maximum number of records to return (default: all)</p>""",
                },
                'order': {
                    'default': None,
                    'annotation': 'str | None',
                    'doc': """<p>sort string</p>""",
                }
            },
            'doc': textwrap.dedent("""\
                <div class="document">


                <p>Search for the records that satisfy the given <tt class="docutils literal">domain</tt>
                <tt class="docutils literal">search domain &lt;reference/orm/domains&gt;</tt>.</p>
                <p>This is a high-level method, which should not be overridden. Its actual
                implementation is done by method <tt class="docutils literal">_search</tt>.</p>
                </div>"""
            ),
            'raise': {
                'AccessError': """<p>if user is not allowed to access requested information</p>""",
            },
            'return': {
                'annotation': 'list[int]',
                'doc': """<p>at most <tt class="docutils literal">limit</tt> records matching the search criteria</p>""",
            },
            'api': ['model'],
        })

    def test_doc_cache(self):
        self.authenticate('demo', 'demo')

        # request the document first
        res = self.url_open('/doc/index.json', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content, "We should have downloaded the document")

        # ensure the necessary is there to cache the document
        cache_control = parse_options_header(res.headers.get('Cache-Control', ''))
        etag = res.headers.get('ETag', '')
        self.assertEqual(cache_control, ('private', {}))
        self.assertTrue(etag)

        # request the document again, this time using the cache
        res = self.url_open(
            '/doc/index.json',
            headers={'If-None-Match': etag},
            allow_redirects=False,
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.NOT_MODIFIED)
        self.assertFalse(res.content, "We should not have downloaded the document")
