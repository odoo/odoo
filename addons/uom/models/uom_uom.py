# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError


class UoMCategory(models.Model):
    _name = 'uom.category'
    _description = 'Product UoM Categories'

    name = fields.Char('Unit of Measure Category', required=True, translate=True)

    uom_ids = fields.One2many('uom.uom', 'category_id')
    reference_uom_id = fields.Many2one('uom.uom', "Reference UoM", store=False) # Dummy field to keep track of reference uom change

    @api.onchange('uom_ids')
    def _onchange_uom_ids(self):
        if len(self.uom_ids) == 1:
            self.uom_ids[0].uom_type = 'reference'
            self.uom_ids[0].factor = 1
        else:
            reference_count = sum(uom.uom_type == 'reference' for uom in self.uom_ids)
            if reference_count == 0 and self._origin.id:
                raise UserError(_('UoM category %s must have at least one reference unit of measure.', self.name))
            if self.reference_uom_id:
                new_reference = self.uom_ids.filtered(lambda o: o.uom_type == 'reference' and o._origin.id != self.reference_uom_id.id)
            else:
                new_reference = self.uom_ids.filtered(lambda o: o.uom_type == 'reference' and o._origin.uom_type != 'reference')
            if new_reference:
                other_uoms = self.uom_ids.filtered(lambda u: u._origin.id) - new_reference
                for uom in other_uoms:
                    uom.factor = uom._origin.factor / (new_reference._origin.factor or 1)
                    if uom.factor > 1:
                        uom.uom_type = 'smaller'
                    else:
                        uom.uom_type = 'bigger'
                self.reference_uom_id = new_reference._origin.id


