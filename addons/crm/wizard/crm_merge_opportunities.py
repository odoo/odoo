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
from crm import crm
from osv import osv, fields
from tools.translate import _

class crm_merge_opportunity(osv.osv_memory):
    """Merge two Opportunities"""

    _name = 'crm.merge.opportunity'
    _description = 'Merge two Opportunities'

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        """
        record_id = context and context.get('active_id', False) or False
        if record_id:
            opp_obj = self.pool.get('crm.lead')
            opp = opp_obj.browse(cr, uid, record_id, context=context)
            if not opp.partner_id:
                raise osv.except_osv(_('Warning!'), _('Opportunity must have Partner assigned before merging with other Opportunity.'))
            #Search for Opportunity for the same partner
            opp_ids = opp_obj.search(cr, uid, [('partner_id', '=', opp.partner_id.id), ('type', '=', 'opportunity'), ('state', 'in', ('open', 'pending'))])
            # Removing current opportunity
            if record_id in opp_ids:
                opp_ids.remove(record_id)
            if not opp_ids:
                raise osv.except_osv(_('Warning!'), _("There are no other 'Open' or 'Pending' Opportunities for the partner '%s'.") % (opp.partner_id.name))
        pass


    def action_merge(self, cr, uid, ids, context=None):
        """
        This function merges two opportunities
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Opportunity IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Opportunity form
        """
        record_id = context and context.get('active_id', False) or False
        if record_id:
            opp_obj = self.pool.get('crm.lead')
            message_obj = self.pool.get('mailgate.message')
            current_opp = opp_obj.browse(cr, uid, record_id, context=context)

            for this in self.browse(cr, uid, ids, context=context):
                for opp in this.opportunity_ids:
                    opp_obj.write(cr, uid, [opp.id], {
                                    'stage_id': opp.stage_id.id or current_opp.stage_id.id or False,
                                    'priority': opp.priority or current_opp.priority,
                                    'email_from': opp.email_from or current_opp.email_from,
                                    'phone': opp.phone or current_opp.phone,
                                    'section_id': opp.section_id.id or current_opp.section_id.id or False,
                                    'categ_id': opp.categ_id.id or current_opp.categ_id.id or False,
                                    'description': (opp.description or '') + '\n' + (current_opp.description or ''),
                                    'partner_name': opp.partner_name or current_opp.partner_name,
                                    'title': opp.title.id or current_opp.title.id or False,
                                    'function': opp.function or current_opp.function,
                                    'street': opp.street or current_opp.street,
                                    'street2': opp.street2 or current_opp.street2,
                                    'zip': opp.zip or current_opp.zip,
                                    'city': opp.city or current_opp.city,
                                    'country_id': opp.country_id.id or current_opp.country_id.id or False,
                                    'state_id': opp.state_id.id or current_opp.state_id.id or False,
                                    'fax': opp.fax or current_opp.fax,
                                    'mobile': opp.mobile or current_opp.mobile,
                                    'email_cc': ','.join(filter(lambda x: x, [opp.email_cc, current_opp.email_cc]))
                                })
                    for history in current_opp.message_ids:
                        if history.history:
                            new_history = message_obj.copy(cr, uid, history.id, default={'res_id': opp.id})
                    opp_obj._history(cr, uid, [current_opp], _('Merged into Opportunity: %s') % (opp.id))

            if this.state == 'unchanged':
                    pass
            elif this.state == 'done':
                opp_obj.case_close(cr, uid, [record_id])
            elif this.state == 'draft':
                opp_obj.case_reset(cr, uid, [record_id])
            elif this.state in ['cancel', 'open', 'pending']:
                act = 'case_' + this.state
                getattr(opp_obj, act)(cr, uid, [record_id])
        return {'type': 'ir.actions.act_window_close'}

    _columns = {
        'opportunity_ids' : fields.many2many('crm.lead',  'merge_opportunity_rel', 'merge_id', 'opportunity_id', 'Opportunities', domain=[('type', '=', 'opportunity')]),
        'state': fields.selection(crm.AVAILABLE_STATES + [('unchanged', 'Unchanged')], string='Set State To', required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        @return : default values of fields.
        """
        record_id = context and context.get('active_id', False) or False
        res = super(crm_merge_opportunity, self).default_get(cr, uid, fields, context=context)

        if record_id:
            opp_obj = self.pool.get('crm.lead')
            opp = opp_obj.browse(cr, uid, record_id, context=context)
            opp_ids = opp_obj.search(cr, uid, [('partner_id', '=', opp.partner_id.id), ('type', '=', 'opportunity'), ('state', 'in', ('open', 'pending'))])
            # Removing current opportunity
            if record_id in opp_ids:
                opp_ids.remove(record_id)

            if 'opportunity_ids' in fields:
                res.update({'opportunity_ids': opp_ids})
            if 'state' in fields:
                res.update({'state': u'cancel'})

        return res

crm_merge_opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
