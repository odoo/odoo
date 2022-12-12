# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from collections import defaultdict
from itertools import product

from lxml import html
from werkzeug import Response
from werkzeug.test import Client
from werkzeug.urls import url_encode, url_parse, url_decode

from odoo import http
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients

@tagged('portal')
class TestPortal(HttpCase, TestMailFullCommon, TestSMSRecipients):

    def setUp(self):
        super(TestPortal, self).setUp()

        self.record_portal = self.env['mail.test.portal'].create({
            'partner_id': self.partner_1.id,
            'name': 'Test Portal Record',
        })

        self.record_portal._portal_ensure_token()


@tagged('-at_install', 'post_install', 'portal')
class TestPortalControllers(TestPortal):

    def test_redirect_to_records(self):
        """ Test redirection of portal-enabled records """
        # Test Case 0: as anonymous, cannot access, redirect to web/login
        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.record_portal._name,
            self.record_portal.id), timeout=15)

        path = url_parse(response.url).path
        self.assertEqual(path, '/web/login')

        # Test Case 1: as admin, can access record
        self.authenticate(self.user_admin.login, self.user_admin.login)
        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.record_portal._name,
            self.record_portal.id), timeout=15)

        self.assertEqual(response.status_code, 200)

        fragment = url_parse(response.url).fragment
        params = url_decode(fragment)
        self.assertEqual(params['cids'], '%s' % self.user_admin.company_id.id)
        self.assertEqual(params['id'], '%s' % self.record_portal.id)
        self.assertEqual(params['model'], self.record_portal._name)

    def test_redirect_to_records_norecord(self):
        """ Check specific use case of missing model, should directly redirect
        to login page. """
        for model, res_id in [
                (False, self.record_portal.id),
                ('', self.record_portal.id),
                (self.record_portal._name, False),
                (self.record_portal._name, ''),
                (False, False),
                ('wrong.model', self.record_portal.id),
                (self.record_portal._name, -4),
            ]:
            response = self.url_open(
                '/mail/view?model=%s&res_id=%s' % (model, res_id),
                timeout=15
            )
            path = url_parse(response.url).path
            self.assertEqual(
                path, '/web/login',
                'Failed with %s - %s' % (model, res_id)
            )

    def test_portal_message_fetch(self):
        """Test retrieving chatter messages through the portal controller"""
        self.authenticate(None, None)
        message_fetch_url = '/mail/chatter_fetch'
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                'res_model': 'mail.test.portal',
                'res_id': self.record_portal.id,
                'token': self.record_portal.access_token,
            },
        })

        def get_chatter_message_count():
            res = self.url_open(
                url=message_fetch_url,
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            return res.json().get('result', {}).get('message_count', 0)

        self.assertEqual(get_chatter_message_count(), 0)

        for _ in range(8):
            self.record_portal.message_post(
                body='Test',
                author_id=self.partner_1.id,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )

        self.assertEqual(get_chatter_message_count(), 8)

        # Empty the body of a few messages
        for i in (2, 5, 6):
            self.record_portal.message_ids[i].body = ""

        # Empty messages should be ignored
        self.assertEqual(get_chatter_message_count(), 5)

    def test_portal_share_comment(self):
        """ Test posting through portal controller allowing to use a hash to
        post wihtout access rights. """
        self.authenticate(None, None)
        post_url = f"{self.record_portal.get_base_url()}/mail/chatter_post"

        # test as not logged
        self.opener.post(
            url=post_url,
            json={
                'params': {
                    'csrf_token': http.Request.csrf_token(self),
                    'hash': self.record_portal._sign_token(self.partner_2.id),
                    'message': 'Test',
                    'pid': self.partner_2.id,
                    'redirect': '/',
                    'res_model': self.record_portal._name,
                    'res_id': self.record_portal.id,
                    'token': self.record_portal.access_token,
                },
            },
        )
        message = self.record_portal.message_ids[0]

        self.assertIn('Test', message.body)
        self.assertEqual(message.author_id, self.partner_2)


@tagged('portal')
class TestPortalMixin(TestPortal):

    @users('employee')
    def test_portal_mixin(self):
        """ Test internals of portal mixin """
        customer = self.partner_1.with_env(self.env)
        record_portal = self.env['mail.test.portal'].create({
            'partner_id': customer.id,
            'name': 'Test Portal Record',
        })

        self.assertFalse(record_portal.access_token)
        self.assertEqual(record_portal.access_url, '/my/test_portal/%s' % record_portal.id)

        record_portal._portal_ensure_token()
        self.assertTrue(record_portal.access_token)

OBJECT_URL = '/web#model={model}&id={id}&active_id={id}&cids=1'
PORTAL_URL = '/my/thing{token}'
NO_ACCESS = '/web#action=mail.action_discuss'
PORTAL_ROOT = '/my' # portal user gets bounced from /web to /my
@tagged('portal')
class TestMailAccess(HttpCaseWithUserDemo):
    def _cleanup(self, location):
        # we want the absolute path but not the absolute URL, strip out bullshit
        # scheme & domain, as well as fragment as Werkzeug's client doesn't
        # support those (TBF they're a client-only concern)
        return url_parse(location).replace(scheme='', netloc='', fragment='').to_url()

    def do_login(self, client, body, user):
        h = html.fromstring(body)
        f = h.find('.//form[@class="oe_login_form"]')
        fields = {
            field.get('name'): field.get('value')
            for field in f.xpath('.//input[@name] | .//button[@name]')
            if field.get('value')
        }
        fields['login'] = fields['password'] = user
        r = client.post(f.get('action'), data=fields, environ_base={
            'REMOTE_HOST': 'localhost',
            'REMOTE_ADDR': '127.0.0.1',
        })
        return r.headers['Location'], self._cleanup(r.headers['Location'])

    def do_flow(self, model, user, *, login, token):
        params = {}
        Model = self.env[model]
        if token and 'access_token' in Model._fields:
            params = {'access_token': '12345'}

        obj = Model.create(params)
        c = Client(http.root, Response)
        if login:
            self.authenticate(user, user)
            c.set_cookie('localhost', key='session_id', value=self.session.sid, httponly=True)
        self.env.cr.flush()
        self.env.cr.clear()
        location = url = '/mail/view?' + url_encode({
            'model': model,
            'res_id': obj.id,
            **params
        })
        while True:
            r = c.get(url)
            self.assertLess(r.status_code, 400, f'{url} = {r.status}')
            if r.status_code // 100 == 2:
                if url.startswith('/web/login'):
                    location, url = self.do_login(c, r.data, user)
                    continue
                break

            location = r.headers['Location']
            redir = self._cleanup(location)
            assert url != redir, "redirection loop"
            url = redir
        return obj, location, r

    @mute_logger(
        'odoo.http', # bunch of "Session expired" message
        'odoo.addons.base.models.res_users', # on every login (~25)
        'odoo.addons.base.models.ir_model', # on every ACL error (~15)
    )
    def test_mail_view_portal(self):
        # Each case is a triplet of (model type, login, results) where the
        # access context is a dict of (logged in, has token) mapping to a final
        # URL.
        #
        # The model type indicates whether the model is portal-enabled
        # (portal.mixin) or not.
        #
        # The login is used if the user gets bounced through `/web/login` during
        # the flow execution in which case they will get logged in at that
        # point, or if the `logged in` pre-set is selected, in which case they
        # will get logged in before the process starts.
        #
        # For each case, the driver will perform the access flow through
        # /mail/view in each of the 4 possible pre-set states then check if the
        # URL it reaches at the end matches that specified for the preset state.
        cases = [
            ('not_portal', 'admin', defaultdict(lambda: OBJECT_URL)),
            # admin always gets backend unless unlogged w/ a token
            ('portal', 'admin', defaultdict(lambda: OBJECT_URL, {
                (False, True): PORTAL_URL,
            })),
            ('not_portal', 'demo', defaultdict(lambda: NO_ACCESS)),
             # demo gets portal if token
            ('portal', 'demo', {
                (True, True): PORTAL_URL, # no access + token => portal
                (False, True): PORTAL_URL, # unlogged + token => portal
                (True, False): NO_ACCESS,
                (False, False): NO_ACCESS,
            }),
            ('not_portal', 'portal', defaultdict(lambda: PORTAL_ROOT)),
            ('portal', 'portal', {
                (True, True): PORTAL_URL,
                (False, True): PORTAL_URL,
                (True, False): PORTAL_ROOT,
                (False, False): PORTAL_ROOT,
            }),
        ]
        for mod, user, items in cases:
            for (logged, token) in product([True, False], [True, False]):
                result = items[logged, token]
                label = f"object={mod} user={user}{', logged' if logged else ''}{', token' if token else ''}"
                with self.subTest(label):
                    obj, url, _ = self.do_flow(f'test_mail_full.{mod}', user, login=logged, token=token)
                    url = url_parse(url).replace(scheme='', netloc='').to_url()
                    tok = ''
                    if token and 'access_token' in obj._fields:
                        tok = f'?access_token={obj.access_token}'
                    expected = result.format(model=obj._name, id=obj.id, token=tok)
                    self.assertEqual(url, expected)

    @mute_logger('odoo.addons.base.models.res_users', 'odoo.addons.base.models.ir_model')
    def test_mail_view_portal_with_access(self):
        """if portal user has access to the resource, then they get a portal
        link with an access token
        """
        self.env['ir.model.access'].create({
            'name': 'portal access',
            'model_id': self.env.ref('test_mail_full.model_test_mail_full_portal').id,
            'group_id': self.env.ref('base.group_portal').id,
            'perm_read': True,
        })
        with self.subTest("object=portal user=portal[acl+] logged"):
            obj, url, _ = self.do_flow('test_mail_full.portal', 'portal', login=True, token=False)
            self.assertEqual(
                self._cleanup(url),
                PORTAL_URL.format(token=f'?access_token={obj.access_token}'),
            )

        with self.subTest("object=portal user=portal[acl+]"):
            obj, url, _ = self.do_flow('test_mail_full.portal', 'portal', login=False, token=False)
            self.assertEqual(
                self._cleanup(url),
                PORTAL_URL.format(token=f'?access_token={obj.access_token}'),
            )
