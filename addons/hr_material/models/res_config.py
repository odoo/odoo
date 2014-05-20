
import urlparse

from openerp.osv import fields, osv

class hr_config_settings(osv.osv_memory):
    _inherit = 'hr.config.settings'

    def get_default_alias_material(self, cr, uid, ids, context=None):
        alias_name = False
        alias_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'hr_material.mail_alias_material')
        if alias_id:
            alias_name = self.pool['mail.alias'].browse(cr, uid, alias_id, context=context).alias_name
        return {'alias_prefix': alias_name}

    def set_default_alias_material(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            default_alias_prefix = self.get_default_alias_material(cr, uid, ids, context=context)['alias_prefix']
            if record.alias_prefix != default_alias_prefix:
                alias_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'hr_material.mail_alias_material')
                if alias_id:
                    self.pool.get('mail.alias').write(cr, uid, alias_id, {'alias_name': record.alias_prefix}, context=context)
        return True

    def get_default_alias_domain(self, cr, uid, ids, context=None):
        alias_domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "mail.catchall.domain", context=context)
        if not alias_domain:
            domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.base.url", context=context)
            try:
                alias_domain = urlparse.urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
