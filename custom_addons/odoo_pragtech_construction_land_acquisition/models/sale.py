# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_lease = fields.Boolean('Is Lease')
    is_sale = fields.Boolean('Is Sale')
    proposal_id = fields.Many2one('land.proposal', 'Proposal')
    acquisition_id = fields.Many2one('land.acquisition', 'Acquisition')

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'proposal_id': self.proposal_id.id,
            'is_lease': self.is_lease,
            'is_sale': self.is_sale,
        })

        return res

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        orders = self.env['sale.order'].search([('acquisition_id', '=', self.acquisition_id.id), ('id', '!=', self.id), ('state', '!=', 'draft')])
        if orders:
            raise UserError(_('Please check this property was already been booked?'))

        proposals = self.env['land.proposal'].search([('acquisition_id', '=', self.acquisition_id.id), ('id', '!=', self.proposal_id.id)])
        if proposals:
            for proposal in proposals:
                proposal.write({'state': 'cancel'})

        if self.is_lease == True:
            self.proposal_id.acquisition_id.write({'state': 'book'})

        if self.is_sale == True:
            self.proposal_id.acquisition_id.write({'state': 'sold'})

        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        if self.state not in ('draft'):
            if self.acquisition_id:
                self.acquisition_id.write({'state': 'draft'})

        return res


class SaleLine(models.Model):
    _inherit = 'sale.order.line'

    is_lease = fields.Boolean('Is Lease')
    is_sale = fields.Boolean('Is Sale')
    proposal_id = fields.Many2one('land.proposal', 'Proposal')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To date')
    unit = fields.Char('Unit')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict')

    def _prepare_invoice_line(self, **optional_values):
        """
            USE: This method is used for update invoice field
        """
        res = super(SaleLine, self)._prepare_invoice_line(**optional_values)
        res.update({
            'proposal_id': self.proposal_id.id,
            'is_lease': self.is_lease,
            'is_sale': self.is_sale,
            'from_date': self.from_date,
            'to_date': self.to_date,
            'unit': self.unit,
        })

        return res

