# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class UpdateBooks(models.TransientModel):
    _name = "update.books"
    _description = "Update Books"

    name = fields.Many2one('product.product', 'Book Name', required=True)

    @api.multi
    def action_update_books(self):
        lib_book_obj = self.env['library.book.issue']
        for rec in self:
            if self._context.get('active_ids'):
                for active_id in self._context.get('active_ids'):
                    lib_book_obj.browse(active_id).write({'name': rec.name.id})
        return {}
