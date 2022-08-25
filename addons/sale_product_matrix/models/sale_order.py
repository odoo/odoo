# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # if set, the matrix of the products configurable by matrix will be shown
    # on the report of the order.
    report_grids = fields.Boolean(string="Print Variant Grids", default=True)

    """ Matrix loading and update: fields and methods :

    NOTE: The matrix functionality was done in python, server side, to avoid js
        restriction.  Indeed, the js framework only loads the x first lines displayed
        in the client, which means in case of big matrices and lots of so_lines,
        the js doesn't have access to the 41nth and following lines.

        To force the loading, a 'hack' of the js framework would have been needed...
    """

    grid_product_tmpl_id = fields.Many2one(
        'product.template', store=False)
    # Whether the grid field contains a new matrix to apply or not
    grid_update = fields.Boolean(default=False, store=False)
    grid = fields.Char(
        "Matrix local storage", store=False,
        help="Technical local storage of grid. "
        "\nIf grid_update, will be loaded on the SO."
        "\nIf not, represents the matrix to open.")

    @api.onchange('grid_product_tmpl_id')
    def _set_grid_up(self):
        """Save locally the matrix of the given product.template, to be used by the matrix configurator."""
        if self.grid_product_tmpl_id:
            self.grid_update = False
            self.grid = json.dumps(self._get_matrix(self.grid_product_tmpl_id))

    @api.onchange('grid')
    def _apply_grid(self):
        """Apply the given list of changed matrix cells to the current SO."""
        if self.grid and self.grid_update:
            grid = json.loads(self.grid)
            product_template = self.env['product.template'].browse(grid['product_template_id'])
            dirty_cells = grid['changes']
            Attrib = self.env['product.template.attribute.value']
            default_so_line_vals = {}
            new_lines = []
            for cell in dirty_cells:
                combination = Attrib.browse(cell['ptav_ids'])
                no_variant_attribute_values = combination - combination._without_no_variant_attributes()

                # create or find product variant from combination
                product = product_template._create_product_variant(combination)
                order_lines = self.order_line.filtered(
                    lambda line: line.product_id.id == product.id
                    and line.product_no_variant_attribute_value_ids.ids == no_variant_attribute_values.ids
                )

                # if product variant already exist in order lines
                old_qty = sum(order_lines.mapped('product_uom_qty'))
                qty = cell['qty']
                diff = qty - old_qty

                if not diff:
                    continue

                # TODO keep qty check? cannot be 0 because we only get cell changes ...
                if order_lines:
                    if qty == 0:
                        if self.state in ['draft', 'sent']:
                            # Remove lines if qty was set to 0 in matrix
                            # only if SO state = draft/sent
                            self.order_line -= order_lines
                        else:
                            order_lines.update({'product_uom_qty': 0.0})
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
                            raise ValidationError(_("You cannot change the quantity of a product present in multiple sale lines."))
                        else:
                            order_lines[0].product_uom_qty = qty
                            # If we want to support multiple lines edition:
                            # removal of other lines.
                            # For now, an error is raised instead
                            # if len(order_lines) > 1:
                            #     # Remove 1+ lines
                            #     self.order_line -= order_lines[1:]
                else:
                    if not default_so_line_vals:
                        OrderLine = self.env['sale.order.line']
                        default_so_line_vals = OrderLine.default_get(OrderLine._fields.keys())
                    last_sequence = self.order_line[-1:].sequence
                    if last_sequence:
                        default_so_line_vals['sequence'] = last_sequence
                    new_lines.append((0, 0, dict(
                        default_so_line_vals,
                        product_id=product.id,
                        product_uom_qty=qty,
                        product_no_variant_attribute_value_ids=no_variant_attribute_values.ids)
                    ))
            if new_lines:
                # Add new SO lines
                self.update(dict(order_line=new_lines))

    def _get_matrix(self, product_template):
        """Return the matrix of the given product, updated with current SOLines quantities.

        :param product.template product_template:
        :return: matrix to display
        :rtype dict:
        """
        def has_ptavs(line, sorted_attr_ids):
            # TODO instead of sorting on ids, use odoo-defined order for matrix ?
            ptav = line.product_template_attribute_value_ids.ids
            pnav = line.product_no_variant_attribute_value_ids.ids
            pav = pnav + ptav
            pav.sort()
            return pav == sorted_attr_ids
        matrix = product_template._get_template_matrix(
            company_id=self.company_id,
            currency_id=self.currency_id,
            display_extra_price=True)
        if self.order_line:
            lines = matrix['matrix']
            order_lines = self.order_line.filtered(lambda line: line.product_template_id == product_template)
            for line in lines:
                for cell in line:
                    if not cell.get('name', False):
                        line = order_lines.filtered(lambda line: has_ptavs(line, cell['ptav_ids']))
                        if line:
                            cell.update({
                                'qty': sum(line.mapped('product_uom_qty'))
                            })
        return matrix

    def get_report_matrixes(self):
        """Reporting method.

        :return: array of matrices to display in the report
        :rtype: list
        """
        matrixes = []
        if self.report_grids:
            grid_configured_templates = self.order_line.filtered('is_configurable_product').product_template_id.filtered(lambda ptmpl: ptmpl.product_add_mode == 'matrix')
            for template in grid_configured_templates:
                if len(self.order_line.filtered(lambda line: line.product_template_id == template)) > 1:
                    # TODO do we really want the whole matrix even if there isn't a lot of lines ??
                    matrixes.append(self._get_matrix(template))
        return matrixes
