from openerp.osv import fields, osv

class web_calendar_contacts(osv.osv):
    _name = 'web_calendar.contacts'    

    _columns = {
        'user_id': fields.many2one('res.users','Me'),
        'partner_id': fields.many2one('res.partner','Contact',required=True),
        'active':fields.boolean('active'),        
     }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'active' : True,        
    }