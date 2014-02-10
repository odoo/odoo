from openerp.osv import osv, fields

class website(osv.osv):
    _inherit = "website"

    _columns = {
        'channel_id': fields.many2one('im_livechat.channel', string="Channel"),
    }