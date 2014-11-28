from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _

class crm_opportunity2phonecall(osv.TransientModel):
    """Converts Opportunity to Phonecall"""
    _inherit = 'crm.phonecall2phonecall'
    _name = 'crm.opportunity2phonecall'
    _description = 'Opportunity to Phonecall'

    def default_get(self, cr, uid, fields, context=None):
        opp_obj = self.pool['crm.lead']
        categ_id = False
        data_obj = self.pool['ir.model.data']
        try:
            res_id = data_obj._get_id(cr, uid, 'crm', 'categ_phone2')
            categ_id = data_obj.browse(cr, uid, res_id, context=context).res_id
        except ValueError:
            pass
        record_ids = context and context.get('active_ids', []) or []
        res = {}
        res.update({'action': 'log', 'date': str(datetime.now())})
        for opp in opp_obj.browse(cr, uid, record_ids, context=context):
            if 'name' in fields:
                res.update({'name': opp.name})
            if 'user_id' in fields:
                res.update({'user_id': opp.user_id and opp.user_id.id or False})
            if 'team_id' in fields:
                res.update({'team_id': opp.team_id and opp.team_id.id or False})
            if 'partner_id' in fields:
                res.update({'partner_id': opp.partner_id and opp.partner_id.id or False})
            if 'contact_name' in fields:
                res.update({'contact_name': opp.partner_id and opp.partner_id.name or False})
            if 'phone' in fields:
                res.update({'phone': opp.phone or (opp.partner_id and opp.partner_id.phone or False)})
        return res

    def action_schedule(self, cr, uid, ids, context=None):
        value = {}
        if context is None:
            context = {}
        opportunity_ids = context and context.get('active_ids') or []
        oppor_to_phonecall_id = self.browse(cr, uid, ids, context=context)[0]
        call_ids = self.pool['crm.lead'].schedule_phonecall(cr, uid, opportunity_ids, oppor_to_phonecall_id.date, oppor_to_phonecall_id.name, \
                oppor_to_phonecall_id.note, oppor_to_phonecall_id.phone, oppor_to_phonecall_id.contact_name, oppor_to_phonecall_id.user_id and oppor_to_phonecall_id.user_id.id or False, \
                oppor_to_phonecall_id.team_id and oppor_to_phonecall_id.team_id.id or False, \
                oppor_to_phonecall_id.categ_id and oppor_to_phonecall_id.categ_id.id or False, \
                action=oppor_to_phonecall_id.action, context=context)
        return {'type': 'ir.actions.act_window_close'}
