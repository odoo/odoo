# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Jean Ventura (<http://venturasystems.net>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class marcos_z_report(osv.osv_memory):
    """
    To generate Z Report.

    """

    _name = "marcos.z.report"
    _description = "Z Report"

    _columns = {
        'filter_type': fields.selection([('cashier', 'Informe de cajero'),
                                         ('last', 'Last Report'),
                                         ('period', 'By Period'),
                                         ('sequence', 'By Sequence'),
                                         ], 'Filter Type', required=True),
        'period_from': fields.date('From'),
        'period_to': fields.date('To'),
        'sequence_from': fields.integer(u"From"),
        'sequence_to': fields.integer(u"To"),
    }

    _defaults = {'filter_type': 'cashier'
                 }

    def get_host(self, cr, uid, filter_type, period_from, period_to, sequence_from, sequence_to, context=None):
        res_user_obj = self.pool.get("res.users")
        pos_conf = res_user_obj.browse(cr, uid, uid, context).pos_config
        if pos_conf.payment_pos:
            host = pos_conf.payment_pos.iface_printer_host.split(":")[0]+":8080/ipf/command"
        else:
            host = pos_conf.iface_printer_host

        data = {}


        if filter_type == "last":
            data.update({u"command": u"0801", u"extension": u"0001"})
        elif filter_type == "period":
            data.update({"command": "0930", "extension": "0001", "a": "".join(period_from.split("-")[::-1]), "b": "".join(period_to.split("-")[::-1])})
        elif filter_type == "sequence":
            data.update({"command": "0931", "extension": "0001", "a": sequence_from, "b": sequence_to})
        elif filter_type == "cashier":
            data.update({u"command": u"0802", u"extension": u"0001"})

        return {"host": host, "data": data}
