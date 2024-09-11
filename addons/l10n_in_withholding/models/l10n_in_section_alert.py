from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from stdnum.in_ import pan


class L10nInSectionAlert(models.Model):
    _name = "l10n_in.section.alert"
    _description = "indian section alert"

    name = fields.Char("Section Name")
    tax_source_type = fields.Selection([
            ('tds', 'TDS'),
            ('tcs', 'TCS'),
        ], string="Tax Source Type")
    consider_amount = fields.Selection([
            ('untaxed_amount', 'Untaxed Amount'),
            ('total_amount', 'Total Amount'),
        ], string="Consider", default='untaxed_amount', required=True)
    is_per_transaction_limit = fields.Boolean("Per Transaction")
    per_transaction_limit = fields.Float("Per Transaction limit")
    is_aggregate_limit = fields.Boolean("Aggregate")
    aggregate_limit = fields.Float("Aggregate limit")
    aggregate_period = fields.Selection([
            ('monthly', 'Monthly'),
            ('fiscal_yearly', 'Financial Yearly'),
        ], string="Aggregate Period", default='fiscal_yearly')
    entity_tax_lines = fields.One2many('l10n_in.section.alert.tax', 'section_id')

    _sql_constraints = [
        ('per_transaction_limit', 'CHECK(per_transaction_limit >= 0)', 'Per transaction limit must be positive'),
        ('aggregate_limit', 'CHECK(aggregate_limit >= 0)', 'Aggregate limit must be positive'),
    ]

    @api.depends('tax_source_type')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.tax_source_type.upper()} {record.name}"

    def _get_warning_message(self):
        warning = ", ".join(self.mapped('name'))
        section_type = next(iter(set(self.mapped('tax_source_type')))).upper()
        action = 'collect' if section_type == 'TCS' else 'deduct'
        return _("It's advisable to %(action)s %(section_type)s u/s %(warning)s on this transaction.",
            action=action,
            section_type=section_type,
            warning=warning
        )

    def _get_applicable_tax_for_section(self, pan_entity, date):
        """
        Retrieves the applicable tax for the given section, PAN entity, and date.
        This method determines the tax based on the following rules:
        1. If the PAN is invalid or not provided, the method returns the tax line where `entity_type` is set to 'no_pan' for the given section and date.
        2. Based on the section's tax type ('TCS' or 'TDS'), it checks for applicable tax lines in the corresponding
           `l10n_in_tax_tcs_ids` (for 'TCS') or `l10n_in_tax_tds_ids` (for 'TDS') that match the section and are valid on the given date.
        3. If no specific tax line is found in the PAN entity, the method derives the applicable tax based on the PAN holder's entity type. The entity type
           is determined from the 4th character of the PAN. The method then returns the tax line where `entity_type` matches the entity type and is valid for the given date.
        4. If no tax is found for the entity type, the method returns the tax line where `entity_type` is set to 'other' for the given section and date.
        """
        self.ensure_one()

        if not pan.is_valid(pan_entity.name):
            return self.entity_tax_lines.filtered(lambda line: line.valid_from <= date and line.valid_upto >= date and line.entity_type == 'no_pan').tax_id

        pan_entity_tax = (
            pan_entity.l10n_in_tax_tcs_ids if self.tax_source_type == 'tcs' else pan_entity.l10n_in_tax_tds_ids
        ).filtered(
            lambda tax: tax.valid_from <= date and tax.valid_upto >= date and tax.l10n_in_section_id == self.id
        ).tax_id
        if pan_entity_tax:
            return pan_entity_tax

        # Get the PAN entity type from the 4th character of the PAN
        pan_entity_type = pan_entity.name[3].capitalize()
        pan_entity_type_tax = self.entity_tax_lines.filtered(
            lambda line: line.valid_from <= date and line.valid_upto >= date and line.entity_type == pan_entity_type
        ).tax_id
        if pan_entity_type_tax:
            return pan_entity_type_tax

        return self.entity_tax_lines.filtered(lambda line: line.valid_from <= date and line.valid_upto >= date and line.entity_type == 'other').tax_id


class L10nInSectionAlertTax(models.Model):
    _name = 'l10n_in.section.alert.tax'
    _description = 'Indian section alert Tax'

    entity_type = fields.Selection([
        ('no_pan', 'No PAN'),
        ('c', 'Company'),
        ('p', 'Individual'),
        ('h', 'Hindu Undivided Family'),
        ('f', 'Firms'),
        ('t', 'Association of Persons for a Trust'),
        ('a', 'Association of Persons'),
        ('b', 'Body of Individuals'),
        ('g', 'Government'),
        ('l', 'Local Authority'),
        ('j', 'Artificial Judicial Person'),
        ('other', 'Any Other'),
    ], required=True)
    valid_from = fields.Date(string="Valid From", required=True)
    valid_upto = fields.Date(string="Valid Upto", required=True)
    tax_id = fields.Many2one('account.tax', required=True)
    section_id = fields.Many2one('l10n_in.section.alert')

    @api.constrains('valid_from', 'valid_upto')
    def _check_section_period(self):
        for record in self:
            if record.valid_upto <= record.valid_from:
                raise ValidationError(_('You cannot set start date greater than end date'))
            overlapping_lines = self.env['l10n_in.section.alert.tax'].search([
                "&", "&", "&",
                ('id', '!=', record.id),
                ('entity_type', '=', record.entity_type),
                ('section_id', '=', record.section_id.id),
                "|", "&", ("valid_from", ">=", record.valid_from), ("valid_from", "<=", record.valid_upto),
                "&", ("valid_upto", ">=", record.valid_from), ("valid_upto", "<=", record.valid_upto),
            ])
            if overlapping_lines:
                raise ValidationError("The date range overlaps with an same existing section.")
