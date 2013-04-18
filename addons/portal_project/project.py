# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-TODAY OpenERP S.A (<http://www.openerp.com>).
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

from openerp.osv import osv


class portal_project(osv.Model):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'project.project'

    def _get_visibility_selection(self, cr, uid, context=None):
        """ Override to add portal option. """
        selection = super(portal_project, self)._get_visibility_selection(cr, uid, context=context)
        idx = [item[0] for item in selection].index('public')
        selection.insert((idx + 1), ('portal', 'Portal Users and Employees'))
        return selection
        # return [('public', 'All Users'),
        #         ('portal', 'Portal Users and Employees'),
        #         ('employees', 'Employees Only'),
        #         ('followers', 'Followers Only')]
