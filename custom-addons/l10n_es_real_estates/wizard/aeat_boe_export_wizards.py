# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Mod347BOEWizard(models.TransientModel):
    _inherit = 'l10n_es_reports.aeat.boe.mod347.export.wizard'

    real_estates_vat_mod347_data = fields.One2many(
        comodel_name='l10n_es_reports.aeat.mod347.real.estates.vat',
        inverse_name='parent_wizard_id',
        string="Amount Perceived for Transfers of Real Estates Subject to VAT")

    def l10n_es_get_partners_manual_parameters_map(self):
        rslt = super(Mod347BOEWizard, self).l10n_es_get_partners_manual_parameters_map()

        real_estates_vat_dict = {}
        for data in self.real_estates_vat_mod347_data:
            if not real_estates_vat_dict.get(data.partner_id.id):
                real_estates_vat_dict[data.partner_id.id] = {}
                for trimester in range(1,5):
                    real_estates_vat_dict[data.partner_id.id][str(trimester)] = {'local_negocio': {'A': 0, 'B':0}, 'seguros': {'B': 0}, 'otras': {'A': 0, 'B': 0}}

            real_estates_vat_dict[data.partner_id.id][data.trimester][data.operation_class][data.operation_key] = data.perceived_amount

        rslt['real_estates_vat'] = real_estates_vat_dict

        return rslt


class Mod347BOERealEstatesVATData(models.TransientModel):
    _name = 'l10n_es_reports.aeat.mod347.real.estates.vat'
    _description = 'BOE Real Estates VAT Data for (mod347)'
    _inherit = 'l10n_es_reports.aeat.mod347.manual.partner.data'

    trimester = fields.Selection(selection=[('1', '1st'), ('2', '2nd'), ('3', '3rd'), ('4', '4th')], required=True)
