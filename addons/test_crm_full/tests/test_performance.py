# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.test_crm_full.tests.common import TestCrmFullCommon
from odoo.tests.common import users, warmup, Form
from odoo.tests import tagged


@tagged('crm_performance', 'post_install', '-at_install')
class CrmPerformanceCase(TestCrmFullCommon):

    def setUp(self):
        super(CrmPerformanceCase, self).setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        self._flush_tracking()

        self.user_sales_leads.write({
            'groups_id': [
                (4, self.env.ref('event.group_event_user').id),
                (4, self.env.ref('im_livechat.im_livechat_group_user').id),
            ]
        })

    def _flush_tracking(self):
        """ Force the creation of tracking values notably, and ensure tests are
        reproducible. """
        self.env.flush_all()
        self.cr.flush()


@tagged('crm_performance', 'post_install', '-at_install')
class TestCrmPerformance(CrmPerformanceCase):

    @users('user_sales_leads')
    @warmup
    def test_lead_create_batch_mixed(self):
        """ Test multiple lead creation (import) """
        batch_size = 10
        country_be = self.env.ref('base.be')
        lang_be_id = self.env['res.lang']._lang_get_id('fr_BE')

        with freeze_time(self.reference_now), self.assertQueryCount(user_sales_leads=194):  # tcf 193 / com 194
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            crm_values = [
                {'country_id': country_be.id,
                 'email_from': 'address.email.%02d@test.example.com' % idx,
                 'function': 'Noisy Customer',
                 'lang_id': lang_be_id,
                 'mobile': '04551111%02d' % idx,
                 'name': 'Test Lead %02d' % idx,
                 'phone': '04550000%02d' % idx,
                 'street': 'Super Street, %092d' % idx,
                 'zip': '1400',
                } for idx in range(batch_size)
            ]
            crm_values += [
                {'partner_id': self.partners[idx].id,
                 'name': 'Test Lead %02d' % idx,
                } for idx in range(batch_size)
            ]
            _leads = self.env['crm.lead'].create(crm_values)

    @users('user_sales_leads')
    @warmup
    def test_lead_create_form_address(self):
        """ Test a single lead creation using Form """
        country_be = self.env.ref('base.be')
        lang_be = self.env['res.lang']._lang_get('fr_BE')

        with freeze_time(self.reference_now), self.assertQueryCount(user_sales_leads=186):  # tcf 174 / com 175
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with Form(self.env['crm.lead']) as lead_form:
                lead_form.country_id = country_be
                lead_form.email_from = 'address.email@test.example.com'
                lead_form.function = 'Noisy Customer'
                lead_form.lang_id = lang_be
                lead_form.mobile = '0455111100'
                lead_form.name = 'Test Lead'
                lead_form.phone = '0455000011'
                lead_form.street = 'Super Street, 00'
                lead_form.zip = '1400'

            _lead = lead_form.save()

    @users('user_sales_leads')
    @warmup
    def test_lead_create_form_partner(self):
        """ Test a single lead creation using Form with a partner """
        with freeze_time(self.reference_now), self.assertQueryCount(user_sales_leads=199):  # tcf 186 / com 188
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            with self.debug_mode():
                # {'invisible': ['|', ('type', '=', 'opportunity'), ('is_partner_visible', '=', False)]}
                # lead.is_partner_visible = bool(lead.type == 'opportunity' or lead.partner_id or is_debug_mode)
                with Form(self.env['crm.lead']) as lead_form:
                    lead_form.partner_id = self.partners[0]
                    lead_form.name = 'Test Lead'

            _lead = lead_form.save()

    @users('user_sales_leads')
    @warmup
    def test_lead_create_single_address(self):
        """ Test multiple lead creation (import) """
        country_be = self.env.ref('base.be')
        lang_be_id = self.env['res.lang']._lang_get_id('fr_BE')

        with freeze_time(self.reference_now), self.assertQueryCount(user_sales_leads=31):  # tcf 30 / com 31
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            crm_values = [
                {'country_id': country_be.id,
                 'email_from': 'address.email.00@test.example.com',
                 'function': 'Noisy Customer',
                 'lang_id': lang_be_id,
                 'mobile': '0455111100',
                 'name': 'Test Lead',
                 'phone': '0455000000',
                 'street': 'Super Street, 00',
                 'zip': '1400',
                }
            ]
            _lead = self.env['crm.lead'].create(crm_values)

    @users('user_sales_leads')
    @warmup
    def test_lead_create_single_partner(self):
        """ Test multiple lead creation (import) """
        with freeze_time(self.reference_now), self.assertQueryCount(user_sales_leads=32):  # tcf 31 / com 32
            self.env.cr._now = self.reference_now  # force create_date to check schedulers
            crm_values = [
                {'partner_id': self.partners[0].id,
                 'name': 'Test Lead',
                }
            ]
            _lead = self.env['crm.lead'].create(crm_values)
