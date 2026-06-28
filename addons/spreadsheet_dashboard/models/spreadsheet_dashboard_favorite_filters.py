from odoo import fields, models


class SpreadsheetDashboardFavoriteFilters(models.Model):
    _name = 'spreadsheet.dashboard.favorite.filters'
    _description = 'Dashboard Favorite Filter'
    _order = "id asc"

    name = fields.Char(string='Filter Name', required=True)
    user_ids = fields.Many2many(
        'res.users',
        string='Users',
        ondelete='cascade',
        help="The users the filter is shared with. If empty, the filter is shared with all users."
    )
    dashboard_id = fields.Many2one(
        'spreadsheet.dashboard',
        string="Dashboard",
        required=True,
        ondelete="cascade",
        index=True
    )
    is_default = fields.Boolean(string='Default Filter')
    global_filters = fields.Json()
    active = fields.Boolean(default=True)