class UoM(models.Model):
    _name = 'uom.uom'
    _description = 'Product Unit of Measure'
    _order = "factor DESC, id"

    def _unprotected_uom_xml_ids(self):
        return [
            "product_uom_hour", # NOTE: this uom is protected when hr_timesheet is installed.
            "product_uom_dozen",
        ]

    name = fields.Char('Unit of Measure', required=True, translate=True)
    category_id = fields.Many2one(
        'uom.category', 'Category', required=True, ondelete='restrict',
        help="Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios.")
    factor = fields.Float(
        'Ratio', default=1.0, digits=0, required=True,  # force NUMERIC with unlimited precision
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
    uom_type = fields.Selection([
        ('bigger', 'Bigger than the reference Unit of Measure'),
        ('reference', 'Reference Unit of Measure for this category'),
        ('smaller', 'Smaller than the reference Unit of Measure')], 'Type',
        default='reference', required=True)
    ratio = fields.Float('Combined Ratio', compute='_compute_ratio', inverse='_set_ratio', store=False)
    color = fields.Integer('Color', compute='_compute_color')

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!'),
        ('rounding_gt_zero', 'CHECK (rounding>0)', 'The rounding precision must be strictly positive.'),
        ('factor_reference_is_one', "CHECK((uom_type = 'reference' AND factor = 1.0) OR (uom_type != 'reference'))", "The reference unit must have a conversion factor equal to 1.")
    ]

    def _check_category_reference_uniqueness(self):
        categ_res = self.read_group(
            [("category_id", "in", self.category_id.ids)],
            ["category_id", "uom_type"],
            ["category_id", "uom_type"],
            lazy=False,
        )
        uom_by_category = defaultdict(int)
        ref_by_category = {}
        for res in categ_res:
            uom_by_category[res["category_id"][0]] += res["__count"]
            if res["uom_type"] == "reference":
                ref_by_category[res["category_id"][0]] = res["__count"]

        for category in self.category_id:
            reference_count = ref_by_category.get(category.id, 0)
            if reference_count > 1:
                raise ValidationError(_("UoM category %s should only have one reference unit of measure.", category.name))
            elif reference_count == 0 and uom_by_category.get(category.id, 0) > 0:
                raise ValidationError(_("UoM category %s should have a reference unit of measure.", category.name))

    @api.depends('factor')
    def _compute_factor_inv(self):
        for uom in self:
            uom.factor_inv = uom.factor and (1.0 / uom.factor) or 0.0

    @api.depends('uom_type', 'factor')
    def _compute_ratio(self):
        for uom in self:
            if uom.uom_type == 'reference':
                uom.ratio = 1
            elif uom.uom_type == 'bigger':
                uom.ratio = uom.factor_inv
            else:
                uom.ratio = uom.factor

    def _set_ratio(self):
        if self.ratio == 0:
            raise ValidationError(_("The value of ratio could not be Zero"))
        if self.uom_type == 'reference':
            self.factor = 1
        elif self.uom_type == 'bigger':
            self.factor = 1 / self.ratio
        else:
            self.factor = self.ratio

    @api.depends('uom_type')
    def _compute_color(self):
        for uom in self:
            if uom.uom_type == 'reference':
                uom.color = 7
            else:
                uom.color = 0

    @api.onchange('uom_type')
    def _onchange_uom_type(self):
        if self.uom_type == 'reference':
            self.factor = 1

    @api.onchange('factor', 'factor_inv', 'uom_type', 'rounding', 'category_id')
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
        res = super(UoM, self).create(vals_list)
        res._check_category_reference_uniqueness()
        return res

    def write(self, values):
        if 'factor_inv' in values:
            factor_inv = values.pop('factor_inv')
            values['factor'] = factor_inv and (1.0 / factor_inv) or 0.0

        res = super(UoM, self).write(values)
        if ('uom_type' not in values or values['uom_type'] != 'reference') and\
                not self.env.context.get('allow_to_change_reference'):
            self._check_category_reference_uniqueness()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        locked_uoms = self._filter_protected_uoms()
        if locked_uoms:
            raise UserError(_(
                "The following units of measure are used by the system and cannot be deleted: %s\nYou can archive them instead.",
                ", ".join(locked_uoms.mapped('name')),
            ))

    @api.model
    def name_create(self, name):
        """ The UoM category and factor are required, so we'll have to add temporary values
        for imported UoMs """
        values = {
            self._rec_name: name,
            'factor': 1
        }
        # look for the category based on the english name, i.e. no context on purpose!
        # TODO: should find a way to have it translated but not created until actually used
        if not self._context.get('default_category_id'):
            EnglishUoMCateg = self.env['uom.category'].with_context({})
            misc_category = EnglishUoMCateg.search([('name', '=', 'Unsorted/Imported Units')])
            if misc_category:
                values['category_id'] = misc_category.id
            else:
                values['category_id'] = EnglishUoMCateg.name_create('Unsorted/Imported Units')[0]
        new_uom = self.create(values)
        return new_uom.id, new_uom.display_name

    def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True):
        """ Convert the given quantity from the current UoM `self` into a given one
            :param qty: the quantity to convert
            :param to_unit: the destination UoM record (uom.uom)
            :param raise_if_failure: only if the conversion is not possible
                - if true, raise an exception if the conversion is not possible (different UoM category),
                - otherwise, return the initial quantity
        """
        if not self or not qty:
            return qty
        self.ensure_one()

        if self != to_unit and self.category_id.id != to_unit.category_id.id:
            if raise_if_failure:
                raise UserError(_(
                    'The unit of measure %s defined on the order line doesn\'t belong to the same category as the unit of measure %s defined on the product. Please correct the unit of measure defined on the order line or on the product, they should belong to the same category.',
                    self.name, to_unit.name))
            else:
                return qty

        if self == to_unit:
            amount = qty
        else:
            amount = qty / self.factor
            if to_unit:
                amount = amount * to_unit.factor

        if to_unit and round:
            amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)

        return amount

    def _compute_price(self, price, to_unit):
        self.ensure_one()
        if not self or not price or not to_unit or self == to_unit:
            return price
        if self.category_id.id != to_unit.category_id.id:
            return price
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
