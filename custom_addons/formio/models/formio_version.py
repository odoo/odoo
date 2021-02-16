# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models, _


class Version(models.Model):
    _name = 'formio.version'
    _description = 'Formio Version'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name DESC'

    name = fields.Char(
        "Name", required=True, tracking=True,
        help="""Form.io release/version.""")
    description = fields.Text("Description")
    translations = fields.Many2many('formio.translation', string='Translations')
    assets = fields.One2many('formio.version.asset', 'version_id', string='Assets')
    css_assets = fields.One2many(
        'formio.version.asset', 'version_id', domain=[('type', '=', 'css')],
        string='CSS Assets')
    js_assets = fields.One2many(
        'formio.version.asset', 'version_id', domain=[('type', '=', 'js')],
        string='Javascript Assets')

    def unlink(self):
        domain = [('formio_version_id', '=', self.ids)]
        self.env['formio.version.github.tag'].search(domain).write({'state': 'available'})
        return super(Version, self).unlink()
