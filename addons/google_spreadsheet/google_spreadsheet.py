##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP SA (<http://www.openerp.com>).
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


class config(osv.osv):
    _inherit = 'google.drive.config'

    def set_spreadsheet(self, cr, uid, model, domain, groupbys, view_id, context=None):
        try:
            config_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'google_spreadsheet', 'google_spreadsheet_template')[1]
        except ValueError:
            raise
        config = self.browse(cr, uid, config_id, context=context)
        res = self.copy_doc(cr, uid, 1, config.google_drive_resource_id, 'Spreadsheet %s' % model, model, context=context)
        return res
