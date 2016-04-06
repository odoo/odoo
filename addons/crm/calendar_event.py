# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class calendar_event(osv.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    def _is_highlighted(self, cr, uid, ids, field_name, arg, context=None):
        res = super(calendar_event, self)._is_highlighted(cr, uid, ids, field_name, arg, context=context)
        if context.get('active_model') == 'crm.lead':
            for event in self.browse(cr, uid, ids, context=context):
                if event.opportunity_id.id == context.get('active_id'):
                    res[event.id] = True
        return res

    _columns = {
        'opportunity_id': fields.many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]"),
        'is_highlighted': fields.function(_is_highlighted, string='# Meetings Highlight', type='boolean'),
    }

    def create(self, cr, uid, vals, context=None):
        res = super(calendar_event, self).create(cr, uid, vals, context=context)
        obj = self.browse(cr, uid, res, context=context)
        if obj.opportunity_id:
            self.pool.get('crm.lead').log_meeting(cr, uid, [obj.opportunity_id.id], obj.name, obj.start, obj.duration, context=context)
        return res
