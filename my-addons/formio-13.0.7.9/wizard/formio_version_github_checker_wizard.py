# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

import requests
from odoo import api, fields, models, _


class VersionGitHubChecker(models.TransientModel):
    _name = 'formio.version.github.checker.wizard'
    _description = 'Formio Version GitHub Checker Wizard'

    installed_version_ids = fields.One2many('formio.version', compute='_compute_wizard_fields', string='Installed Versions')
    available_version_github_tag_ids = fields.One2many('formio.version.github.tag.available', 'version_checker_wizard_id')
    github_tag_ids = fields.One2many('formio.version.github.tag', compute='_compute_wizard_fields', string='GitHub Tags')

    def _compute_wizard_fields(self):
        self.installed_version_ids = [(6, False, self.env['formio.version'].search([]).ids)]
        self.github_tag_ids = [(6, False, self.env['formio.version.github.tag'].search([]).ids)]

    @api.model
    def check_new_versions(self):
        res = []
        headers = {}
        token = self.env['ir.config_parameter'].sudo().get_param('formio.github.personal.access.token')
        if token:
            headers = {"Authorization": token}
        response = requests.get('https://api.github.com/repos/formio/formio.js/tags', headers=headers)

        if response.status_code == 200:
            tags = response.json()
            existing = self.env['formio.version.github.tag'].search([]).mapped('name')

            for t in tags:
                if t['name'] not in existing:
                    tag_vals = {
                        'name': t['name'],
                    }
                    res.append(tag_vals)
        return res

    @api.model
    def create(self, vals):
        tags_vals_list = self.check_new_versions()
        if tags_vals_list:
            vals['available_version_github_tag_ids'] = [(False, False, tag_vals) for tag_vals in tags_vals_list]
        return super(VersionGitHubChecker, self).create(vals)
        
    def action_register_available_versions(self):
        self.env['formio.version.github.tag'].check_and_register_available_versions()
        action = {
            'name': _('Versions GitHub tags'),
            'type': 'ir.actions.act_window',
            "views": [[False, "tree"], [False, "form"]],
            'view_id': self.env.ref('formio.view_formio_version_github_tag_tree').id,
            'res_model': 'formio.version.github.tag',
        }
        return action


class VersionGitHubTagAvailable(models.TransientModel):
    _name = 'formio.version.github.tag.available'
    _description = 'Formio Version GitHub Tag Available'

    name = fields.Char(required=True)
    changelog_url = fields.Char(compute='_compute_fields', string='Changelog URL')
    version_checker_wizard_id = fields.Many2one('formio.version.github.checker.wizard')

    @api.depends('name')
    def _compute_fields(self):
        for r in self:
            if r.name:
                r.changelog_url = 'https://github.com/formio/formio.js/blob/%s/Changelog.md' % r.name
            else:
                r.changelog_url = False
