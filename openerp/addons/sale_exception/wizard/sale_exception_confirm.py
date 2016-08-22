# -*- coding: utf-8 -*-
# © 2011 Raphaël Valyi, Renato Lima, Guewen Baconnier, Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api


class SaleExceptionConfirm(models.TransientModel):

    _name = 'sale.exception.confirm'

    sale_id = fields.Many2one('sale.order', 'Sale')
    exception_ids = fields.Many2many('sale.exception',
                                     string='Exceptions to resolve',
                                     readonly=True)
    ignore = fields.Boolean('Ignore Exceptions')

    @api.model
    def default_get(self, field_list):
        res = super(SaleExceptionConfirm, self).default_get(field_list)
        order_obj = self.env['sale.order']
        sale_id = self._context.get('active_ids')
        assert len(sale_id) == 1, "Only 1 ID accepted, got %r" % sale_id
        sale_id = sale_id[0]
        sale = order_obj.browse(sale_id)
        exception_ids = [e.id for e in sale.exception_ids]
        res.update({'exception_ids': [(6, 0, exception_ids)]})
        res.update({'sale_id': sale_id})
        return res

    @api.one
    def action_confirm(self):
        if self.ignore:
            self.sale_id.ignore_exception = True
        return {'type': 'ir.actions.act_window_close'}
