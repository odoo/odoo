# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        # Overridden to add export button on GL for Mexican companies
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        if self.env.company.account_fiscal_country_id.code == 'MX':
            options['buttons'].append({
                'name': _('XML (Polizas)'),
                'sequence': 30,
                'action': 'l10n_mx_open_xml_export_wizard',
                'file_export_type': _('XML')
            })

    def l10n_mx_open_xml_export_wizard(self, options):
        """ Action to open the XML Polizas Export Options from the General Ledger button """
        return {
            'type': 'ir.actions.act_window',
            'name': _('XML Polizas Export Options'),
            'res_model': 'l10n_mx_xml_polizas.xml_polizas_wizard',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                **self.env.context,
                'l10n_mx_xml_polizas_generation_options': options,
                'default_export_type': 'AF'
            }
        }
