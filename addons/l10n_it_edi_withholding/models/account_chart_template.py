# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        """
            Override normal default taxes, which are the ones with lowest sequence.
        """
        result = super()._load(company)
        if company.chart_template_id == self.env.ref('l10n_it.l10n_it_chart_template_generic'):
            company.account_sale_tax_id = self.env.ref(f'l10n_it.{company.id}_22v')
            company.account_purchase_tax_id = self.env.ref(f'l10n_it.{company.id}_22am')
        return result
