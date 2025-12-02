# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _description = 'Companies'
    _inherit = ['res.company']

    l10n_sg_unique_entity_number = fields.Char(string='UEN', related="partner_id.l10n_sg_unique_entity_number", readonly=False)

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        company_vat_label = self.env.company.country_id.vat_label
        if company_vat_label:
            for node in arch.iterfind(".//field[@name='vat']"):
                node.set("string", company_vat_label)
        return arch, view
