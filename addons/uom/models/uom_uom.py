# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Literal

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import float_round

if TYPE_CHECKING:
    from odoo.orm.types import Self
    from odoo.tools.float_utils import RoundingMethod


class UomUom(models.Model):
    _name = 'uom.uom'
    _description = 'Product Unit of Measure'
    _parent_name = 'relative_uom_id'
    _parent_store = True
    _order = 'sequence, relative_uom_id, id'

    def _unprotected_uom_xml_ids(self):
        """ Return a list of UoM XML IDs that are not protected by default.
        Note: Some of these may be protected via overrides in other modules.
        """
        return [
            "product_uom_hour",
            "product_uom_dozen",
            "product_uom_pack_6",
        ]

    name = fields.Char('Unit Name', required=True, translate=True)
    sequence = fields.Integer(compute="_compute_sequence", store=True, readonly=False, precompute=True)
    relative_factor = fields.Float(
        'Contains', default=1.0, digits=0, required=True,  # force NUMERIC with unlimited precision
        help='How much bigger or smaller this unit is compared to the reference UoM for this unit')
    rounding = fields.Float('Rounding Precision', compute="_compute_rounding")
    active = fields.Boolean('Active', default=True, help="Uncheck the active field to disable a unit of measure without deleting it.")
    relative_uom_id = fields.Many2one('uom.uom', 'Reference Unit', ondelete='cascade', index='btree_not_null')
    related_uom_ids = fields.One2many('uom.uom', 'relative_uom_id', 'Related UoMs')
    factor = fields.Float('Absolute Quantity', digits=0, compute='_compute_factor', recursive=True, store=True)
    parent_path = fields.Char(index=True)

    _factor_gt_zero = models.Constraint(
        'CHECK (relative_factor!=0)',
        'The conversion ratio for a unit of measure cannot be 0!',
    )

    # === COMPUTE METHODS === #

    @api.depends('relative_factor')
    def _compute_sequence(self):
        for uom in self:
            if uom.id and uom.sequence:
                # Only set a default sequence before the record creation, or on module update if
                # there is no value.
                continue
            uom.sequence = min(int(uom.relative_factor * 100.0), 1000)

    def _compute_rounding(self):
        """ All Units of Measure share the same rounding precision defined in 'Product Unit'.
            Set in a compute to ensure compatibility with previous calls to `uom.rounding`.
        """
        decimal_precision = self.env['decimal.precision'].precision_get('Product Unit')
        self.rounding = 10 ** -decimal_precision

    @api.depends('relative_factor', 'relative_uom_id', 'relative_uom_id.factor')
    def _compute_factor(self):
        for uom in self:
            if uom.relative_uom_id:
                uom.factor = uom.relative_factor * uom.relative_uom_id.factor
            else:
                uom.factor = uom.relative_factor

    # === ONCHANGE METHODS === #

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

    # === CONSTRAINT METHODS === #

    @api.constrains('relative_factor', 'relative_uom_id')
    def _check_factor(self):
        for uom in self:
            if not uom.relative_uom_id and uom.relative_factor != 1.0:
                raise UserError(_("Reference unit of measure is missing."))

    # === CRUD METHODS === #

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        locked_uoms = self._filter_protected_uoms()
        if locked_uoms:
            raise UserError(_(
                "The following units of measure are used by the system and cannot be deleted: %s\nYou can archive them instead.",
                ", ".join(locked_uoms.mapped('name')),
            ))

    # === BUSINESS METHODS === #

    def round(self, value: float, rounding_method: RoundingMethod = 'HALF-UP') -> float:
        """Round the value using the 'Product Unit' precision"""
        self.ensure_one()
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        return tools.float_round(value, precision_digits=digits, rounding_method=rounding_method)

    def compare(self, value1: float, value2: float) -> Literal[-1, 0, 1]:
        """Compare two measures after rounding them with the 'Product Unit' precision

        :param value1: origin value to compare
        :param value2: value to compare to
        :return: -1, 0 or 1, if ``value1`` is lower than, equal to, or greater than ``value2``.
        """
        self.ensure_one()
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        return tools.float_compare(value1, value2, precision_digits=digits)

    def is_zero(self, value: float) -> bool:
        """Check if the value is zero after rounding with the 'Product Unit' precision"""
        self.ensure_one()
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        return tools.float_is_zero(value, precision_digits=digits)

    @api.depends('name', 'relative_factor', 'relative_uom_id')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        for uom in self:
            if uom.env.context.get('formatted_display_name') and uom.relative_uom_id:
                uom.display_name = f"{uom.name}\t--{uom.relative_factor} {uom.relative_uom_id.name}--"

    def _compute_quantity(
        self,
        qty: float,
        to_unit: Self,
        round: bool = True,
        rounding_method: RoundingMethod = 'UP',
        raise_if_failure: bool = True,
    ) -> float:
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

    def _check_qty(self, product_qty, uom_id, rounding_method="HALF-UP"):
        """Check if product_qty in given uom is a multiple of the packaging qty.
        If not, rounding the product_qty to closest multiple of the packaging qty
        according to the rounding_method "UP", "HALF-UP or "DOWN".
        """
        self.ensure_one()
        packaging_qty = self._compute_quantity(1, uom_id)
        # We do not use the modulo operator to check if qty is a mltiple of q. Indeed the quantity
        # per package might be a float, leading to incorrect results. For example:
        # 8 % 1.6 = 1.5999999999999996
        # 5.4 % 1.8 = 2.220446049250313e-16
        if product_qty and packaging_qty:
            product_qty = float_round(product_qty / packaging_qty, precision_rounding=1.0,
                                  rounding_method=rounding_method) * packaging_qty
        return product_qty

    def _compute_price(self, price: float, to_unit: Self) -> float:
        self.ensure_one()
        if not self or not price or not to_unit or self == to_unit:
            return price
        amount = price * to_unit.factor
        if to_unit:
            amount = amount / self.factor
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

    def _has_common_reference(self, other_uom: Self) -> bool:
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
