# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields, api


class DashboardAccess(models.TransientModel):
    _name = "dashboard.access"
    _description = "Dashboard Access"

    @api.model
    def default_get(self, fields):
        """
        Set default value for the dashboard access
        """
        res = super(DashboardAccess, self).default_get(fields)
        context = dict(self.env.context)
        if context.get("active_model") == "dashboard.dashboard" and context.get(
            "active_id"
        ):
            dashboard_id = self.env["dashboard.dashboard"].browse(context["active_id"])
            res.update(
                {
                    "user_ids": [(6, 0, [])]
                    if dashboard_id.access_by == "access_group"
                    else [(6, 0, dashboard_id.user_ids.ids)],
                    "dashboard_id": context["active_id"],
                    # "chart_ids": [(6, 0, dashboard_id.chart_ids.ids)],
                    "access_by": dashboard_id.access_by or "access_group",
                }
            )
        return res

    # selected_user = fields.Boolean(
    #     string="Update Selected Users",
    #     help="Activate boolean to select specific users.",
    # )
    access_by = fields.Selection(
        [("access_group", "Access Groups"), ("user", "Users")],
        string="Access By",
        help="Provide dashboard to individual user's or user group's",
    )
    is_remove = fields.Boolean(string="Remove Access?")
    group_ids = fields.Many2many(
        "res.groups",
        "dashboard_user_group_rel",
        "dashboard_id",
        "group_id",
        string="Access Groups",
        help="Select user access group for accessing dashboard.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "dashboard_wiz_user_rel",
        "dashboard_id",
        "user_id",
        string="Users",
        help="Select user's for accessing dashboard.",
    )
    # update_user_ids = fields.Many2many(
    #     "res.users",
    #     "dashboard_wiz_update_user_rel",
    #     "dashboard_id",
    #     "user_id",
    #     string="Update Users",
    #     help="Select specific users to access the dashboard.",
    # )
    # chart_ids = fields.Many2many(
    #     "dashboard.chart",
    #     "dashboard_id",
    #     string="Charts",
    #     help="Select charts to be accessed by user's",
    # )
    dashboard_id = fields.Many2one(
        "dashboard.dashboard",
        string="Dashboard",
        domain=[("is_save_template", "=", False)],
    )

    @api.onchange("is_remove")
    def onchange_is_remove(self):
        if self.is_remove:
            self.access_by = False

    @api.onchange("access_by")
    def onchange_access_by(self):
        """
        to set user groups based on access
        """
        # self.user_ids = [
        #     (3, user)
        #     for user in list(
        #         filter(lambda uid: uid != self.env.user.id, self.user_ids.ids)
        #     )
        # ]
        self.user_ids = [(6, 0, self.dashboard_id.user_ids.ids)]
        self.group_ids = [(6, 0, self.dashboard_id.group_ids.ids)]

    @api.onchange("group_ids")
    def onchange_group_ids(self):
        """
        Set user base on groups
        """
        user_id = self.env.user
        # user_ids = list(filter(lambda uid: uid != user_id.id, self.user_ids.ids))
        # self.user_ids = [(3, user) for user in user_ids]
        self.user_ids = [(6, 0, self.dashboard_id.user_ids.ids)]
        if self.group_ids and self.access_by == "access_group":
            user_ids = list(
                filter(
                    lambda uid: uid != user_id.id, self.group_ids.mapped("users").ids
                )
            )
            self.user_ids = [(6, 0, user_ids)]

    # @api.onchange("selected_user", "user_ids")
    # def onchange_selected_user(self):
    #     """
    #     Set updated user base on access
    #     """
    #     self.update_user_ids = [(3, user.id) for user in self.update_user_ids]
    #     if self.selected_user:
    #         self.update_user_ids = [(6, 0, self.user_ids.ids)]

    def action_confirm(self):
        """
        Set users and groups base on user access
        """
        if self.dashboard_id:
            if self.is_remove:
                self.dashboard_id.access_by = False
                self.dashboard_id.group_ids = [(6, 0, [])]
                self.dashboard_id.user_ids = [(6, 0, [])]
                self.dashboard_id.created_menu_id.user_ids = [(6, 0, [])]
            else:
                self.dashboard_id.access_by = self.access_by
                self.dashboard_id.group_ids = [(6, 0, self.group_ids.ids)]
                self.dashboard_id.user_ids = [(6, 0, self.user_ids.ids)]
                self.dashboard_id.created_menu_id.user_ids = [(6, 0, self.user_ids.ids)]
