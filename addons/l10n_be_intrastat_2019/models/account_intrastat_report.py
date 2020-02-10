# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.pycompat import text_type
from collections import namedtuple


class XmlDeclaration(models.TransientModel):
    """
    Intrastat XML Declaration
    """
    _inherit = "l10n_be_intrastat_xml.xml_decl"

    def _get_rounding_digits(self):
        """
        @override

        https://www.nbb.be/doc/dq/f_pdf_ex/nieuwsbriefintrastat_n28_2018_fr.pdf
        Chapter 3
        """
        return 2

    def _build_intrastat_line(self, numlgn, item, linekey, amounts, dispatchmode, extendedmode):
        super(XmlDeclaration, self)._build_intrastat_line(numlgn, item, linekey, amounts, dispatchmode, extendedmode)
        if dispatchmode:
            self._set_Dim(item, 'EXCNTORI', text_type(linekey.EXCNTORI))
            self._set_Dim(item, 'PARTNERID', text_type(linekey.PARTNERID))

    def _get_intrastat_linekey(self, declcode, inv_line, dispatchmode, extendedmode):
        res = super(XmlDeclaration, self)._get_intrastat_linekey(declcode, inv_line, dispatchmode, extendedmode)
        if res and dispatchmode:
            res_dict = res._asdict()
            res_dict['EXCNTORI'] = inv_line.intrastat_product_origin_country_id.code or 'QU'
            res_dict['PARTNERID'] = inv_line.invoice_id.partner_id.vat or 'QV999999999999'
            return namedtuple('intrastatkey', res_dict.keys())(**res_dict)
        return res

    def _get_expedition_code(self, extended):
        return 'INTRASTAT_X_E' if extended else 'INTRASTAT_X_S'

    def _get_expedition_form(self, extended):
        return 'INTRASTAT_X_EF' if extended else 'INTRASTAT_X_SF'
