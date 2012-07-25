from openerp.osv import osv, fields

class base_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'auth_signup_template_user_id': fields.many2one('res.users', 'Template user for signup')
    }

    def get_default_signup(self, cr, uid, fields, context=None):
        icp = self.pool.get('ir.config_parameter')
        return {
            'auth_signup_template_user_id': icp.get_param(cr, uid, 'auth.signup_template_user_id', 0) or False
        }

    def set_signup(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)
        icp = self.pool.get('ir.config_parameter')
        icp.set_param(cr, uid, 'auth.signup_template_user_id', config.signup_user_template_id.id)

