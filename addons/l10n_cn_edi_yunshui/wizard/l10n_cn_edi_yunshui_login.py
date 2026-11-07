# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError


class L10nCnEdiYunshuiLogin(models.TransientModel):
    _name = 'l10n_cn_edi_yunshui.login'
    _description = "Yunshui Tax Bureau Login"

    company_id = fields.Many2one(comodel_name='res.company', required=True, readonly=True)
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        readonly=True,
        help="Invoices waiting for this login, sent again once it's done.",
    )
    step_name = fields.Char(required=True, readonly=True)
    step_code = fields.Char(readonly=True)
    message = fields.Char(readonly=True)
    role_options = fields.Char(readonly=True)
    zrrlx = fields.Selection(
        selection=[
            ('01', '01 法定代表人'),
            ('02', '02 财务负责人'),
            ('03', '03 办税员'),
            ('05', '05 管理员'),
            ('07', '07 领票员'),
            ('08', '08 社保经办人'),
            ('09', '09 开票员'),
            ('10', '10 销售人员'),
        ],
        string="Responsibility Role",
    )
    sms_code = fields.Char(string="SMS Code")
    qrcode_image = fields.Binary(string="QR Code Image", readonly=True, attachment=False)
    qrcode_id = fields.Char(string="QR Code ID", readonly=True)
    qrcode_expires_in = fields.Char(readonly=True)
    qrcode_status = fields.Char(readonly=True)

    def _check_company_access(self):
        self.ensure_one()
        if self.company_id not in self.env.user.company_ids:
            raise UserError(self.env._("You cannot operate Yunshui login for this company."))
        if self.invoice_ids.filtered(lambda move: move.company_id != self.company_id):
            raise UserError(self.env._("This login wizard has invoices from another company."))

    def action_send_sms(self):
        self.ensure_one()
        return self._run_step('send_sms') or self._action_reopen()

    def action_get_qr(self):
        self.ensure_one()
        return self._run_step('create_qrcode') or self._action_reopen()

    def action_verify_qr(self):
        self.ensure_one()
        if not self.qrcode_id:
            raise UserError(self.env._("Missing QR code id. Click 'Get QR Code' first."))
        return self._run_step('verify_qrcode', qrcode_id=self.qrcode_id) or self._action_reopen()

    def action_select_role(self):
        self.ensure_one()
        if not self.zrrlx:
            raise UserError(self.env._("Please select a responsibility role."))
        allowed_roles = {value for value in (self.role_options or '').split(',') if value}
        if allowed_roles and self.zrrlx not in allowed_roles:
            raise UserError(self.env._("The selected role is not offered by the tax bureau in this step."))
        return self._run_step('select_zrrlx', zrrlx=self.zrrlx) or self._action_reopen()

    def action_submit_sms(self):
        self.ensure_one()
        sms_code = (self.sms_code or '').strip()
        if not sms_code.isdigit():
            raise UserError(self.env._("Please enter the numeric SMS code from the tax bureau."))
        return self._run_step('sms_login', smsCode=sms_code) or self._action_reopen()

    def action_restart(self):
        self.ensure_one()
        return self._run_step('login') or self._action_reopen()

    def _run_step(self, step_name, **extra_payload):
        self.check_access('write')
        self._check_company_access()
        result = self.company_id._l10n_cn_edi_get_client().login_step(step_name, **extra_payload)
        role_data = result.get('data') or []
        if isinstance(role_data, str):
            role_data = [value for value in role_data.split(',') if value]
        if role_data and self.zrrlx and self.zrrlx not in role_data:
            self.zrrlx = False
        self.write({
            'step_name': step_name,
            'step_code': str(result.get('step_code') or ''),
            'message': result.get('message') or False,
            'role_options': ','.join(role_data),
            'qrcode_image': result.get('qrcode') or self.qrcode_image,
            'qrcode_id': result.get('qrcode_id') or self.qrcode_id,
            'qrcode_expires_in': str(result['expires_in']) if 'expires_in' in result else self.qrcode_expires_in,
            'qrcode_status': str(result['qrcode_status']) if 'qrcode_status' in result else self.qrcode_status,
        })
        if self.step_code == '0':
            self.company_id.sudo().l10n_cn_edi_yunshui_relogin = False
            if self.invoice_ids:
                return self.invoice_ids.action_send_and_print()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': self.env._("%(company)s is logged in to the tax bureau.", company=self.company_id.name),
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        return None

    def action_next(self):
        self.ensure_one()
        action = self._run_step(self.step_name)
        return action or self._action_reopen()

    def _action_reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Tax Bureau Login"),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
