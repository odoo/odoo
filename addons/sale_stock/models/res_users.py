from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["property_warehouse_id"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["property_warehouse_id"]

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    property_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Default Warehouse",
        company_dependent=True,
        check_company=True,
    )

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _get_default_warehouse_id(self):
        if self.property_warehouse_id:
            return self.property_warehouse_id
        return super()._get_default_warehouse_id()
