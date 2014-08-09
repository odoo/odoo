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
from openerp.osv import orm, fields


class stock_warehouse(orm.Model):
    _inherit = "stock.warehouse"
    _description = "Warehouse"

    _columns = {
        'fiscal_id': fields.many2one('account.journal', u'NCF Con valor fiscal', help=u"Facturas que Generan Crédito y Sustentan Costos y/o Gastos.", required=True),
        'final_id': fields.many2one('account.journal', u'NCF Consumidor final', help=u"Facturas para Consumidores Finales.", required=True),
        'especiales_id': fields.many2one('account.journal', u'NCF Regímenes Especiales', help=u"Regímenes Especiales de Tributación.", required=True),
        'gubernamentales_id': fields.many2one('account.journal', u'NCF Gubernamentales', help=u"Comprobantes Gubernamentales.", required=True),
        'notas_credito_id': fields.many2one('account.journal', u'NCF Notas de credito', help=u"Comprobantes Notas de credito.", required=True),
        'default_partner_id': fields.many2one('res.partner', u'Cliente de contado', help=u"Se asignara este cliente por defecto cuando "
                                                                                      u"cuando se grabe la factura sin un cliente seleccionado."),
        'default_receipt_journal_id': fields.many2one('account.journal', u'Diario de recibos de clientes', help=u"Define el diario para los recibos hechos pendiente de cobrar.", required=True)
    }
