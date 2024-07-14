# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import xml_utils


L10N_EC_XSD_INFOS = {
    'xmldsig': {
        'name': 'xmldsig.xsd',
        'url': r'https://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd'
    },
    'invoice': {
        'name': 'factura_V2.1.0.xsd',
        'url': r'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/05546998-6f29-4870-be3b-62650f312a6c/XML%20y%20XSD%20Factura.zip',
    },
    'credit_note': {
        'name': 'NotaCredito_V1.1.0.xsd',
        'url': r'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/dfc944cd-5f18-4433-a626-3cc64cfc4549/XML%20y%20XSD%20Nota%20de%20Cr%c3%a9dito.zip',
    },
    'debit_note': {
        'name': 'NotaDebito_V1.0.0.xsd',
        'url': r'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/ccc3913a-879e-41b6-82b7-11b627b7d1d8/XML%20y%20XSD%20Nota%20de%20D%c3%a9bito.zip',
    },
    'purchase_liquidation': {
        'name': 'LiquidacionCompra_V1.1.0.xsd',
        'url': r'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/ee386507-04f8-4a45-b9cd-6d4e4c6ac1e6/XML%20y%20XSD%20Liquidaci%c3%b3n.zip',
    },
    'withhold': {
        'name': 'ComprobanteRetencion_V2.0.0.xsd',
        'url': r'https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/90950fca-73a7-4cfb-9c2d-3142b10435f2/XML%20y%20XSD%20Comprobante%20de%20Retenci%c3%b3n.zip',
    }
}


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_ec_edi_load_xsd_attachments(self):
        """Downloads the xsd validation files if they don't already exist."""
        for xsd_info in L10N_EC_XSD_INFOS.values():
            xml_utils.load_xsd_files_from_url(self.env, xsd_info['url'], xsd_name_prefix='l10n_ec_edi')

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py

        self._l10n_ec_edi_load_xsd_attachments()
        super().action_download_xsd_files()
