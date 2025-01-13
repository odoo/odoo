# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError


class UomUom(models.Model):
    _name = 'uom.uom'
    _description = 'Product Unit of Measure'
    _parent_name = 'relative_uom_id'
    _parent_store = True
    _order = "relative_uom_id, name, id"

    def _unprotected_uom_xml_ids(self):
        return [
            "product_uom_hour",  # NOTE: this uom is protected when hr_timesheet is installed.
            "product_uom_dozen",
            "product_uom_pack_6",
        ]

    name = fields.Char('Unit Name', required=True, translate=True)
    relative_factor = fields.Float(
        'Contains', default=1.0, digits=0, required=True,  # force NUMERIC with unlimited precision
        help='How much bigger or smaller this unit is compared to the reference UoM for this unit')
    rounding = fields.Float('Rounding Precision', compute="_compute_rounding")
    active = fields.Boolean('Active', default=True, help="Uncheck the active field to disable a unit of measure without deleting it.")
    relative_uom_id = fields.Many2one('uom.uom', 'Reference Unit', ondelete='cascade')
    related_uom_ids = fields.One2many('uom.uom', 'relative_uom_id', 'Related UoMs')
    factor = fields.Float('Absolute Quantity', digits=0, compute='_compute_factor', recursive=True, store=True)
    parent_path = fields.Char(index=True)

    _factor_gt_zero = models.Constraint(
        'CHECK (relative_factor!=0)',
        'The conversion ratio for a unit of measure cannot be 0!',
    )

    @api.onchange('relative_factor')
    def _onchange_critical_fields(self):
        if self._filter_protected_uoms() and self.create_date < (fields.Datetime.now() - timedelta(days=1)):
            return {
                'warning': {
                    'title': _("Warning for %s", self.name),
                    'message': _(
                        "Some critical fields have been modified on %s.\n"
                        "Note that existing data WON'T be updated by this change.\n\n"
                        "As units of measure impact the whole system, this may cause critical issues.\n"
                        "Therefore, changing core units of measure in a running database is not recommended.",
                        self.name,
                    )
                }
            }

    @api.constrains('relative_factor', 'relative_uom_id')
    def _check_factor(self):
        for uom in self:
            if not uom.relative_uom_id and uom.relative_factor != 1.0:
                raise UserError(_("The conversion ratio for a unit of measure without a reference unit must be 1!"))

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
        amount = price * to_unit.factor
        if to_unit:
            amount = amount / self.factor
        return amount

    @api.depends('relative_factor', 'relative_uom_id', 'relative_uom_id.factor')
    def _compute_factor(self):
        for uom in self:
            if uom.relative_uom_id:
                uom.factor = uom.relative_factor * uom.relative_uom_id.factor
            else:
                uom.factor = uom.relative_factor

    def _compute_rounding(self):
        """ All Units of Measure share the same rounding precision defined in 'Product Unit'.
            Set in a compute to ensure compatibility with previous calls to `uom.rounding`.
        """
        decimal_precision = self.env['decimal.precision'].precision_get('Product Unit')
        self.rounding = 10 ** -decimal_precision

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

    def _has_common_reference(self, other_uom):
        """ Check if `self` and `other_uom` have a common reference unit """
        self.ensure_one()
        other_uom.ensure_one()
        self_path = self.parent_path.split('/')
        other_path = other_uom.parent_path.split('/')
        common_path = []
        for self_parent, other_parent in zip(self_path, other_path):
            if self_parent == other_parent:
                common_path.append(self_parent)
            else:
                break
        return bool(common_path)
