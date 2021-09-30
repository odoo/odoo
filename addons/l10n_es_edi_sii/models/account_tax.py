# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class SIIAccountTaxMixin(models.AbstractModel):
    _name = 'l10n_es.sii.account.tax.mixin'
    _description = 'SII Fields'

    l10n_es_exempt_reason = fields.Selection(
        selection=[
            ('E1', 'Art. 20'),
            ('E2', 'Art. 21'),
            ('E3', 'Art. 22'),
            ('E4', 'Art. 23 y 24'),
            ('E5', 'Art. 25'),
            ('E6', 'Otros'),
        ],
        string="Exempt Reason (Spain)",
    )
    l10n_es_type = fields.Selection(
        selection=[
            ('exento', 'Exento'),
            ('sujeto', 'Sujeto'),
            ('sujeto_agricultura', 'Sujeto Agricultura'),
            ('sujeto_isp', 'Sujeto ISP'),
            ('no_sujeto', 'No Sujeto'),
            ('no_sujeto_loc', 'No Sujeto por reglas de Localization'),
            ('no_deducible', 'No Deducible'),
            ('retencion', 'Retencion'),
            ('recargo', 'Recargo de Equivalencia'),
            ('ignore', 'Ignore even the base amount'),
        ],
        string="Tax Type (Spain)", default='sujeto'
    )
    l10n_es_bien_inversion = fields.Boolean('Bien de Inversion', default=False)


class AccountTax(models.Model):
    _inherit = ['account.tax', 'l10n_es.sii.account.tax.mixin']
    _name = 'account.tax'


class AccountTaxTemplate(models.Model):
    _inherit = ['account.tax.template', 'l10n_es.sii.account.tax.mixin']
    _name = 'account.tax.template'

    def _get_tax_vals(self, company, tax_template_to_tax):
        # OVERRIDE
        # Copy values from 'account.tax.template' to vals will be used to create a new 'account.tax'.
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        vals['l10n_es_exempt_reason'] = self.l10n_es_exempt_reason
        vals['l10n_es_type'] = self.l10n_es_type
        vals['l10n_es_bien_inversion'] = self.l10n_es_bien_inversion
        return vals
