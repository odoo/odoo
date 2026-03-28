# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_test_themes_websites_theme_preview(self):
        websites_themes = self.env['website'].get_test_themes_websites()
        return {
            website.id: f"/web/image/{website.theme_id.sudo().image_ids[0].id}"
            for website in websites_themes.filtered(lambda w: w.theme_id.sudo().image_ids)
        }

    def get_test_themes_websites(self):
        website_imd_ids = self.env['ir.model.data'].sudo().search([
            ('module', '=', 'test_themes'),
            ('model', '=', 'website'),
        ])
        return self.browse(website_imd_ids.mapped('res_id'))

    def unlink(self):
        websites_themes = self.get_test_themes_websites()
        if self in websites_themes:
            # Bypass foreign key constraint
            website_domain = [('website_id', '=', self.id)]
            self.env['ir.ui.view'].with_context(active_test=False, _force_unlink=True).search(website_domain).unlink()
            self.env['ir.attachment'].with_context(active_test=False).search(website_domain).unlink()
        return super().unlink()
