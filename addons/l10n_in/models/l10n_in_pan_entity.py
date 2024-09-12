from stdnum.in_ import pan
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class L10nInPanEntity(models.Model):
    _name = "l10n_in.pan.entity"
    _description = 'Indian PAN Entity'

    name = fields.Char(string="PAN Number")
    partner_ids = fields.One2many('res.partner', 'l10n_in_pan_entity_id')
    pan_holder_type = fields.Char(compute="_compute_pan_holder_type", readonly=True)
    l10n_in_tax_tcs_ids = fields.One2many('l10n_in.tax.tcs', 'l10n_in_pan_entity_id', string="TCS")
    l10n_in_tax_tds_ids = fields.One2many('l10n_in.tax.tds', 'l10n_in_pan_entity_id', string="TDS")

    _sql_constraints = [
        ('pan_uniq', "unique(name)", "A PAN Entity same PAN Number already exists.")
        ]

    @api.depends('name')
    def _compute_pan_holder_type(self):
        for record in self:
            if pan.is_valid(self.name):
                pan_info = pan.info(record.name)
                record.pan_holder_type = pan_info['holder_type']
            else:
                raise UserError("invalid PAN")


class L10nINTaxTcs(models.Model):
    _name = 'l10n_in.tax.tcs'
    _description = 'Tax TCS'

    l10n_in_pan_entity_id = fields.Many2one('l10n_in.pan.entity')
    tax_group_ids = fields.Many2many('account.tax.group', string="Section")
    l10n_in_selection = fields.Selection([
        ('no_deduction', 'No Deduction'),
        ('low_deduction', 'Low Deduction'),
    ], string="Selection")
    l10n_in_reason = fields.Selection([
        ('a', 'A'),
        ('b', 'B')
    ],
    string="Reason",
    help="(A):- In case of lower collection as per section 206C (9)\n"
         "(B):- Non collection as per section 206C (1A)\n"
    )
    l10n_in_certificate_number = fields.Char(string="Certificate Number issued u/s 206C")
    valid_from = fields.Date(string="Valid From")
    valid_upto = fields.Date(string="Valid Upto")

    @api.constrains('valid_from', 'valid_upto')
    def _check_reconcile(self):
        for record in self:
            if record.valid_upto <= record.valid_from:
                raise ValidationError(_('You cannot set start date greater than end date'))
            overlapping_lines = self.env['l10n_in.tax.tds'].search([
                ('id', '!=', record.id),
                ('tax_group_ids', 'in', record.tax_group_ids.ids),
                ('valid_from', '<=', record.valid_upto),
                ('valid_upto', '>=', record.valid_from),
            ])
            if overlapping_lines:
                raise ValidationError("The date range overlaps with an same existing section.")


class L10nINTaxTds(models.Model):
    _name = 'l10n_in.tax.tds'
    _description = 'Tax TDS'

    l10n_in_pan_entity_id = fields.Many2one('l10n_in.pan.entity')
    tax_group_ids = fields.Many2many('account.tax.group', string="Section")
    l10n_in_selection = fields.Selection([
        ('no_deduction', 'No Deduction'),
        ('low_deduction', 'Low Deduction'),
        ('high_deduction', 'High Deduction'),
        ('transporter', 'Transporter')
    ], string="Selection TDS")
    l10n_in_reason = fields.Selection([
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('t', 'T'),
        ('y', 'Y'),
        ('s', 'S'),
        ('z', 'Z')
    ],
    string="Reason",
    help="(A):- In case of lower deduction/no deduction on account of \n"
         "certificate under section 197\n"
         "(B):- In case of no deduction on account of declaration\n"
         "under section 197A. Allowed only for section 194, 194A,\n"
         "194EE, 193, 194DA, 192A, 1941(a), 1941(b) & 194D (no\n"
         "deduction/lower deduction). Also, in case of Lower/No\n"
         "deduction on account of business of operation of call\n"
         "centre. Allowe only for section 194J and for statements\n"
         "pertains to FY 2017-18 onwards.\n"
         "(C):- In case of deduction of tax at higher rate due to\n"
         "non-availability of PAN\n"
         "(T):- In case of Transporter transaction and valid PAN is\n"
         "provided [section 194C(6)]\n"
         "(Y):- Transaction where tax not been deducted as amount\n"
         "paid/credited to the vendor/party has not exceeded the\n"
         "threshold limit (as per the provisions of income tax act).\n"
         "Applicable for sections 193, 194, 194A, 194B, 194BB, 194C,\n"
         "194D, 194EE, 194G, 194H, 1941, 194J, 194LA.\n"
         "(S):- For software acquired under section 194J (Notification\n"
         "21/2012). Applicable from FY 2012-13 onwards.\n"
         "(Z):- In case of no deduction on account of payment under\n"
         "section 197A\n"
    )
    l10n_in_certificate_number = fields.Char(string="Certificate Number issued u/s 197")
    valid_from = fields.Date(string="Valid From")
    valid_upto = fields.Date(string="Valid Upto")

    @api.constrains('valid_from', 'valid_upto')
    def _check_reconcile(self):
        for record in self:
            if record.valid_upto <= record.valid_from:
                raise ValidationError(_('You cannot set start date greater than end date'))
            overlapping_lines = self.env['l10n_in.tax.tds'].search([
                ('id', '!=', record.id),
                ('tax_group_ids', 'in', record.tax_group_ids.ids),
                ('valid_from', '<=', record.valid_upto),
                ('valid_upto', '>=', record.valid_from),
            ])
            if overlapping_lines:
                raise ValidationError("The date range overlaps with an same existing section.")
