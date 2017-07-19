# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SBRCode(models.Model):
    _name = 'l10n_nl.sbr'
    _description = 'Standard Business Reporting'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code', required=True)
    reference = fields.Char(string='Reference')

    @api.multi
    @api.depends('name', 'reference')
    def name_get(self):
        result = []
        for sbr in self:
            if not sbr.name or not sbr.reference:
                continue
            result.append((sbr.id, sbr.reference + ' ' + sbr.name))
        return result
