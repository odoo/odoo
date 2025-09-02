import json
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import file_open, file_path


ODOO_IDENTIFIER_VALUES = json.loads(
    file_open(
        file_path('account/data/odoo_identifier_types.json'),
        mode='rb',
    ).read()
)['values']  # It is preferable to traceback here than to load with no identifier types
ODOO_IDENTIFIERS = {
    identifier_vals['schemeid']: identifier_vals
    for identifier_vals in ODOO_IDENTIFIER_VALUES
    if identifier_vals.get('state') == 'active'
}
IDENTIFIER_CODES_SELECTION = [
    (identifier_vals['schemeid'], identifier_vals.get('odoo-name') or identifier_vals['scheme-name'])
    for identifier_vals
    in ODOO_IDENTIFIER_VALUES
    if identifier_vals.get('state') == 'active'
]


class ResPartnerIdentification(models.Model):
    _name = 'res.partner.identification'
    _description = 'Partner Identification'
    _order = 'sequence, id'

    partner_id = fields.Many2one(comodel_name='res.partner', required=True, ondelete='cascade')
    sequence = fields.Integer(default=100)
    code = fields.Selection(
        selection=IDENTIFIER_CODES_SELECTION,
        required=True,
    )
    identifier = fields.Char(required=True)

    # Computed "quick access" fields
    label = fields.Char(compute='_compute_label')
    country_code = fields.Char(compute='_compute_country_code')
    iso_code = fields.Char(compute='_compute_iso_code')
    iso_identifier = fields.Char(compute='_compute_iso_identifier')  # in the form 'iso_code:identifier'
    is_vat = fields.Boolean(compute='_compute_is_vat')

    _unique_code_partner_id = models.Constraint('unique(partner_id, code)', "A code can only be used once per partner.")

    @api.constrains('identifier')
    def _check_identifier(self):
        for identification in self:
            identification._validate(allow_raising=True)

    @api.depends('identifier')
    def _compute_display_name(self):
        for identification in self:
            identification.display_name = identification.identifier

    @api.depends('code')
    def _compute_label(self):
        for identification in self:
            code_vals = self._get_code_vals(identification.code)
            identification.label = code_vals.get('odoo-name') or code_vals['scheme-name']

    @api.depends('code', 'identifier')
    def _compute_iso_identifier(self):
        for identification in self:
            if identification.code and identification.identifier:
                identification.iso_identifier = f'{identification.iso_code}:{identification.identifier}'
            else:
                identification.iso_identifier = ''

    @api.depends('code')
    def _compute_country_code(self):
        for identification in self:
            identification.country_code = self._get_code_vals(identification.code).get('country', None)

    @api.depends('code')
    def _compute_iso_code(self):
        for identification in self:
            identification.iso_code = self._get_code_vals(identification.code).get('iso6523', None)

    @api.depends('code')
    def _compute_is_vat(self):
        for identification in self:
            identification.is_vat = self._get_code_vals(identification.code).get('is_vat', False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sequence' not in vals:
                # get the sequence from the data file
                vals['sequence'] = ODOO_IDENTIFIERS[vals['code']].get('sequence', 100)
            # TODO sanitize
            # TODO validate + handle context silent_identification_validation
            # TODO pre-check uniqueness to fail silently ?
        return super().create(vals_list)

    def write(self, vals):
        # TODO sanitize
        # TODO validate + handle context silent_identification_validation
        # TODO pre-check uniqueness to fail silently ?
        return super().write(vals)

    @api.model
    def _get_code_vals(self, code):
        if not code:
            return {}
        return ODOO_IDENTIFIERS.get(code)

    def _get_parent_country(self, country_code):
        country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
        if 'DOM-TOM' in country.country_group_codes:
            return 'FR'
        return country_code

    @api.model
    def _get_codes_by_country(self, country_code, include_international=False):
        if not country_code:
            return {}
        country_code = self._get_parent_country(country_code)
        country_domain = [country_code] if not include_international else [country_code, 'international']
        identifiers_with_sequence = [
            {'code': code, 'sequence': code_vals.get('sequence', 100)}
            for code, code_vals in ODOO_IDENTIFIERS.items()
            if code_vals.get('country') in country_domain
        ]
        sorted_by_sequence = sorted(identifiers_with_sequence, key=lambda vals: vals.get('sequence', 100))
        return {
            odoo_identifier.get('code'): self.env['res.partner.identification']._get_code_vals(odoo_identifier.get('code'))
            for odoo_identifier in sorted_by_sequence
        }

    @api.model
    def _get_code_for_vat(self, country_code):
        if not country_code:
            return False
        vat_for_country = [
            code
            for code, code_vals in ODOO_IDENTIFIERS.items()
            if code_vals.get('schemeid') == f'{country_code}:VAT'
        ]
        return next(iter(vat_for_country), None)

    @api.model
    def _get_code_from_iso(self, iso_code):
        return ODOO_IDENTIFIERS.get(iso_code)['schemeid']

    def _validate(self, allow_raising=True):
        self.ensure_one()
        valid, message = self._apply_validation_rules(self.code, self.identifier)
        if not valid and allow_raising:
            raise UserError(message)
        return valid, message

    @api.model
    def _apply_validation_rules(self, code, identifier):
        # TODO
        code_vals = self._get_code_vals(code)
        examples = code_vals.get('examples')
        expected_format = f" The expected format is: {examples}." if examples else ""
        error_message = _("The identifier (%(code)s) is not valid.\n (%(expected_format)s", code=code, expected_format=expected_format)
        # apply regex -> if none & is_registrable_on_peppol: PEPPOL_ENDPOINT_INVALIDCHARS_RE.search(self.identifier) or not 1 <= len(self.identifier) <= 50
        # apply extra rules
        # regex, examples = _get_validation_for_identification(code)
        # if re.match(regex, identifier):
        #     if not _need_vat_check(regex['schemeid'], eas):
        #         return {'valid': True, 'examples': False}
        #     if _perform_vat_check(env, regex['schemeid'].split(':')[0], endpoint):
        #         return {'valid': True, 'examples': False}
        # return {'valid': False, 'examples': regex['examples']}
        return True, error_message
