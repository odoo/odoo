# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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


class res_company(osv.Model):
    _name = "res.company"
    _inherit = "res.company"
    _columns = {
           "gengo_private_key": fields.text("Gengo Private Key"),
           "gengo_public_key": fields.text("Gengo Public Key"),
           "gengo_comment": fields.text("Comments", help="This comment will be automatically be enclosed in each an every request sent to Gengo"),
           "gengo_auto_approve": fields.boolean("Auto Approve Translation ?", help="Jobs are Automatically Approved by Gengo."),
    }

    _defaults = {
        "gengo_auto_approve": True,
    }
