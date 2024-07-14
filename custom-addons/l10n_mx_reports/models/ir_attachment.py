# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools

XSD_INFOS = {
    'xsd_mx_cfdicoa_1_3.xsd': {
        'name': 'xsd_mx_cfdicoa_1_3.xsd',
        'url': 'https://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas/CatalogoCuentas_1_3.xsd',
        'prefix': 'l1On_mx_reports',
    },
     'xsd_mx_cfdibalance_1_3.xsd': {
        'name': 'xsd_mx_cfdibalance_1_3.xsd',
        'url': 'https://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion/BalanzaComprobacion_1_3.xsd',
        'prefix': 'l1On_mx_reports',
     },
}


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_mx_reports_load_xsd_files(self, force_reload=False):
        for xsd_info in XSD_INFOS.values():
            tools.load_xsd_files_from_url(self.env, xsd_info['url'], xsd_info['name'], xsd_name_prefix=xsd_info['prefix'])

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py
        self._l10n_mx_reports_load_xsd_files()
        super().action_download_xsd_files()

    @api.model
    def l10n_mx_reports_validate_xml_from_attachment(self, xml_content, xsd_name):
        xsd_info = XSD_INFOS[xsd_name]
        return tools.validate_xml_from_attachment(self.env, xml_content, xsd_info['name'], prefix=xsd_info['prefix'])
