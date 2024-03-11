# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools, _
from odoo.exceptions import UserError
from odoo.http import request


class Lang(models.Model):
    _inherit = "res.lang"

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            if self.env['website'].search([('language_ids', 'in', self._ids)]):
                raise UserError(_("Cannot deactivate a language that is currently used on a website."))
        return super(Lang, self).write(vals)

    @api.model
    @tools.ormcache_context(keys=("website_id",))
    def get_available(self):
        if request and getattr(request, 'is_frontend', True):
            return self.env['website'].get_current_website().language_ids.get_sorted()
        return super().get_available()

    def action_activate_langs(self):
        """
        Open wizard to install language(s), so user can select the website(s)
        to translate in that language.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add languages'),
            'view_mode': 'form',
            'res_model': 'base.language.install',
            'views': [[False, 'form']],
            'target': 'new',
        }
