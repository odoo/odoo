# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import single_email_re


auto_mobn_re = re.compile(r"""^[+]\d{1,3}-\d{1,29}$""", re.VERBOSE)

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_hk_surname = fields.Char(
        "Surname",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_given_name = fields.Char(
        "Given Name",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_name_in_chinese = fields.Char(
        "Name in Chinese",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_passport_place_of_issue = fields.Char(
        "Place of Issue",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_spouse_identification_id = fields.Char(
        "Spouse Identification No",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_spouse_passport_id = fields.Char(
        "Spouse Passport No",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_spouse_passport_place_of_issue = fields.Char(
        "Spouse Place of Issue",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_mpf_manulife_account = fields.Char(
        "MPF Manulife Account",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_mpf_vc_option = fields.Selection(
        selection=[
            ("none", "Only Mandatory Contribution"),
            ("custom", "With Fixed %VC"),
            ("max", "Cap 5% VC")],
        string="Volunteer Contribution Option", groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_mpf_vc_percentage = fields.Float(
        string="Volunteer Contribution %",
        groups="hr.group_hr_user",
        tracking=True,
        copy=False)
    l10n_hk_rental_id = fields.Many2one(
        'l10n_hk.rental',
        string='Current Rental',
        groups="hr.group_hr_user",
        copy=False,
    )
    l10n_hk_rental_ids = fields.One2many(
        'l10n_hk.rental',
        'employee_id',
        string='Rentals',
        copy=False,
        groups="hr.group_hr_user")
    l10n_hk_rentals_count = fields.Integer(
        compute='_compute_l10n_hk_rentals_count',
        groups="hr.group_hr_user")
    l10n_hk_years_of_service = fields.Float(
        "Years of Service",
        compute="_compute_l10n_hk_years_of_service",
        digits=(16, 2),
        groups="hr.group_hr_user")

    # Autopay fields
    l10n_hk_autopay_account_type = fields.Selection(
        selection=[
            ('bban', 'BBAN'),
            ('svid', 'SVID'),
            ('emal', 'EMAL'),
            ('mobn', 'MOBN'),
            ('hkid', 'HKID')
        ],
        default='bban',
        string='Autopay Type',
        groups='hr.group_hr_user'
    )
    l10n_hk_autopay_svid = fields.Char(string='FPS Identifier', groups="hr.group_hr_user")
    l10n_hk_autopay_emal = fields.Char(string='Autopay Email Address', groups="hr.group_hr_user")
    l10n_hk_autopay_mobn = fields.Char(string='Autopay Mobile Number', groups="hr.group_hr_user")
    l10n_hk_autopay_ref = fields.Char(string='Autopay Reference', groups="hr.group_hr_user")

    @api.constrains('l10n_hk_mpf_vc_percentage')
    def _check_l10n_hk_mpf_vc_percentage(self):
        for employee in self:
            if employee.l10n_hk_mpf_vc_percentage > 0.05 or employee.l10n_hk_mpf_vc_percentage < 0:
                raise ValidationError(_('Enter VC Percentage between 0% and 5%.'))

    @api.constrains('l10n_hk_autopay_emal')
    def _check_l10n_hk_autopay_emal(self):
        for employee in self:
            if employee.l10n_hk_autopay_emal and not single_email_re.match(employee.l10n_hk_autopay_emal):
                raise ValidationError(_('Invalid Email! Please enter a valid email address.'))

    @api.constrains('l10n_hk_autopay_mobn')
    def _check_l10n_hk_auto_mobn(self):
        for employee in self:
            if employee.l10n_hk_autopay_mobn and not auto_mobn_re.match(employee.l10n_hk_autopay_mobn):
                raise ValidationError(_('Invalid Mobile! Please enter a valid mobile number.'))

    def _compute_l10n_hk_years_of_service(self):
        for employee in self:
            contracts = employee.contract_ids.filtered(lambda c: c.state not in ['draft', 'cancel']).sorted('date_start', reverse=True)
            if contracts:
                contract_end_date = contracts[0].date_end or fields.datetime.today().date()
                employee.l10n_hk_years_of_service = ((contract_end_date - employee.first_contract_date).days + 1) / 365

    def get_l10n_hk_autopay_bank_code(self) -> str:
        self.ensure_one()
        if self.l10n_hk_autopay_account_type == 'bban':
            return self.bank_account_id.bank_id.l10n_hk_bank_code
        else:
            return ''

    def get_l10n_hk_autopay_field(self) -> str:
        self.ensure_one()
        if self.l10n_hk_autopay_account_type == 'bban':
            return re.sub(r"[^0-9]", "", self.bank_account_id.acc_number)
        if self.l10n_hk_autopay_account_type == 'svid':
            return self.l10n_hk_autopay_svid
        if self.l10n_hk_autopay_account_type == 'emal':
            return self.l10n_hk_autopay_emal
        if self.l10n_hk_autopay_account_type == 'mobn':
            return self.l10n_hk_autopay_mobn
        if self.l10n_hk_autopay_account_type == 'hkid':
            return self.identification_id

    @api.depends('l10n_hk_rental_ids')
    def _compute_l10n_hk_rentals_count(self):
        for employee in self:
            employee.l10n_hk_rentals_count = len(employee.l10n_hk_rental_ids)

    def action_open_rentals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('l10n_hk_hr_payroll.action_l10n_hk_rental')
        action['views'] = [(False, 'list'), (False, 'form')]
        action['domain'] = [('id', 'in', self.l10n_hk_rental_ids.ids)]
        action['context'] = {'default_employee_id': self.id}
        return action
