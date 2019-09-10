from openerp.osv import osv, fields

class website(osv.osv):
    _inherit = "website"

    _columns = {
        'channel_id': fields.many2one('im_livechat.channel', string="Channel"),
    }

class website_config_settings(osv.osv_memory):
    _inherit = 'website.config.settings'

    _columns = {
        'channel_id': fields.related('website_id', 'channel_id', type='many2one', relation='im_livechat.channel', string='Live Chat Channel'),
    }
