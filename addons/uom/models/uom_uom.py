# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError


class UomUom(models.Model):
    _description = 'Product Unit of Measure'
    _order = "factor DESC, id"

    def _unprotected_uom_xml_ids(self):
        return [
            "product_uom_hour", # NOTE: this uom is protected when hr_timesheet is installed.
            "product_uom_dozen",
        ]

    name = fields.Char('Unit of Measure', required=True, translate=True)
    factor = fields.Float(
        'Contains Qty', default=1.0, digits=0, required=True,  # force NUMERIC with unlimited precision
        help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category: 1 * (reference unit) = ratio * (this unit)')
    factor_inv = fields.Float(
        'Bigger Ratio', compute='_compute_factor_inv', digits=0,  # force NUMERIC with unlimited precision
        readonly=True, required=True,
        help='How many times this Unit of Measure is bigger than the reference Unit of Measure in this category: 1 * (this unit) = ratio * (reference unit)')
    rounding = fields.Float(
        'Rounding Precision', default=0.01, digits=0, required=True,
        help="The computed quantity will be a multiple of this value. "
             "Use 1.0 for a Unit of Measure that cannot be further split, such as a piece.")
    active = fields.Boolean('Active', default=True, help="Uncheck the active field to disable a unit of measure without deleting it.")

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!'),
        ('rounding_gt_zero', 'CHECK (rounding>0)', 'The rounding precision must be strictly positive.'),
    ]

    @api.depends('factor')
    def _compute_factor_inv(self):
        for uom in self:
            uom.factor_inv = uom.factor and (1.0 / uom.factor) or 0.0

    @api.onchange('factor', 'factor_inv', 'rounding')
    def _onchange_critical_fields(self):
        if self._filter_protected_uoms() and self.create_date < (fields.Datetime.now() - timedelta(days=1)):
            return {
                'warning': {
                    'title': _("Warning for %s", self.name),
                    'message': _(
                        "Some critical fields have been modified on %s.\n"
                        "Note that existing data WON'T be updated by this change.\n\n"
                        "As units of measure impact the whole system, this may cause critical issues.\n"
                        "E.g. modifying the rounding could disturb your inventory balance.\n\n"
                        "Therefore, changing core units of measure in a running database is not recommended.",
                        self.name,
                    )
                }
            }

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'factor_inv' in values:
                factor_inv = values.pop('factor_inv')
                values['factor'] = factor_inv and (1.0 / factor_inv) or 0.0
        res = super().create(vals_list)
        return res

    def write(self, values):
        if 'factor_inv' in values:
            factor_inv = values.pop('factor_inv')
            values['factor'] = factor_inv and (1.0 / factor_inv) or 0.0

        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        locked_uoms = self._filter_protected_uoms()
        if locked_uoms:
            raise UserError(_(
                "The following units of measure are used by the system and cannot be deleted: %s\nYou can archive them instead.",
                ", ".join(locked_uoms.mapped('name')),
            ))

    def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True):
        """ Convert the given quantity from the current UoM `self` into a given one
            :param qty: the quantity to convert
            :param to_unit: the destination UomUom record (uom.uom)
            :param raise_if_failure: only if the conversion is not possible
                - if true, raise an exception if the conversion is not possible (different UomUom category),
                - otherwise, return the initial quantity
        """
        if not self or not qty:
            return qty
        self.ensure_one()

        if self == to_unit:
            amount = qty
        else:
            amount = qty * self.factor
            if to_unit:
                amount = amount / to_unit.factor

        if to_unit and round:
            amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)

        return amount

    def _compute_price(self, price, to_unit):
        self.ensure_one()
        if not self or not price or not to_unit or self == to_unit:
            return price
        # if self.category_id.id != to_unit.category_id.id:
        #     return price
        amount = price * self.factor
        if to_unit:
            amount = amount / to_unit.factor
        return amount

    def _filter_protected_uoms(self):
        """Verifies self does not contain protected uoms."""
        linked_model_data = self.env['ir.model.data'].sudo().search([
            ('model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('module', '=', 'uom'),
            ('name', 'not in', self._unprotected_uom_xml_ids()),
        ])
        if not linked_model_data:
            return self.browse()
        else:
            return self.browse(set(linked_model_data.mapped('res_id')))
