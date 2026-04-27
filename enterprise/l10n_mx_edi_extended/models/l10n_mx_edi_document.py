# -*- coding: utf-8 -*-
from odoo import api, models


class L10nMxEdiDocument(models.Model):
    _inherit = 'l10n_mx_edi.document'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _decode_cfdi_attachment(self, cfdi_data):
        # EXTENDS 'l10n_mx_edi'
        def get_node(node, xpath):
            nodes = node.xpath(xpath)
            return nodes[0] if nodes else None

        cfdi_infos = super()._decode_cfdi_attachment(cfdi_data)
        if not cfdi_infos:
            return cfdi_infos

        cfdi_node = cfdi_infos['cfdi_node']

        external_trade_node = get_node(cfdi_node, "//*[local-name()='ComercioExterior']")
        if external_trade_node is None:
            return cfdi_infos

        cfdi_infos.update({
            'ext_trade_node': external_trade_node,
            'ext_trade_certificate_key': external_trade_node.get('ClaveDePedimento', ''),
            'ext_trade_certificate_source': external_trade_node.get('CertificadoOrigen', '').replace('0', 'No').replace('1', 'Si'),
            'ext_trade_nb_certificate_origin': external_trade_node.get('CertificadoOrigen', ''),
            'ext_trade_certificate_origin': external_trade_node.get('NumCertificadoOrigen', ''),
            'ext_trade_nb_reliable_exporter': external_trade_node.get('NumeroExportadorConfiable', ''),
            'ext_trade_incoterm': external_trade_node.get('Incoterm', ''),
            'ext_trade_rate_usd': external_trade_node.get('TipoCambioUSD', ''),
            'ext_trade_total_usd': external_trade_node.get('TotalUSD', ''),
        })
        return cfdi_infos
