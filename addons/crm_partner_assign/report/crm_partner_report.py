# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from osv import fields,osv
import tools


class crm_partner_report_assign(osv.osv):
    """ CRM Lead Report """
    _name = "crm.partner.report.assign"
    _auto = False
    _description = "CRM Partner Report"
    _columns = {
        'name': fields.char('Partner name', size=64, required=False, readonly=True),
        'grade_id':fields.many2one('res.partner.grade', 'Grade', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sales Team', readonly=True),
        'nbr': fields.integer('# of Partner', readonly=True),
        'opp': fields.integer('# of Opportunity', readonly=True),
    }

    def init(self, cr):

        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'crm_partner_report_assign')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_partner_report_assign AS (
                SELECT
                    p.id,
                    p.name,
                    a.country_id,
                    p.grade_id,
                    p.user_id,
                    p.section_id,
                    1 as nbr,
                    (SELECT count(id) FROM crm_lead WHERE partner_assigned_id=p.id) AS opp
                FROM
                    res_partner p
                    left join res_partner_address a on (p.id=a.partner_id)
            )""")

crm_partner_report_assign()
