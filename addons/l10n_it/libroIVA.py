# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#    Servabit srl
#    Agile Business Group sagl
#    Domsense srl
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


# ##################################################################################
# Questa vista SQL viene usata solo per far scegliere l'anno di pianificazione all'utente
# Viene infatti costruita una vista XML di tipo tree che contiene solo i diversi anni per i quali stata fatta almeno una pianificazione
# ##################################################################################

from osv import fields, osv

class l10n_chart_it_report_libroIVA (osv.osv):
    _name = "account.report_libroiva"
    _description = "SQL view for libro IVA"
    _auto = False
    _rec_name = "name"
    #_order = "fiscal_year";

    _columns = {
        'name': fields.char('Fiscal year',size=64),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    def init (self, cr) :
        cr.execute("""DROP VIEW IF EXISTS account_report_libroiva""")
        cr.execute("""
                CREATE VIEW account_report_libroiva AS (
                        SELECT  id, name, company_id FROM account_fiscalyear
        )""")
l10n_chart_it_report_libroIVA()


