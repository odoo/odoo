# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError


class CardNumber(models.TransientModel):
    _name = "card.number"
    _description = "Card Number"

    card_id = fields.Many2one("library.card", "Card No", required=True)

    @api.multi
    def card_number_ok(self):
        lib_book_obj = self.env['library.book.issue']
        for rec in self:
            domain = [('card_id', '=', rec.card_id.id)]
            search_card_ids = lib_book_obj.search(domain)
            if not search_card_ids:
                raise UserError(_('Invalid Card Number.'))
            else:
                return {'type': 'ir.actions.act_window',
                        'res_model': 'book.name',
                        'src_model': 'library.book.issue',
                        'target': 'new',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'context': {'default_card_id': rec.card_id.id}}
