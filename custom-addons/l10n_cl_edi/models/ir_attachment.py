# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree, objectify

from odoo import api, models, tools


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_cl_edi_load_xsd_files(self, force_reload=False):
        main_xsd_download_url = 'http://www.sii.cl/factura_electronica'

        validation_types = {
            'consu': {
                'description': 'Libro de consumo de folios para boletas de venta',
                'file_name': 'ConsumoFolio_v10.xsd',
                'file_url': 'ConsumoFolio_v10.xsd',
            },
            'doc': {
                'description': 'Documentos Tributarios Electrónicos',
                'file_name': 'DTE_v10.xsd',
                'file_url': 'schema_dte.zip',
            },
            'bol': {
                'description': 'Validación de XML de envío de boletas de venta',
                'file_name': 'EnvioBOLETA_v11.xsd',
                'file_url': 'schema_envio_bol.zip',
            },
            'siitypes': {
                'description': 'Tipos SII',
                'file_name': 'SiiTypes_v10.xsd',
                'file_url': 'schema_dte.zip',
            },
            'env': {
                'description': 'Validación de XML de envío de documentos tributarios Electrónicos',
                'file_name': 'EnvioDTE_v10.xsd',
                'file_url': 'schema_dte.zip',
            },
            'recep': {
                'description': 'Validación de XML de intercambio entre contribuyentes',
                'file_name': 'Recibos_v10.xsd',
                'file_url': 'schema19983.zip',
            },
            'env_recep': {
                'description': 'Validación de envíos de intercambio entre contribuyentes',
                'file_name': 'EnvioRecibos_v10.xsd',
                'file_url': 'schema19983.zip',
            },
            'resp_sii': {
                'description': 'Esquema de respuestas de envío del SII',
                'file_name': 'RespSII_v10.xsd',
                'file_url': 'schema_resp.zip',
            },
            'book': {
                'description': 'Informacion Electronica de Libros de Compra y Venta',
                'file_name': 'LibroCV_v10.xsd',
                'file_url': 'schema_iecv.zip',
            },
            'resp_env': {
                'description': 'Validación de XML de intercambio entre contribuyentes',
                'file_name': 'RespuestaEnvioDTE_v10.xsd',
                'file_url': 'schema_ic.zip',
            },
            'librobol': {
                'description': 'Informacion Electronica de Libros de Boletas',
                'file_name': 'LibroBOLETA_v10.xsd',
                'file_url': 'schema_libro_bol.zip',
            },
            'libroguia': {
                'description': 'Informacion Electronica del Libro de Guias',
                'file_name': 'LibroGuia_v10.xsd',
                'file_url': 'schema_lgd.zip',
            },
            'sig': {
                'description': 'Validación de Firma electrónica',
                'file_name': 'xmldsignature_v10.xsd',
                'file_url': 'schema_dte.zip',
            },
        }
        for values in validation_types.values():
            file_url = values['file_url']
            url = f'{main_xsd_download_url}/{file_url}'
            tools.load_xsd_files_from_url(self.env, url, values['file_name'],
                                          xsd_name_prefix='l10n_cl_edi', xsd_names_filter=values['file_name'],
                                          modify_xsd_content=lambda content: etree.tostring(objectify.fromstring(content), encoding='utf-8', pretty_print=True))
        return

    @api.model
    def action_download_xsd_files(self):
        # EXTENDS account/models/ir_attachment.py
        self._l10n_cl_edi_load_xsd_files()
        super().action_download_xsd_files()
