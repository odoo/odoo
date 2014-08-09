# -*- coding: utf-8 -*-
##############################################################################
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

from openerp.osv import orm, fields, osv
from openerp.tools.translate import _
from openerp import api


class account_fiscal_position(orm.Model):
    _name = 'account.fiscal.position'
    _inherit = 'account.fiscal.position'

    def _get_fiscal_type(self, cursor, user_id, context=None):
        return (
            ("fiscal", u"Facturas que Generan Crédito y Sustentan Costos y/o Gastos"),
            ("final", u"Facturas para Consumidores Finales"),
            ("final_note", u"Nota de crédito a consumidor final"),
            ("fiscal_note", u"Nota de crédito con derecho a crédito fiscal"),
            ("special", u"Regímenes Especiales de Tributación"),
            ("gov", u"Comprobantes Gubernamentales"),
            ("informal", u"Proveedores Informales"),
            ("minor", u"Gastos Menores"),
            ('01', u'01 - Gastos de personal'),
            ('02', u'02 - Gastos por trabajo, suministros y servicios'),
            ('03', u'03 - Arrendamientos'),
            ('04', u'04 - Gastos de Activos Fijos'),
            ('05', u'05 - Gastos de Representación'),
            ('06', u'06 - Otras Deducciones Admitidas'),
            ('07', u'07 - Gastos Financieros'),
            ('08', u'08 - Gastos Extraordinarios'),
            ('09', u'09 - Compras y Gastos que forman parte del Costo de Venta'),
            ('10', u'10 - Adquisiciones de Activos'),
            ('11', u'11 - Gastos de Seguro')
        )

    _columns = {
        "fiscal_type": fields.selection(_get_fiscal_type, "Tipo de NCF"),
        "for_supplier": fields.boolean("Para proveedores")
    }


class account_journal(orm.Model):
    _order = "name"
    _inherit = 'account.journal'
    _columns = {
        'ipf_payment_type': fields.selection([('1', 'Efectivo'),
                                              ('2', 'Cheque'),
                                              ('3', 'Tarjeta de credito'),
                                              ('4', 'Tarjeta de debito'),
                                              ('5', 'Tarjeta propia'),
                                              ('6', 'Cupon'),
                                              ('7', 'Otros 1'),
                                              ('8', 'Otros 2'),
                                              ('9', 'Otros 3'),
                                              ('10', 'Otros 4'),
                                              ('11', 'Nota de credito')
                                             ], 'Formas de pago impresora fiscal', required=False,
                                             help="Esta configuracion se encuantra internamente en la impresora fiscal y debe de especificar esta opecion. " \
                                                  "Esta es la forma en que la impresora fiscal registra el pago en los libros."),
        'type': fields.selection([('sale', 'Sale'),
                                  ('sale_refund', 'Sale Refund'),
                                  ('purchase', 'Purchase'),
                                  ('purchase_refund', 'Purchase Refund'),
                                  ('cash', u'Forma de pago en Efectivo/Cheque'),
                                  ('bank', u'Forma de pago Tarjeta/Transferencia'),
                                  ('general', 'General'),
                                  ('situation', 'Opening/Closing Situation')], 'Type', size=32, required=True,
                                 help="Select 'Sale' for customer invoices journals." \
                                      " Select 'Purchase' for supplier invoices journals." \
                                      " Select 'Cash' or 'Bank' for journals that are used in customer or supplier payments." \
                                      " Select 'General' for miscellaneous operations journals." \
                                      " Select 'Opening/Closing Situation' for entries generated for new fiscal years."),
        "ncf_special": fields.selection([("gasto", "Gastos Menores"),
                                         ("informal", "Proveedores Informales"),
                                         ("pruchase", "Diario de compra por caja chica")], "Compras Especiales", help="Debe marcar esta casilla si el diario esta destinado pa generar comprobantes especiales de compra como Gastos Menores o Proveedores informales."),
        "special_partner": fields.many2one("res.partner", "Empresa para gastos menores"),
        "special_product": fields.many2one("product.product", "Producto para gastos menores"),
        "is_cjc": fields.boolean("Caja Chica", help="Marcar si usara este diario para control de efectivo de caja chica"),
        "informal_journal_id": fields.many2one("account.journal", "Diario de Proveedores informales"),
        "gastos_journal_id": fields.many2one("account.journal", "Diario de Gastos Menores"),
        "purchase_journal_id": fields.many2one("account.journal", "Diario Compras"),
        "pay_to": fields.many2one("res.partner", "Pagar a")

    }


class account_tax(osv.osv):
    _inherit = 'account.tax'

    _columns = {
        "exempt": fields.boolean("Exempt"),
        "itbis": fields.boolean("ITBIS"),
        "retention": fields.boolean(u"Retención")
    }

    # Validate if each tax is marked as 'exempt' and zero the 'amount'
    @api.v7
    def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False):
        result = super(account_tax, self).compute_all(cr, uid, taxes, price_unit, quantity, product=product,
                                                      partner=partner, force_excluded=force_excluded)
        for tax in result['taxes']:
            tax_obj = self.pool.get('account.tax').browse(cr, uid, tax['id'])
            if tax_obj.exempt:
                tax['amount'] = 0.0
        return result


    @api.v8
    def compute_all(self, price_unit, quantity, product=None, partner=None, force_excluded=False):
        return self._model.compute_all(
            self._cr, self._uid, self, price_unit, quantity,
            product=product, partner=partner, force_excluded=force_excluded)

class account_move(orm.Model):
    _inherit = "account.move"
    _description = "Account Entry"
    _order = 'id desc'

    def post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice = context.get('invoice', False)

        try:
            if invoice.type in ["in_invoice", "in_refund"]:
                invoice.internal_number = invoice.reference
        except:
            pass

        valid_moves = self.validate(cr, uid, ids, context)

        if not valid_moves:
            raise orm.except_osv(_('Error!'), _(
                'You cannot validate a non-balanced entry.\nMake sure you have configured payment terms properly.\nThe latest payment term line should be of the "Balance" type.'))
        obj_sequence = self.pool.get('ir.sequence')
        for move in self.browse(cr, uid, valid_moves, context=context):
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                        new_name = obj_sequence.next_by_id(cr, uid, journal.sequence_id.id, c)
                    else:
                        raise orm.except_osv(_('Error!'), _('Please define a sequence on the journal.'))

                if new_name:
                    self.write(cr, uid, [move.id], {'name': new_name})

        cr.execute('UPDATE account_move ' \
                   'SET state=%s ' \
                   'WHERE id IN %s',
                   ('posted', tuple(valid_moves),))
        return True