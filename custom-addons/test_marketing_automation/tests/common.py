# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.marketing_automation_sms.tests.common import MarketingAutomationSMSCommon


class TestMACommon(MarketingAutomationSMSCommon):

    # ------------------------------------------------------------
    # RECORDS TOOLS
    # ------------------------------------------------------------

    @classmethod
    def _create_marketauto_records(cls, model='marketing.test.sms', count=1):
        """ Create records for marketing automation. Each batch consists in

          * 3 records with a valid partner w mobile and email;
          * 1 record without partner w email and mobile;
          * 1 record without partner, wo email and mobile
        """
        record_vals = []
        for idx in range(0, count):
            for inner_idx in range(0, 5):
                current_idx = idx * 5 + inner_idx
                customer_name = f'Customer_{current_idx}'
                record_name = f'Test_{current_idx:02d}'

                if inner_idx < 3:
                    email = f'email_{current_idx:02d}@customer.example.com'
                    partner = cls.env['res.partner'].create({
                        'country_id': cls.env.ref('base.be').id,
                        'email': f'"{customer_name}" <{email}>',
                        'mobile': f'045600{current_idx:04d}',
                        'name': customer_name,
                    })
                else:
                    partner = cls.env['res.partner']

                vals = {
                    'customer_id': partner.id,
                    'description': f'Linked to partner {partner.name}' if partner else '',
                    'name': record_name,
                }
                if inner_idx == 3:
                    vals['email_from'] = f'"{customer_name}" <nopartner.email_{current_idx:02d}@customer.example.com>'
                    vals['mobile'] = f'+3245600{current_idx:04d}'

                record_vals.append(vals)

        return cls.env[model].create(record_vals)
