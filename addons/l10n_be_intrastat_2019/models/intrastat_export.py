# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import xml.etree.ElementTree as ET
from collections import namedtuple

from odoo import api, exceptions, fields, models, _

INTRASTAT_XMLNS = 'http://www.onegate.eu/2010-01-01'


class XmlDeclaration(models.TransientModel):
    _inherit = "l10n_be_intrastat_xml.xml_decl"
    
    def _get_intrastatkey(self):
        supertuple = super(XmlDeclaration,self)._get_intrastatkey()
        return namedtuple("intrastatkey", supertuple._fields + ('EXCNTORI','PARTNERID',))
    
    def _set_Item(self, item, linekey, numlgn, amounts, dispatchmode=False, extendedmode=False):
        super(XmlDeclaration, self)._set_Item(item, linekey, numlgn, amounts, dispatchmode, extendedmode)
        if dispatchmode:
            self._set_Dim(item, 'EXCNTORI', unicode(linekey.EXCNTORI))
            self._set_Dim(item, 'PARTNERID', unicode(linekey.PARTNERID))
            
    def _populate_linekey(self, linekey, inv_line, dispatchmode, extendedmode):
        if super(XmlDeclaration,self)._populate_linekey(linekey, inv_line, dispatchmode, extendedmode):
            if dispatchmode:
                if inv_line.intrastat_product_origin_country_id:
                    linekey['EXCNTORI'] = inv_line.intrastat_product_origin_country_id.code
                else:
                    linekey['EXCNTORI'] = 'QU'
                partner = self.env['res.partner'].browse(inv_line.partner_id.id)
                if partner.country_id.intrastat:
                    linekey['PARTNERID'] = partner.vat
                else:
                    linekey['PARTNERID'] = 'QV999999999999'
            return True
        else:
            return False