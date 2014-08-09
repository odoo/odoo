# -*- coding: utf-8 -*-
# #############################################################################
#
# Copyright (c) 2014 Marcos Organizador de Negocios- Eneldo Serrata - http://marcos.do
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Marcos Organizador de Negocios.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################


from openerp import api, _, models, fields
from ..tools import is_ncf
from openerp import netsvc

from datetime import datetime
from openerp.exceptions import except_orm, Warning, RedirectWarning


class account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def _get_reference_type(self):
        return [('none', u'Referencia libre / Nº Fact. Proveedor'),
                ('01', '01 - Gastos de personal'),
                ('02', '02 - Gastos por trabajo, suministros y servicios'),
                ('03', '03 - Arrendamientos'),
                ('04', '04 - Gastos de Activos Fijos'),
                ('05', u'05 - Gastos de Representación'),
                ('06', '06 - Otras Deducciones Admitidas'),
                ('07', '07 - Gastos Financieros'),
                ('08', '08 - Gastos Extraordinarios'),
                ('09', '09 - Compras y Gastos que forman parte del Costo de Venta'),
                ('10', '10 - Adquisiciones de Activos'),
                ('11', '11 - Gastos de Seguro')
        ]

    def on_change_fiscal_position(self, cr, uid, ids, value):
        fiscal_type = self.pool.get("account.fiscal.position").browse(cr, uid, value).fiscal_type
        if fiscal_type in [u'informal', u'minor']:
            ncf_required = False
        else:
            ncf_required = True
        return {"value": {'reference_type': fiscal_type, 'ncf_required': ncf_required}}

    def onchange_journal_id(self, cr, uid, ids, *args):
        if args:
            journal = self.pool.get("account.journal").browse(cr, uid, args[0])
            ncf_required = True
            if journal.ncf_special:
                ncf_required = False
            return {"value": {'ncf_required': ncf_required}}
        else:
            return {"value": {}}

    def onchange_reference(self, cr, uid, ids, reference, ncf_required):
        if reference:
            if not is_ncf(reference) and ncf_required:
                raise except_orm(u"NCF Invalido!", u"El NCF del proveedor no es válido!")
        return False

    def action_date_assign(self, cr, uid, ids, *args):
        for inv in self.browse(cr, uid, ids):
            if inv.journal_id.ncf_special in ['gasto', 'informal']:
                self.write(cr, uid, [inv.id], {"reference": False})
            if inv.type in ['in_invoice', 'in_refund'] and inv.ncf_required:
                if inv.reference_type != 'none' and not is_ncf(inv.reference.encode("ascii")):
                    raise except_orm(u"NCF Invalido!", u"El NCF del proveedor no es válido!")
                    # TODO si la entrada de almacen referente a este pedido advertir al contador que debe terminar de recibir
                    # los productos pendientes o cancelarlos en caso de que se reciba parciarmente debe crear una nota de credito
                    # borrador

            res = self.onchange_payment_term_date_invoice(cr, uid, inv.id, inv.payment_term.id, inv.date_invoice)
            if res and res['value']:
                self.write(cr, uid, [inv.id], res['value'])
        return True


    reference_type  = fields.Selection(_get_reference_type, 'Payment Reference', required=True, readonly=True, states={'draft': [('readonly', False)]})
    reference       = fields.Char('Invoice Reference', size=19, help="Numero de comprobante fiscal.", readonly=True, states={'draft': [('readonly', False)]})
    ipf     = fields.Boolean("Impreso", readonly=False, default=False)
    ncf_required    = fields.Boolean("ncf_required", default=True)
    pay_to          = fields.Many2one("res.partner", "Pagar a")
    internal_number = fields.Char('Invoice Number', size=32, readonly=True, states={'draft': [('readonly', False)]})
    parent_id       = fields.Many2one('account.invoice', 'Parent Invoice', readonly=True, states={'draft': [('readonly', False)]}, help='This is the main invoice that has ' 'generated this credit note')
    child_ids       = fields.One2many('account.invoice', 'parent_id', 'Debit and Credit Notes', readonly=True, states={'draft': [('readonly', False)]}, help='These are all credit and debit ' 'to this invoice')


    def _get_journal_id(self, fiscal_type, warehouse_id, refund):

        if refund:
            return warehouse_id.notas_credito_id.id
        elif fiscal_type == "final" or fiscal_type is None:
            return warehouse_id.final_id.id
        elif fiscal_type == "fiscal":
            return warehouse_id.fiscal_id.id
        elif fiscal_type == "special":
            return warehouse_id.especiales_id.id
        elif fiscal_type == "gov":
            return warehouse_id.gubernamentales_id.id
        else:
            return False

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}

        if context.get('active_model', False) == 'pos.order' and vals.get('type', False) in ["out_invoice",
                                                                                             'out_refund']:
            pass
        elif context.get('active_model', False) == 'stock.picking.in' and vals.get('type', False) == "out_refund":
            pass
        elif vals.get('type', False) == "out_invoice":
            order_obj = self.pool.get('sale.order')
            so_id = order_obj.search(cr, uid, [('name', '=', vals['origin'])])
            so = order_obj.browse(cr, uid, so_id, context)[0]
            if not vals['fiscal_position']: vals['fiscal_position'] = 2
            fiscal_type = so.partner_id.property_account_position.fiscal_type or 'final'
            vals['journal_id'] = self._get_journal_id(fiscal_type, so.warehouse_id, False)
        elif vals.get('type', False) == "out_refund":
            if vals.get('origin', False):
                order_obj = self.pool.get('sale.order')
                so_id = order_obj.search(cr, uid, [('name', '=', vals.get('origin', None))])
                so = order_obj.browse(cr, uid, so_id, context)[0]
                if not vals['fiscal_position']:
                    vals['fiscal_position'] = 2
                vals['journal_id'] = self._get_journal_id(None, so.shop_id, True)
            else:
                vals['reference'] = u""
                inv_obj = self.pool.get('account.invoice')
                origin = inv_obj.read(cr, uid, context['active_id'], ['number'])
                vals['origin'] = origin["number"]
        elif vals.get('type', False) == "in_invoice" and vals.get('fiscal_position', False):
            fiscal_type = self.pool.get("account.fiscal.position").browse(cr, uid, vals['fiscal_position']).fiscal_type
            vals['reference_type'] = fiscal_type
        elif vals.get('type', False) == "in_refund" and vals.get('fiscal_position', False):
            vals['reference'] = vals.get('origin', "")
            fiscal_type = self.pool.get("account.fiscal.position").browse(cr, uid, vals['fiscal_position']).fiscal_type
            vals['reference_type'] = fiscal_type

        inv = super(account_invoice, self).create(cr, uid, vals, context)
        return inv

        # go from canceled state to draft state

    def action_cancel_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft', 'internal_number': False})
        wf_service = netsvc.LocalService("workflow")
        for inv_id in ids:
            wf_service.trg_delete(uid, 'account.invoice', inv_id, cr)
            wf_service.trg_create(uid, 'account.invoice', inv_id, cr)
        return True

    def _refund_cleanup_lines(self, cr, uid, lines, context=None):
        """
        For each invoice line.
            If amount of days since invoice is greater than 30.
                For each tax on each invoice line.
                If the tax is included in the price.
                The tax is replaced with the corresponding tax exempt tax.
                If tax is not include in price, no tax will show up in the refund.

        """

        result = super(account_invoice, self)._refund_cleanup_lines(cr, uid, lines, context=context)

        # For each invoice_line
        for x, y, line in result:
            inv_obj = self.pool.get('account.invoice').browse(cr, uid, line['invoice_id'], context=context)
            inv_date = datetime.strptime(inv_obj['date_invoice'], "%Y-%m-%d").date()
            days_diff = datetime.today().date() - inv_date
            # If amount of days since invoice is greater than 30:
            if days_diff.days > 30:
                taxes_ids = []
                # For each tax on the invoice line:
                for tax_id in line['invoice_line_tax_id'][0][2]:
                    tax_original = self.pool.get('account.tax').browse(cr, uid, tax_id, context=context)
                    # If the tax is included in the price:
                    if tax_original.price_include:
                        # Replace it with the corresponding tax exempt tax.
                        tax_replacement = self.pool.get('account.tax').search(cr, uid,
                                                                              [('type_tax_use', '=',
                                                                                tax_original.type_tax_use),
                                                                               ('amount', '=', tax_original.amount),
                                                                               ('exempt', '=', True),
                                                                              ],
                                                                              context=context)[0]
                        # No duplicate taxes allowed
                        if tax_replacement not in taxes_ids:
                            taxes_ids.append(tax_replacement)
                # If tax is not include in price, no tax will show up in the refund.
                line['invoice_line_tax_id'] = [(6, 0, taxes_ids)]

        return result

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        inv = self.search([('origin', '=', move_lines[0][2]['ref'])])
        if inv.pay_to:
            supplier_account_id = inv.partner_id.property_account_payable.id
            for line in [lines[2] for lines in move_lines]:
                if line.get("account_id", False) == supplier_account_id:
                    line.update({'partner_id': inv.pay_to.id, 'account_id': inv.pay_to.property_account_payable.id})
        return move_lines


    @api.multi
    def action_move_create(self):
        for inv in self:
            if not is_ncf(inv.reference) and inv.ncf_required and inv.type == 'in_invoice':
                raise except_orm(u"NCF Invalido!", u"El NCF del proveedor no es válido!")
            if self.search([('number', '=', inv.reference), ("partner_id", '=', inv.partner_id.id)]) and inv.type == 'in_invoice':
                raise except_orm(_(u'Número de comprobante fiscal duplicado!'), _('Ya existe es numero de NCF para este proveedor.'))
        return super(account_invoice, self).action_move_create()