# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

from openerp import models, api, fields, _
import logging
_logger = logging.getLogger(__name__)


class calendar_event(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    phonecall_id = fields.Many2one('crm.phonecall', 'Phonecall')
    opportunity_id = fields.Many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]")

    @api.model
    def create(self, vals):
        
        obj = super(calendar_event, self).create(vals)
        if obj.opportunity_id:
            
            obj.opportunity_id.log_meeting(obj.name, obj.start, obj.duration)
        
        return obj

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
