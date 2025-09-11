import base64

from stdnum.in_ import pan
from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class L10nInPanEntity(models.Model):
    _name = 'l10n_in.pan.entity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Indian PAN Entity'

    name = fields.Char(string="PAN", tracking=1, required=True)
    type = fields.Selection([
        ('a', 'Association of Persons'),
        ('b', 'Body of Individuals'),
        ('c', 'Company'),
        ('f', 'Firms'),
        ('g', 'Government'),
        ('h', 'Hindu Undivided Family'),
        ('j', 'Artificial Judicial Person'),
        ('l', 'Local Authority'),
        ('p', 'Individual'),
        ('t', 'Association of Persons for a Trust'),
        ('k', 'Krish (Trust Krish)'),
    ], compute='_compute_type', readonly=True, store=True)
    partner_ids = fields.One2many(
        comodel_name='res.partner',
        inverse_name='l10n_in_pan_entity_id',
        string="Partners",
        domain="[('l10n_in_pan_entity_id', '=', False), '|', ('vat', '=', False), ('vat', 'like', name)]"
    )
    tds_deduction = fields.Selection([
        ('normal', 'Normal'),
        ('lower', 'Lower'),
        ('higher', 'Higher'),
        ('no', 'No'),
    ], string="TDS Deduction", default='normal', tracking=2)
    tds_certificate = fields.Binary(string="TDS Certificate", copy=False)
    tds_certificate_filename = fields.Char(string="TDS Certificate Filename", copy=False)

    # MSME/Udyam Registration details
    msme_type = fields.Selection([
        ("micro", "Micro"),
        ("small", "Small"),
        ("medium", "Medium")
    ], string="MSME/Udyam Registration Type", copy=False)
    msme_number = fields.Char(string="MSME/Udyam Registration Number", copy=False)

    _name_uniq = models.Constraint(
        'unique (name)',
        'A PAN Entity with same PAN Number already exists.',
    )

    @api.constrains('name')
    def _check_pan_name(self):
        if 'import_file' in self.env.context:
            return
        for record in self:
            if record.name and not pan.is_valid(record.name):
                raise ValidationError(_("The entered PAN %s seems invalid. Please enter a valid PAN.", record.name))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.name = record.name.upper()
        return records

    def write(self, vals):
        if vals.get('name'):
            vals['name'] = vals['name'].upper()
        res = super().write(vals)
        if vals.get('tds_certificate'):
            for rec in self:
                rec.message_post(
                    body=_("TDS Certificate Added"),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                    attachments=[(rec.tds_certificate_filename, base64.b64decode(vals['tds_certificate']))]
                )
        return res

    @api.depends('name')
    def _compute_type(self):
        for record in self:
            if record.name:
                if pan.is_valid(record.name):
                    record.type = record.name[3].lower()
                else:
                    record.type = False
