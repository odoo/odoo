# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class calendar_event(osv.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'
    _columns = {
        'opportunity_id': fields.many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]"),
    }

    def create(self, cr, uid, vals, context=None):
        res = super(calendar_event, self).create(cr, uid, vals, context=context)
        obj = self.browse(cr, uid, res, context=context)
        if obj.opportunity_id:
            self.pool.get('crm.lead').log_meeting(cr, uid, [obj.opportunity_id.id], obj.name, obj.start, obj.duration, context=context)
        return res
