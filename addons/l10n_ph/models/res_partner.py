# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

KNOWN_PREFIXES = {"de", "dela", "delos", "del", "san", "santa", "sto", "santo", "sta", "mac", "mc", "la", "los", "vda", "vda."}
KNOWN_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}
KNOWN_TITLES = {"atty", "atty.", "dr", "dr.", "engr", "engr.", "mr", "mr.", "ms", "ms.", "mrs", "mrs.", "prof", "prof."}


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ph_branch_code = fields.Char(
        string="Branch Code",
        compute='_compute_branch_code',
        store=True,
    )
    l10n_ph_entity_type = fields.Selection([
            ('individual', 'Individual'),
            ('corporation', 'Corporation'),
        ],
        string='Type of Entity',
        help='Philippines: Defines the type of entity.',
    )
    l10n_ph_first_name = fields.Char(
        string="First Name",
        compute='_l10n_ph_compute_split_name',
        help="First name and suffix used for BIR Alphalist and tax reporting.",
    )
    l10n_ph_middle_name = fields.Char(
        string="Middle Name",
        compute='_l10n_ph_compute_split_name',
        help="Middle name used for BIR Alphalist and tax reporting.",
    )
    l10n_ph_last_name = fields.Char(
        string="Last Name",
        compute='_l10n_ph_compute_split_name',
        help="Last name used for BIR Alphalist and tax reporting.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_ph_branch_code']

    @api.depends('name', 'l10n_ph_entity_type', 'fiscal_country_codes')
    def _l10n_ph_compute_split_name(self):
        for partner in self:
            if 'PH' not in partner.fiscal_country_codes or partner.l10n_ph_entity_type == 'corporation' or not partner.name:
                partner.write({
                    'l10n_ph_first_name': False,
                    'l10n_ph_middle_name': False,
                    'l10n_ph_last_name': False,
                })
                continue

            first_name, middle_name, last_name, suffix = self._l10n_ph_split_name(partner.name)
            if suffix:  # For names with a suffix, we append it to the first name excluding the dot.
                first_name += f" {suffix.replace('.', '')}"
            partner.l10n_ph_first_name = first_name
            partner.l10n_ph_middle_name = middle_name
            partner.l10n_ph_last_name = last_name

    @api.model
    def _l10n_ph_split_name(self, full_name):
        """
        Splits a full name into first, middle, and last names for Philippine individuals.

        In the Philippines, names usually follow this structure:
            - First Name(s): One to three+ given names.
            - Middle Name: The mother's maiden surname.
            - Last Name: The father's surname.

        Philippine surnames often have multiple words starting with Spanish prefixes
        (like 'dela Cruz', 'de los Reyes', or 'San Jose'). If we just split the name
        by spaces, it will be wrong in too many case.

        This algorithm splits the name by spaces and reads it backwards (right to left:
        Last -> Middle -> First). It looks at the word right before the current one to
        see if it's in our list of known prefixes (NAME_PREFIXES). If it is, it keeps
        them together so multi-word surnames don't get accidentally cut in half.

        Examples:
            - "Jose Rizal" -> First: "Jose", Middle: "", Last: "Rizal"
            - "Juan Miguel dela Cruz Jr." -> First: "Juan", Middle: "Miguel", Last: "dela Cruz"
            - "Maria Anna de los Reyes Santos" -> First: "Maria Anna", Middle: "de los Reyes", Last: "Santos"

        Known edge cases: The split won't correctly handle first/middle/last names with multiple words that are not prefixes
        and that are not hyphenated. It also won't handle well names without middle name.

        The suffix is returned separately as its handling may differ between usages of this split.

        :returns a tuple containing in order: (first name, middle name, last name, suffix)
        """
        first_name_parts, middle_name_parts, last_name_parts = [], [], []
        parts_groups = iter([last_name_parts, middle_name_parts, first_name_parts])
        current_group = next(parts_groups)

        name_parts = list(filter(None, full_name.replace(',', ' ').strip().split(" ")))
        # Check for a suffix and remove it; we do not need it as part of the split name.
        # In practice these shouldn't be added, but a user in ecommerce/... could do so as these can be legally part
        # of the name
        suffix = ""
        if name_parts and name_parts[-1].lower() in KNOWN_SUFFIXES:
            suffix = name_parts.pop()
        # Since we already handle suffixes and do quite a lot of parsing, we can also check if there is a title
        # at the start of the name, to avoid mistakes we could easily handle.
        if name_parts and name_parts[0].lower() in KNOWN_TITLES:
            name_parts.pop(0)

        # Loop backward through the parts, and split when the next value is no longer part of the known prefixes.
        for i, part in reversed(list(enumerate(name_parts))):
            current_group.append(part)
            if i > 0 and name_parts[i - 1].lower() not in KNOWN_PREFIXES:
                current_group = next(parts_groups, current_group)

        # If we have a middle name but no first name, we will swap these as it likely more correct.
        if not first_name_parts and middle_name_parts:
            first_name_parts = middle_name_parts
            middle_name_parts = []

        # As we looped backward earlier, we need to reverse here again to put the parts back in their right order.
        return (
            " ".join(reversed(first_name_parts)),
            " ".join(reversed(middle_name_parts)),
            " ".join(reversed(last_name_parts)),
            suffix,
        )

    @api.depends('vat', 'country_id')
    def _compute_branch_code(self):
        for partner in self:
            branch_code = False
            if partner.country_id.code == 'PH' and partner.vat:
                match = partner._check_vat_ph_re.match(partner.vat)
                branch_code = (match and match.group(1) and match.group(1)[1:]) or branch_code
            partner.l10n_ph_branch_code = branch_code

    @api.depends('vat', 'commercial_partner_id', 'country_code', 'l10n_ph_entity_type')
    def _compute_is_company(self):
        ph_partners = self.filtered(lambda partner: partner.country_code == 'PH' and partner.l10n_ph_entity_type)
        for partner in ph_partners:
            partner.is_company = partner.l10n_ph_entity_type == 'corporation'
        super(ResPartner, self - ph_partners)._compute_is_company()
