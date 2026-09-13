from odoo import fields, models


class Test_UninstallModel(models.Model):
    _name = "test_uninstall.model"
    _description = "Testing Uninstall Model"

    name = fields.Char(string="Name")
    ref = fields.Many2one(
        comodel_name="res.users",
        string="User",
    )
    rel = fields.Many2many(
        comodel_name="res.users",
        string="Users",
    )

    _name_uniq = models.Constraint(
        "unique (name)",
        "Each name must be unique.",
    )


class ResUsers(models.Model):
    _inherit = "res.users"

    _test_uninstall_res_user_unique_constraint = models.Constraint(
        "unique (password)",
        "Test uninstall unique constraint",
    )
    _test_uninstall_res_user_check_constraint = models.Constraint(
        "check (true)",
        "Test uninstall check constraint",
    )
    _test_uninstall_res_user_exclude_constraint = models.Constraint(
        "exclude (password with =)",
        "Test uninstall exclude constraint",
    )
    _test_uninstall_res_user_exclude_constraint_looooooooooooong_name = (
        models.Constraint(
            "exclude (password with =)",
            "Test uninstall exclude constraint",
        )
    )
