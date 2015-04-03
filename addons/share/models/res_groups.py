# -*- coding: utf-8 -*-

from openerp import api, fields, models, SUPERUSER_ID

class ResGroups(models.Model):
    _name = "res.groups"
    _inherit = 'res.groups'
    
    share = fields.Boolean(string='Share Group', readonly=True,
                     help="Group created to set access rights for sharing data with some users.")

    def init(self, cr):
        # force re-generation of the user groups view without the shared groups
        self.update_user_groups_view(cr, SUPERUSER_ID)
        parent_class = super(ResGroups, self)
        if hasattr(parent_class, 'init'):
            parent_class.init(cr)

    @api.model
    def get_application_groups(self, domain=None):
        if domain is None:
            domain = []
        domain.append(('share', '=', False))
        return super(ResGroups, self).get_application_groups(domain=domain)
