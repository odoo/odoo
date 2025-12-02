import json

from odoo import Command, _, api, fields, models
from odoo.tools import file_open


class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _description = 'Spreadsheet Dashboard'
    _inherit = ["spreadsheet.mixin"]
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    dashboard_group_id = fields.Many2one('spreadsheet.dashboard.group', required=True, index=True)
    sequence = fields.Integer()
    sample_dashboard_file_path = fields.Char(export_string_translation=False)
    is_published = fields.Boolean(default=True)
    company_ids = fields.Many2many('res.company', string="Companies")
    group_ids = fields.Many2many('res.groups', default=lambda self: self.env.ref('base.group_user'))
    favorite_user_ids = fields.Many2many(
        'res.users',
        domain=lambda self: [('id', '=', self.env.uid)],
        string='Favorite Users',
        help='Users who have favorited this dashboard'
    )
    is_favorite = fields.Boolean(
        compute='_compute_is_favorite',
        string='Is Favorite',
        help='Indicates whether the dashboard is favorited by the current user'
    )
    main_data_model_ids = fields.Many2many('ir.model')

    @api.depends_context('uid')
    @api.depends('favorite_user_ids')
    def _compute_is_favorite(self):
        for dashboard in self:
            dashboard.is_favorite = self.env.uid in dashboard.favorite_user_ids.ids

    def action_toggle_favorite(self):
        self.ensure_one()
        current_user_id = self.env.uid
        if current_user_id in self.favorite_user_ids.ids:
            self.sudo().favorite_user_ids = [Command.unlink(current_user_id)]
        else:
            self.sudo().favorite_user_ids = [Command.link(current_user_id)]

    def _get_serialized_readonly_dashboard(self):
        snapshot = json.loads(self.spreadsheet_data)
        user_locale = self.env['res.lang']._get_user_spreadsheet_locale()
        snapshot.setdefault('settings', {})['locale'] = user_locale
        default_currency = self.env['res.currency'].get_company_currency_for_spreadsheet()
        return json.dumps({
            'snapshot': snapshot,
            'revisions': [],
            'default_currency': default_currency,
            'translation_namespace': self._get_dashboard_translation_namespace(),
        })

    def _get_sample_dashboard(self):
        try:
            with file_open(self.sample_dashboard_file_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return

    def _dashboard_is_empty(self):
        return any(self.env[model].search_count([], limit=1) == 0 for model in self.sudo().main_data_model_ids.mapped("model"))

    def _get_dashboard_translation_namespace(self):
        data = self.env['ir.model.data'].sudo().search([
            ('model', '=', self._name),
            ('res_id', 'in', self.ids),
        ], limit=1)
        return data.module

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for dashboard, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", dashboard.name)
        return vals_list
