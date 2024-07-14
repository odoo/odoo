# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2022 WT-IO-IT GmbH (https://www.wt-io-it.at)
#                    Mag. Wolfgang Taferner <wolfgang.taferner@wt-io-it.at>
from odoo import models


class AustrianECSalesReport(models.AbstractModel):
    _name = 'l10n_at.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Austrian EC Sales Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        """
        Add the invoice lines search domain that is specific to the country.
        Typically, the taxes account.report.expression ids relative to the country for the triangular, sale of goods
        or services.
        :param dict options: Report options
        :return dict: The modified options dictionary
        """
        super()._init_core_custom_options(report, options, previous_options)
        ec_operation_category = options.setdefault('sales_report_taxes', {})

        goods = self.env.ref('l10n_at.tax_report_line_l10n_at_tva_line_3_zm_igl_tag')
        goods |= self.env.ref('l10n_at.tax_report_line_l10n_at_tva_line_4_8_tag')
        goods |= self.env.ref('l10n_at.tax_report_line_l10n_at_tva_line_4_9_tag')
        triangular = self.env.ref('l10n_at.tax_report_line_l10n_at_tva_line_3_zm_igl3_tag')
        services = self.env.ref('l10n_at.tax_report_line_l10n_at_tva_line_3_zm_dl_tag')

        ec_operation_category['goods'] = tuple(goods._get_matching_tags().ids)
        ec_operation_category['triangular'] = tuple(triangular._get_matching_tags().ids)
        ec_operation_category['services'] = tuple(services._get_matching_tags().ids)

        # Change the names of the taxes to specific ones that are dependant to the tax type
        ec_operation_category['operation_category'] = {
            'goods': 'L',
            'triangular': 'D',
            'services': 'S',
        }

        options.update({'sales_report_taxes': ec_operation_category})
