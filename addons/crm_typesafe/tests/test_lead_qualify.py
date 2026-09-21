# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import tagged, users

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.crm_typesafe.models.crm_lead import TYPESAFE_PROVIDERS


class MockTypeSafe:

    @contextmanager
    def mockTypeSafeGateway(self, answers=None, sim_error=None):
        self._typesafe_requests = []
        test = self

        def _mock_request(model, questions, state):
            test._typesafe_requests.append({'questions': questions, 'state': state})
            if sim_error == 'http':
                message = '429 Client Error: Too Many Requests'
                raise requests.exceptions.HTTPError(message)
            return answers or {
                'priority': {'type': 'choice', 'choice': '2', 'probabilities': {'0': 0.02, '1': 0.08, '2': 0.85, '3': 0.05}, 'confidence': 0.8},
                'readiness': {'type': 'score', 'score': 2.1, 'legend': {}, 'probabilities': {'0': 0.0, '1': 0.1, '2': 0.7, '3': 0.2}, 'confidence': 0.6},
                'is_spam': {'type': 'noul', 'noul': 0.03},
            }

        with patch('odoo.addons.crm_typesafe.models.crm_lead.CrmLead._typesafe_request', side_effect=_mock_request, autospec=True):
            yield


@tagged('post_install', '-at_install')
class TestLeadQualify(TestCrmCommon, MockTypeSafe):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_str('crm.typesafe.api_key', 'test-key')
        cls.leads = cls.env['crm.lead'].create([{
            'name': 'Quote for 200 licences',
            'contact_name': 'Jane Doe',
            'partner_name': 'Acme Corp',
            'email_from': 'jane@acme.example.com',
            'description': '<p>We need a quote for 200 seats before end of quarter.</p>',
            'expected_revenue': 24000,
        }, {
            'name': 'Best SEO services!!!',
            'email_from': 'promo@spammy.example.com',
            'description': '<p>Rank #1 on Google with our services</p>',
        }])

    @users('user_sales_manager')
    def test_qualify_applies_answers(self):
        lead = self.leads[0].with_env(self.env)
        with self.mockTypeSafeGateway():
            lead.typesafe_qualify()

        self.assertTrue(lead.typesafe_done)
        self.assertEqual(lead.priority, '2')
        self.assertAlmostEqual(lead.typesafe_readiness, 70.0)
        self.assertAlmostEqual(lead.typesafe_spam_probability, 0.03)
        self.assertFalse(lead.show_typesafe_qualify_button)
        note = lead.message_ids.filtered(lambda m: 'TypeSafe' in (m.body or ''))
        self.assertEqual(len(note), 1)

        request = self._typesafe_requests[0]
        self.assertEqual(request['state']['lead']['company_name'], 'Acme Corp')
        self.assertEqual(request['state']['lead']['notes'], 'We need a quote for 200 seats before end of quarter.')
        self.assertEqual(set(request['questions']), {'priority', 'readiness', 'is_spam'})

    @users('user_sales_manager')
    def test_qualify_low_confidence_keeps_priority(self):
        lead = self.leads[1].with_env(self.env)
        lead.priority = '1'
        answers = {
            'priority': {'type': 'choice', 'choice': '0', 'probabilities': {'0': 0.4, '1': 0.35, '2': 0.2, '3': 0.05}, 'confidence': 0.2},
            'readiness': {'type': 'score', 'score': 0.15, 'legend': {}, 'probabilities': {'0': 0.85, '1': 0.15, '2': 0.0, '3': 0.0}, 'confidence': 0.8},
            'is_spam': {'type': 'noul', 'noul': 0.97},
        }
        with self.mockTypeSafeGateway(answers=answers):
            lead.typesafe_qualify()

        self.assertTrue(lead.typesafe_done)
        self.assertEqual(lead.priority, '1', 'Priority should not change on a low-confidence answer')
        self.assertAlmostEqual(lead.typesafe_readiness, 5.0)
        self.assertAlmostEqual(lead.typesafe_spam_probability, 0.97)
        self.assertIn(lead, self.env['crm.lead'].search([('typesafe_spam_probability', '>=', 0.8)]))

    @users('user_sales_manager')
    def test_qualify_error_manual(self):
        lead = self.leads[0].with_env(self.env)
        with self.mockTypeSafeGateway(sim_error='http'), self.assertRaises(UserError):
            lead.typesafe_qualify()
        self.assertFalse(lead.typesafe_done)

    def test_qualify_error_cron(self):
        with self.mockTypeSafeGateway(sim_error='http'):
            self.env['crm.lead']._typesafe_qualify_leads_cron()
        self.assertFalse(any(self.leads.mapped('typesafe_done')), 'Failed leads stay pending for a later run')

    def test_qualify_cron(self):
        pending = self.env['crm.lead'].search([('typesafe_done', '=', False), ('probability', '<', 100)])
        self.assertIn(self.leads[0], pending)
        with self.mockTypeSafeGateway():
            self.env['crm.lead']._typesafe_qualify_leads_cron()
        self.assertTrue(all(pending.mapped('typesafe_done')))
        self.assertEqual(len(self._typesafe_requests), len(pending), 'One request per lead')

    def test_qualify_without_api_key(self):
        self.env['ir.config_parameter'].sudo().set_str('crm.typesafe.api_key', '')
        with self.mockTypeSafeGateway():
            self.env['crm.lead']._typesafe_qualify_leads_cron()
        self.assertFalse(self._typesafe_requests)
        with self.assertRaises(UserError):
            self.leads[0].typesafe_qualify()

    def test_qualify_auto_setting(self):
        cron = self.env.ref('crm_typesafe.ir_cron_lead_qualification')

        config = self.env['res.config.settings'].create({'typesafe_qualify_auto': 'manual'})
        config.execute()
        self.assertFalse(cron.active)

        config.write({'typesafe_qualify_auto': 'auto'})
        config.execute()
        self.assertTrue(cron.active)

    def test_request_unknown_provider_falls_back(self):
        self.env['ir.config_parameter'].sudo().set_str('crm.typesafe.provider', 'nope')
        with patch('odoo.addons.crm_typesafe.models.crm_lead.requests.post') as post:
            post.return_value.json.return_value = {'answers': {}}
            self.env['crm.lead']._typesafe_request({}, 'state')
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://api.typesafe.ai/v1/systemone')
        self.assertEqual(kwargs['json']['model'], 'jev-latest')

    def test_request_providers(self):
        for provider, expected in TYPESAFE_PROVIDERS.items():
            with self.subTest(provider=provider):
                self.env['ir.config_parameter'].sudo().set_str('crm.typesafe.provider', provider)
                with patch('odoo.addons.crm_typesafe.models.crm_lead.requests.post') as post:
                    post.return_value.json.return_value = {'answers': {}}
                    self.env['crm.lead']._typesafe_request({}, 'state')
                args, kwargs = post.call_args
                self.assertEqual(args[0], expected['url'])
                self.assertTrue(args[0].startswith('https://'))
                self.assertEqual(kwargs['json']['model'], expected['model'])

    def test_request_uses_configured_gateway(self):
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_str('crm.typesafe.provider', 'vercel')
        with patch('odoo.addons.crm_typesafe.models.crm_lead.requests.post') as post:
            post.return_value.json.return_value = {'answers': {'q': {'type': 'noul', 'noul': 0.5}}}
            answers = self.env['crm.lead']._typesafe_request({'q': {'type': 'noul', 'instructions': 'x'}}, 'state')
        self.assertEqual(answers['q']['noul'], 0.5)
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://ai-gateway.vercel.sh/typesafe/v1/systemone')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')
        self.assertEqual(kwargs['json']['model'], 'typesafe-ai/jev')
        self.assertEqual(kwargs['json']['state'], 'state')
        self.assertIn('timeout', kwargs)

    def test_request_error_message(self):
        with patch('odoo.addons.crm_typesafe.models.crm_lead.requests.post') as post:
            post.return_value.ok = False
            post.return_value.status_code = 403
            post.return_value.reason = 'Forbidden'
            post.return_value.json.return_value = {'error': {'message': 'Add a credit card to unlock credits'}}
            with self.assertRaises(requests.exceptions.HTTPError) as cm:
                self.env['crm.lead']._typesafe_request({'q': {'type': 'noul', 'instructions': 'x'}}, 'state')
        self.assertEqual(str(cm.exception), '403 Forbidden: Add a credit card to unlock credits')
