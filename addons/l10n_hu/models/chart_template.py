# -*- coding: utf-8 -*-
"""
@author: Online ERP Hungary Kft.
"""

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        """This method generates Fiscal Position, Fiscal Position Accounts
        and Fiscal Position Taxes from templates.
        :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
        :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
        :param company_id: the company to generate fiscal position data for
        :returns: True
        """
        self.ensure_one()
        positions = self.env["account.fiscal.position.template"].search([("chart_template_id", "=", self.id)])

        # first create fiscal positions in batch
        template_vals = []
        for position in positions:
            fp_vals = self._get_fp_vals(company, position)
            template_vals.append((position, fp_vals))
        fps = self._create_records_with_xmlid("account.fiscal.position", template_vals, company)

        # then create fiscal position taxes and accounts
        tax_template_vals = []
        account_template_vals = []
        for position, fp in zip(positions, fps):
            for tax in position.tax_ids:
                tax_template_vals.append(
                    (
                        tax,
                        {
                            "tax_src_id": tax_template_ref[tax.tax_src_id].id,
                            "tax_dest_id": tax.tax_dest_id and tax_template_ref[tax.tax_dest_id].id or False,
                            ############ FROM HERE ############
                            # We have a new field
                            "service_tax_dest_id": tax.service_tax_dest_id
                            and tax_template_ref[tax.service_tax_dest_id].id
                            or False,
                            ############ TO HERE ############
                            "position_id": fp.id,
                        },
                    )
                )
            for acc in position.account_ids:
                account_template_vals.append(
                    (
                        acc,
                        {
                            "account_src_id": acc_template_ref[acc.account_src_id].id,
                            "account_dest_id": acc_template_ref[acc.account_dest_id].id,
                            "position_id": fp.id,
                        },
                    )
                )
        self._create_records_with_xmlid("account.fiscal.position.tax", tax_template_vals, company)
        self._create_records_with_xmlid("account.fiscal.position.account", account_template_vals, company)

        return True
