import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    report_grids = fields.Boolean(
        string="Print Variant Grids",
        default=True,
        help="If set, the matrix of configurable products will be shown on the report of this order.",
    )

    """ Matrix loading and update: fields and methods :

    NOTE: The matrix functionality was done in python, server side, to avoid js
        restriction.  Indeed, the js framework only loads the x first lines displayed
        in the client, which means in case of big matrices and lots of po_lines,
        the js doesn't have access to the 41st and following lines.

        To force the loading, a 'hack' of the js framework would have been needed...
    """

    grid_product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        store=False,
        help="Technical field for product_matrix functionalities.",
    )
    grid_update = fields.Boolean(
        default=False,
        store=False,
        help="Whether the grid field contains a new matrix to apply or not.",
    )
    grid = fields.Char(
        store=False,
        help="Technical storage of grid. \nIf grid_update, will be loaded on the PO. \nIf not, represents the matrix to open.",
    )

    @api.onchange("grid_product_tmpl_id")
    def _set_grid_up(self):
        if self.grid_product_tmpl_id:
            self.grid_update = False
            self.grid = json.dumps(self._get_matrix(self.grid_product_tmpl_id))

    def _is_date_commitment_removed_by(self, field_name):
        return (
            super()._is_date_commitment_removed_by(field_name) or field_name == "grid"
        )

    @api.onchange("grid")
    def _apply_grid(self):
        if self.grid and self.grid_update:
            grid = json.loads(self.grid)
            product_template = self.env["product.template"].browse(
                grid["product_template_id"]
            )
            product_ids = set()
            dirty_cells = grid["changes"]
            Attrib = self.env["product.template.attribute.value"]
            default_po_line_vals = {}
            new_lines = []
            for cell in dirty_cells:
                combination = Attrib.browse(cell["ptav_ids"])
                no_variant_attribute_values = (
                    combination - combination._without_no_variant_attributes()
                )

                product = product_template._create_product_variant(combination)
                order_lines = self.line_ids.filtered(
                    lambda line: (
                        (line._origin or line).product_id == product
                        and (
                            line._origin or line
                        ).product_no_variant_attribute_value_ids
                        == no_variant_attribute_values
                    )
                )

                old_qty = sum(order_lines.mapped("product_qty"))
                qty = cell["qty"]
                diff = qty - old_qty

                if not diff:
                    continue

                product_ids.add(product.id)

                if order_lines:
                    if qty == 0:
                        if self.state in ["draft", "sent"]:
                            self.line_ids -= order_lines
                        else:
                            order_lines.update({"product_qty": 0.0})
                    else:
                        """
                        When there are multiple lines for same product and its quantity was changed in the matrix,
                        An error is raised.

                        A 'good' strategy would be to:
                            * Sets the quantity of the first found line to the cell value
                            * Remove the other lines.

                        But this would remove all business logic linked to the other lines...
                        Therefore, it only raises an Error for now.
                        """
                        if len(order_lines) > 1:
                            raise ValidationError(
                                _(
                                    "You cannot change the quantity of a product present in multiple purchase lines."
                                )
                            )
                        order_lines[0].product_qty = qty
                else:
                    if not default_po_line_vals:
                        OrderLine = self.env["purchase.order.line"]
                        default_po_line_vals = OrderLine.default_get(
                            OrderLine._fields.keys()
                        )
                    last_sequence = self.line_ids[-1:].sequence
                    if last_sequence:
                        default_po_line_vals["sequence"] = last_sequence
                    new_lines.append(
                        (
                            0,
                            0,
                            dict(
                                default_po_line_vals,
                                product_id=product.id,
                                product_qty=qty,
                                product_no_variant_attribute_value_ids=no_variant_attribute_values.ids,
                            ),
                        )
                    )
            if product_ids and new_lines:
                # No per-line reset call follows: name, price_unit, tax_ids and
                # date_commitment are computed from product_id, so the lines this
                # onchange adds get them from their own computes.
                self.update({"line_ids": new_lines})

    def _get_matrix(self, product_template):
        def has_ptavs(line, sorted_attr_ids):
            ptav = line.product_template_attribute_value_ids.ids
            pnav = line.product_no_variant_attribute_value_ids.ids
            pav = pnav + ptav
            pav.sort()
            return pav == sorted_attr_ids

        matrix = product_template._get_template_matrix(
            company_id=self.company_id, currency_id=self.currency_id
        )
        if self.line_ids:
            lines = matrix["matrix"]
            order_lines = self.line_ids.filtered(
                lambda line: line.product_template_id == product_template
            )
            for line in lines:
                for cell in line:
                    if not cell.get("name", False):
                        line = order_lines.filtered(
                            lambda line: has_ptavs(line, cell["ptav_ids"])
                        )
                        if line:
                            cell.update({"qty": sum(line.mapped("product_qty"))})
        return matrix

    def get_report_matrixes(self):
        matrixes = []
        if self.report_grids:
            grid_configured_templates = self.line_ids.filtered(
                "is_configurable_product"
            ).product_template_id
            for template in grid_configured_templates:
                if (
                    len(
                        self.line_ids.filtered(
                            lambda line: line.product_template_id == template
                        )
                    )
                    > 1
                ):
                    matrix = self._get_matrix(template)
                    matrix["matrix"] = [
                        row
                        for row in matrix["matrix"]
                        if any(column["qty"] != 0 for column in row[1:])
                    ]
                    matrixes.append(matrix)
        return matrixes


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    product_template_id = fields.Many2one(
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        string="Product Template",
        domain=[("purchase_ok", "=", True)],
    )
    is_configurable_product = fields.Boolean(
        related="product_template_id.has_configurable_attributes",
        string="Is the product configurable?",
    )
    product_template_attribute_value_ids = fields.Many2many(
        related="product_id.product_template_attribute_value_ids",
        readonly=True,
    )
