# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class L10nLuGenerateXML(models.TransientModel):
    """
    This wizard is used to generate xml reports for Luxembourg
    according to the xml 2.0 standard.
    """
    _inherit = 'l10n_lu.generate.xml'
    _name = 'l10n_lu.generate.asset.report'
    _description = 'Generate XML for Luxembourg'

    def _lu_get_declarations(self, declaration_template_values):
        values = self.env.ref('account_asset.assets_report').l10n_lu_asset_report_get_xml_2_0_report_values(self.env.context['report_generation_options'])
        declarations = {'declaration_singles': {'forms': values['forms']}, 'declaration_groups': []}
        declarations.update(declaration_template_values)
        return {'declarations': [declarations]}
