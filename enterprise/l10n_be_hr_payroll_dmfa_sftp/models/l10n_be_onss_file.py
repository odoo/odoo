# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import date

from odoo import api, fields, models

from odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.utils import xml_str_to_dict


FILE_TYPES = [
    ('FI', 'Declaration File (Sent)'),
    ('FO', 'Declaration File (Received)'),
    ('CO', 'Compressed File (Received)'),
    ('GO', 'Go File'),
    ('FS', 'Signature File'),
    ('TD', 'Cancel File'),
    ('other', 'Other'),
]

# https://www.socialsecurity.be/site_fr/general/helpcentre/batch/files/goal.htm
DECLARATION_TYPES = [
    ("ACRF", "Acknowledgment Receipt"),
    ("AOAT", "DRS declaration 'Work Accidents'"),
    ("BEWA", "Corrective Notices"),
    ("BEWL", "Checklist of Sent Corrective Notices (BEWA)"),
    ("CDHG", "Capelo Historical Data"),
    ("DDTN", "Original/Modified Work Declaration"),
    ("DEFI", "Temporary Unemployment Final Decision"),
    ("DIMN", "Dimona declaration"),
    ("DMDB", "DmfA Consultation Response"),
    ("DMNO", "DmfA Modification Notification"),
    ("DMFA", "DmfA declaration"),
    ("DMPI", "Dmfa Technical Key Identification"),
    ("DMRQ", "DmfA consultation (Request)"),
    ("DMWA", "DmfA Modification"),
    ("ECAN", "Ecaro Data Consultation Response"),
    ("ECOA", "Economic Unemployment Contribution Days Response"),
    ("ECOR", "Ecaro Technical Identification Keys"),
    ("ECRQ", "Ecaro Data Consultation Request"),
    ("FINO", "Financial Note"),
    ("FISI", "Financial Statement for Accredited Social Secretariats"),
    ("IDFL", "Identification Change"),
    ("LIRE", "Payment Allocation List (Social Secretariats)"),
    ("LOIC", "Career Break/Credit-Time/Leave Request"),
    ("NOTI", "Notification"),
    ("PFAN", "Personnel File Consultation Response"),
    ("PFRQ", "Personnel File Consultation"),
    ("PROA", "Proactive Action Information (Social Secretariats)"),
    ("PUBL", "Work Accident Declaration (Public Sector)"),
    ("REAN", "First Hire Deduction Data Response (DmfA)"),
    ("RECO", "First Hire Deduction Data Request (DmfA)"),
    ("SIGN", "Employer Directory Alert"),
    ("TWCT", "Temporary Unemployment Declaration"),
    ("VBLV", "Validation Book Declaration"),
    ("WECH", "DRS declaration 'Unemployment'"),
    ("ZIMA", "DRS declaration 'Allowances'"),
    ("other", "Other"),
]

ENVIRONMENTS = [
    ('R', 'Production'),
    ('T', 'Circuit Test'),
    ('S', 'Declaration Test'),
    ('other', 'other'),
]


class L10nBeOnssFile(models.Model):
    _name = 'l10n.be.onss.file'
    _description = 'ONSS File'
    _order = "create_date DESC"

    name = fields.Char("File Name", required=True)
    file = fields.Binary("File")
    file_type = fields.Selection(
        selection=FILE_TYPES,
        compute="_compute_file_description",
        store=True)
    declaration_type = fields.Selection(
        selection=DECLARATION_TYPES,
        compute="_compute_file_description",
        store=True)
    expeditor_number = fields.Char(
        compute="_compute_file_description",
        store=True)
    creation_date = fields.Date(
        compute="_compute_file_description",
        store=True)
    file_sequence = fields.Char(
        compute="_compute_file_description",
        store=True)
    environment = fields.Selection(
        selection=ENVIRONMENTS,
        compute="_compute_file_description",
        store=True)
    file_count = fields.Integer(
        compute="_compute_file_description",
        store=True)
    file_number = fields.Integer(
        compute="_compute_file_description",
        store=True)

    form_creation_date = fields.Char(
        compute='_compute_form_creation_date',
        store=True)
    form_creation_hour = fields.Char(
        compute='_compute_form_creation_date',
        store=True)

    file_content = fields.Text(compute='_compute_file_content', store=True)

    onss_declaration_id = fields.Many2one('l10n.be.onss.declaration')
    employee_id = fields.Many2one('hr.employee')
    company_id = fields.Many2one('res.company', related="onss_declaration_id.company_id", store=True)

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'ONSS file name should be unique!')
    ]

    @api.depends('name')
    def _compute_file_description(self):
        def nullify(self):
            self.file_type = 'other'
            self.declaration_type = 'other'
            self.expeditor_number = False
            self.creation_date = False
            self.file_sequence = False
            self.environment = False
            self.file_count = False
            self.file_number = False

        FILE_TYPE_KEYS = {e[0] for e in FILE_TYPES}
        DECLARATION_TYPE_KEYS = {e[0] for e in DECLARATION_TYPES}
        ENVIRONMENT_KEYS = {e[0] for e in ENVIRONMENTS}
        for file in self:
            if not file.name:
                nullify(file)
                continue
            try:
                # filename example: e.g. FO.ACRF.999999.20250410.99998.T
                # format:
                #  {FILE_TYPE}.{DECL_TYPE}.{EXP_NUM}.{DATE}.{FILE_SEQ}.{ENV}[[.FILE_COUNT].FILE_NUM]
                split_file = file.name.split('.')
                file.file_type = split_file[0] if split_file[0] in FILE_TYPE_KEYS else "other"
                file.declaration_type = split_file[1] if split_file[1] in DECLARATION_TYPE_KEYS else "other"
                file.expeditor_number = split_file[2]
                date_str = split_file[3]
                file.creation_date = date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))
                file.file_sequence = split_file[4]
                file.environment = split_file[5] if split_file[5] in ENVIRONMENT_KEYS else "other"
                if len(split_file) == 8:
                    try:
                        file.file_count = int(split_file[6])
                    except ValueError:
                        file.file_count = 1
                    try:
                        file.file_number = int(split_file[7])
                    except ValueError:
                        file.file_number = 1
                elif len(split_file) == 7:
                    file.file_count = 1
                    try:
                        file.file_number = int(split_file[6])
                    except ValueError:
                        file.file_number = 1
                else:
                    file.file_count = 1
                    file.file_number = 1
            except Exception:  # noqa: BLE001
                nullify(file)

    @api.depends('file')
    def _compute_file_content(self):
        for onss_file in self:
            file_content_b64 = onss_file.with_context(bin_size=False).file
            if not file_content_b64:
                onss_file.file_content = False
                continue
            try:
                onss_file.file_content = base64.b64decode(file_content_b64)
            except UnicodeDecodeError:
                onss_file.file_content = file_content_b64

    @api.depends('file', 'declaration_type')
    def _compute_form_creation_date(self):
        for onss_file in self:
            file_content_b64 = onss_file.with_context(bin_size=False).file
            if not file_content_b64:
                onss_file.form_creation_date = False
                onss_file.form_creation_hour = False
                continue
            try:
                data_dict = xml_str_to_dict(base64.b64decode(file_content_b64))
            except Exception:  # noqa: BLE001
                continue
            form = {}
            for key in ['DmfAOriginal', 'NOTIFICATION', 'ACRF']:
                if key in data_dict:
                    form = data_dict[key]['Form']
                    break
            onss_file.form_creation_date = form.get('FormCreationDate', False)
            onss_file.form_creation_hour = form.get('FormCreationHour', False)
