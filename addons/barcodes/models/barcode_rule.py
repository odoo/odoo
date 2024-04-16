import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BarcodeRule(models.Model):
    _name = 'barcode.rule'
    _description = 'Barcode Rule'
    _order = 'sequence asc, id'

    name = fields.Char(string='Rule Name', required=True, help='An internal identification for this barcode nomenclature rule')
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcode Nomenclature', required=True)
    sequence = fields.Integer(string='Sequence', help='Used to order rules such that rules with a smaller sequence match first')
    encoding = fields.Selection(
        string='Encoding', required=True, default='any', selection=[
            ('any', 'Any'),
            ('ean8', 'EAN-8'),
            ('ean13', 'EAN-13'),
            ('gtin14', 'GTIN-14'),
            ('sscc', 'SSCC'),
            ('upca', 'UPC-A'),
        ], help='This rule will apply only if the barcode is encoded with the specified encoding')
    type = fields.Char(string='Type', compute='_compute_type')
    pattern = fields.Char(string='Barcode Pattern', help="The barcode matching pattern", compute='_compute_pattern')
    alias = fields.Char(string='Alias', default='', help='The matched pattern will alias to this barcode')
    rule_part_ids = fields.One2many('barcode.rule.part', 'rule_id')
    is_combined = fields.Boolean(related="barcode_nomenclature_id.is_combined")
    required_rule_ids = fields.Many2many(
        'barcode.rule', 'barcode_rule_required_rel', 'required_rule_ids', 'child_rule_ids',
        string="Required Rule",
        help="When set, this rule can be used only when at least one of the required "
             "rule is also present in the parsed barcode.")
    child_rule_ids = fields.Many2many(
        'barcode.rule', 'barcode_rule_required_rel', 'child_rule_ids', 'required_rule_ids',
        string="Depending rules")
    associated_uom_id = fields.Many2one(related='rule_part_ids.associated_uom_id')

    @api.depends('rule_part_ids', 'rule_part_ids.pattern', 'rule_part_ids.sequence')
    def _compute_pattern(self):
        for rule in self:
            if not rule.rule_part_ids:
                rule.pattern = ''
                continue
            patterns = rule.rule_part_ids.sorted('sequence').mapped('pattern')
            rule.pattern = ''.join(patterns)

    @api.depends('rule_part_ids', 'rule_part_ids.type', 'rule_part_ids.sequence')
    def _compute_type(self):
        # Since prefix and decimal position are always used alongside other
        # types, we don't count them to avoid useless noise.
        ignored_types = {'decimal_position', 'prefix'}
        dict_type_labels = dict(self.env['barcode.rule.part']._fields['type']._description_selection(self.env))
        self.type = ''
        for rule in self:
            rule_types = [part.type for part in rule.rule_part_ids if part.type not in ignored_types]
            if len(rule_types) == 1:
                rule.type = dict_type_labels[rule_types[0]]
            elif len(rule_types) > 1:
                rule_type_labels = [dict_type_labels[rule_type] for rule_type in rule_types]
                rule.type = _("Multiple (%(rule_types)s)", rule_types=', '.join(rule_type_labels))


class BarcodeRulePart(models.Model):
    _name = 'barcode.rule.part'
    _description = 'Barcode Rule - Catching Group'
    _order = 'sequence asc, id'

    sequence = fields.Integer(string='Order', help="Must follow the rule pattern groups order")
    type = fields.Selection(
        string='Type', required=True, selection=[
            ('alias', 'Alias'),
            ('prefix', 'Prefix'),  # TODO: Maybe useless, to remove ?
            ('product', 'Unit Product'),
            ('measure', 'Measure'),
            ('weight', 'Weighted Product'),  # TODO: to check with POS if 'measure' isn't already enough.
            ('decimal_position', 'Decimal Position'),
        ], default='product')
    rule_id = fields.Many2one('barcode.rule')
    encoding = fields.Selection(
        string='Encoding', required=True, default='any', selection=[
            ('any', 'Any'),
            ('ean8', 'EAN-8'),
            ('ean13', 'EAN-13'),
            ('gtin14', 'GTIN-14'),
            ('sscc', 'SSCC'),
            ('upca', 'UPC-A'),
        ], help="This barcode part catched by the rule's pattern have to use the set encoding, "
                "which usually include the use of a checksume digit")
    pattern = fields.Char(string='Group Pattern', required=True, default='')
    associated_uom_id = fields.Many2one('uom.uom')
    decimal_position = fields.Integer("Decimal Position")
    hide_decimal_position = fields.Boolean(compute='_compute_hide_decimal_position')

    @api.depends('rule_id.rule_part_ids', 'type')
    def _compute_hide_decimal_position(self):
        self.hide_decimal_position = True
        for rule_group in self:
            if rule_group.type == 'measure':
                # The decimal position field should not be visible if it's defined on another group.
                rule_groups = rule_group.rule_id.rule_part_ids
                rule_group.hide_decimal_position = 'decimal_position' in rule_groups.mapped('type')

    @api.depends('type')
    def _compute_name(self):
        for rule_group in self:
            rule_group.display_name = rule_group.type

    @api.constrains('pattern')
    def _check_pattern(self):
        for rule_group in self:
            try:
                # Rule group patterns use regex, checks the regex is valid.
                compiled_regex = re.compile(rule_group.pattern)
                # Check the rule group's pattern has only one catching groups.
                if compiled_regex.groups != 1:
                    raise ValidationError(_(
                        "The pattern \"%s\" is not valid, it should have one catching group.",
                        rule_group.pattern))
            except re.error as error:
                raise ValidationError(
                    _("The pattern \"%s\" is not a valid Regex: ", rule_group.pattern) + str(error))
            continue
