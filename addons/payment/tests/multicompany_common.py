# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.fields import Command

from odoo.addons.payment.tests.common import PaymentCommon

_logger = logging.getLogger(__name__)


class PaymentMultiCompanyCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_a = cls.company_data['company']
        cls.company_b = cls.company_data_2['company']

        cls.user_company_a = cls.internal_user
        cls.user_company_b = cls.env['res.users'].create({
            'name': f"{cls.company_b.name} User (TEST)",
            'login': 'user_company_b',
            'password': 'user_company_b',
            'company_id': cls.company_b.id,
            'company_ids': [Command.set(cls.company_b.ids)],
            'groups_id': [Command.link(cls.group_user.id)],
        })
        cls.user_multi_company = cls.env['res.users'].create({
            'name': "Multi Company User (TEST)",
            'login': 'user_multi_company',
            'password': 'user_multi_company',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id, cls.company_b.id])],
            'groups_id': [Command.link(cls.group_user.id)],
        })

        cls.acquirer_company_b = cls._prepare_acquirer(company=cls.company_b)
