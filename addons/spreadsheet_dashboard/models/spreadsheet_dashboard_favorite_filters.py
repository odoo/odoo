from odoo import api, fields, models


class SpreadsheetDashboardFavoriteFilters(models.Model):
    _name = 'spreadsheet.dashboard.favorite.filters'
    _description = 'Dashboard Favorite Filter'
    _order = "dashboard_id, name, id desc"

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

    @api.model
    def get_filters(self, dashboard):
        """Obtain the list of filters available for the user on the given dashboard"""
        # available filters: private filters (user_ids=uid) and public filters (user_ids=NULL),
        user_context = self.env['res.users'].context_get()
        return self.with_context(user_context).search_read([
            ('dashboard_id', '=', dashboard),
            ('user_ids', 'in', [self.env.uid, False]),
        ], [
            'name', 'is_default', 'global_filters', 'user_ids',
        ])
