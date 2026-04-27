# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def import_website(self, **kwargs):
        if not self.is_website_generator_available():
            raise UserError(_("The website scraper service is currently unavailable."))

        vals = {
            'target_url': self._normalize_domain_url(kwargs['url']),
        }

        modules_to_install = self.env['ir.module.module']

        # website_generator_sale
        if kwargs.get('import_products'):
            module = self.env['ir.module.module'].search([('name', '=', 'website_generator_sale')])
            if module.state != 'installed':
                modules_to_install += module
            vals['import_products'] = True

        # install modules
        if modules_to_install:
            modules_to_install.button_immediate_install()

        request = self.env['website_generator.request'].create(vals)

        if request.status != 'waiting':
            raise UserError(request.status_message)

        self.configurator_skip()

        return True
