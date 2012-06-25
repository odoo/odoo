from openerp.osv import osv, fields

class ResConfig(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'signup_user_template_id': fields.many2one('res.users', 'Template user for account creation')
    }

    def get_default_user_tpl(self, cr, uid, fields, context=None):
        icp = self.pool.get('ir.config_parameter')
        return {
            'signup_user_template_id': icp.get_param(cr, uid, 'signup.user_template_id', 0) or False
        }

    def set_user_template(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)
        icp = self.pool.get('ir.config_parameter')
        icp.set_param(cr, uid, 'signup.user_template_id', config.signup_user_template_id.id)
