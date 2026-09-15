from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    type = fields.Selection(
        selection_add=[("subcontract", "Subcontracting")],
        ondelete={
            "subcontract": lambda recs: recs.write({"type": "normal", "active": False})
        },
    )
    subcontractor_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="mrp_bom_subcontractor",
        string="Subcontractors",
        check_company=True,
    )

    def _get_subcontract_bom_by_product(
        self,
        product,
        picking_type=None,
        company_id=False,
        bom_type="subcontract",
        subcontractor=False,
    ):
        domain = self._get_domain_bom(
            product, picking_type=picking_type, company_id=company_id, bom_type=bom_type
        )
        if subcontractor:
            domain &= Domain("subcontractor_ids", "parent_of", subcontractor.ids)
            _debug.logic(
                "subcontract_bom", product=product.id, subcontractor=subcontractor.id
            )
            return self.search(domain, order="sequence, product_id, id", limit=1)
        else:
            _debug.logic("subcontract_bom", product=product.id, by="no_subcontractor")
            return self.env["mrp.bom"]

    @api.constrains("operation_ids", "byproduct_ids", "type")
    def _check_subcontracting_no_operation(self):
        if self.filtered_domain(
            [
                ("type", "=", "subcontract"),
                "|",
                ("operation_ids", "!=", False),
                ("byproduct_ids", "!=", False),
            ]
        ):
            _debug.logic("bom_refused", reason="subcontract_with_operations", boms=self)
            raise ValidationError(
                _(
                    "You can not set a Bill of Material with operations or by-product line as subcontracting."
                )
            )
