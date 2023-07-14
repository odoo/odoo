# -*- coding: utf-8 -*-

from odoo import models

# ISO_3166_RO_CODES = {"Alba": "RO-AB", "Arad": "RO-AR", "Argeș": "RO-AG", "Bacău": "RO-BC", "Bihor": "RO-BH",
#                      "Bistrița-Năsăud": "RO-BN", "Botoșani": "RO-BT", "Brașov": "RO-BV", "Brăila": "RO-BR",
#                      "Buzău": "RO-BZ", "Caraș-Severin": "RO-CS", "Călărași": "RO-CL", "Cluj": "RO-CJ",
#                      "Constanța": "RO-CT", "Covasna": "RO-CV", "Dâmbovița": "RO-DB", "Dolj": "RO-DJ", "Galați": "RO-GL",
#                      "Giurgiu": "RO-GR", "Gorj": "RO-GJ", "Harghita": "RO-HR", "Hunedoara": "RO-HD",
#                      "Ialomița": "RO-IL", "Iași": "RO-IS", "Ilfov": "RO-IF", "Maramureș": "RO-MM", "Mehedinți": "RO-MH",
#                      "Mureș": "RO-MS", "Neamț": "RO-NT", "Olt": "RO-OT", "Prahova": "RO-PH", "Satu Mare": "RO-SM",
#                      "Sălaj": "RO-SJ", "Sibiu": "RO-SB", "Suceava": "RO-SV", "Teleorman": "RO-TR", "Timiș": "RO-TM",
#                      "Tulcea": "RO-TL", "Vaslui": "RO-VS", "Vâlcea": "RO-VL", "Vrancea": "RO-VN", "București": "RO-B", }


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_ro'
    _description = "CIUS RO"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._get_partner_address_vals(partner)

        # TODO
        # vals["country_subentity"] = ISO_3166_RO_CODES[vals["city_name"]]

        return vals

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        vals['vals']['customization_id'] = 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1'

        # <assert test="(normalize-space(cbc:TaxCurrencyCode) = 'RON' and normalize-space(cbc:DocumentCurrencyCode) != 'RON') or (normalize-space(cbc:TaxCurrencyCode) = 'RON' and normalize-space(cbc:DocumentCurrencyCode) = 'RON')  or (normalize-space(cbc:TaxCurrencyCode) != 'RON' and normalize-space(cbc:DocumentCurrencyCode) = 'RON') or (not(exists (cbc:TaxCurrencyCode)) and normalize-space(cbc:DocumentCurrencyCode) = 'RON')"

        return vals
