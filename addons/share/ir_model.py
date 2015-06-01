# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import osv

class ir_model_access(osv.Model):
    _inherit = 'ir.model.access'

    # overload group_names_with_access() to avoid returning sharing groups
    # by filtering out groups with share=true.
    def group_names_with_access(self, cr, model_name, access_mode):
        """Returns the names of visible groups which have been granted ``access_mode`` on
           the model ``model_name``.
           :rtype: list
        """
        assert access_mode in ['read','write','create','unlink'], 'Invalid access mode: %s' % access_mode
        cr.execute('''SELECT
                        c.name, g.name
                      FROM
                        ir_model_access a
                        JOIN ir_model m ON (a.model_id=m.id)
                        JOIN res_groups g ON (a.group_id=g.id)
                        LEFT JOIN ir_module_category c ON (c.id=g.category_id)
                      WHERE
                        m.model=%s AND
                        a.active IS true AND
                        (g.share IS NULL or g.share IS false) AND
                        a.perm_''' + access_mode, (model_name,))
        return [('%s/%s' % x) if x[0] else x[1] for x in cr.fetchall()]
    
