# Copyright Nova Code (http://www.novacode.nl)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    formio_default_version_id = fields.Many2one('formio.version', string='Form.io Version')
    formio_default_asset_css_ids = fields.Many2many('formio.default.asset.css', string='Form.io CSS assets')
    formio_default_builder_js_options_id = fields.Many2one('formio.builder.js.options', string='Form.io Builder JS options ID')
    formio_default_builder_js_options = fields.Text(related='formio_default_builder_js_options_id.value', string='Form.io Builder JS options')
    formio_github_personal_access_token = fields.Char(string='GitHub personal access token')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        Param = self.env['ir.config_parameter'].sudo()

        param_version = Param.get_param('formio.default_version')
        domain = [('name', '=', param_version)]
        version = self.env['formio.version'].search(domain, limit=1)
        if version:
            res.update(
                formio_default_version_id=version.id
            )

        default_builder_js_options_id = Param.get_param('formio.default_builder_js_options_id')
        builder_js_options = self.env['formio.builder.js.options'].browse(int(default_builder_js_options_id))

        if builder_js_options:
            res.update(
                formio_default_builder_js_options_id=builder_js_options.id
            )

        context = {'active_test': False}
        default_asset_css = self.env['formio.default.asset.css'].with_context(context).search([])
        if default_asset_css:
            res.update(
                formio_default_asset_css_ids=default_asset_css.ids
            )
        github_personal_access_token = Param.get_param('formio.github.personal.access.token')
        if github_personal_access_token:
            res.update(
                formio_github_personal_access_token=github_personal_access_token
            )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param(
            "formio.default_version",
            self.formio_default_version_id.name)
        Param.sudo().set_param(
            "formio.default_builder_js_options_id",
            self.formio_default_builder_js_options_id.id
        )
        Param.sudo().set_param(
            "formio.github.personal.access.token",
            self.formio_github_personal_access_token
        )

        context = {'active_test': False}
        defaults = self.env['formio.default.asset.css'].with_context(context).search([])

        # delete (deleted)
        deleted = defaults - self.formio_default_asset_css_ids
        deleted.filtered(lambda r: not r.nodelete).unlink()

        for r in self.formio_default_asset_css_ids:
            if r not in defaults:
                vals = {
                    'attachment_id': r.attachment_id.id,
                    'active': r.active,
                }
                self.env['formio.default.asset.css'].create(vals)

    def action_formio_version_github_importer(self):
        wizard = self.env['formio.version.github.checker.wizard']
        res = wizard.create({})
        action = {
            'name': _('Check and Register new Versions'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('formio.view_formio_version_github_checker_wizard').id,
            'res_model': 'formio.version.github.checker.wizard',
            'res_id': res.id
        }
        return action
