from odoo import fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    mobility_card = fields.Char(related="operator_employee_id.mobility_card")

    def action_view_employee(self):
        self.check_singleton()
        return {
            "name": self.env._("Related Employee"),
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "view_mode": "form",
            "res_id": self.operator_employee_id.id,
        }

    def _get_manager_user(self):
        # A resource names its user only when its person had a login when the
        # resource was made; the party is what carries the login afterwards.
        manager = self.manager_id.sudo()
        return manager.user_id or manager.partner_id.user_ids[:1]
