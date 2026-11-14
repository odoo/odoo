from odoo import api, fields, models
from odoo.tools import get_lang
from odoo.tools.binary import BinaryBytes


class HrContractPDFWizard(models.TransientModel):
    _name = 'hr.contract.pdf.wizard'
    _description = 'Generate Contract'

    version_id = fields.Many2one('hr.version', required=True, readonly=True)
    employee_id = fields.Many2one(related='version_id.employee_id')
    company_id = fields.Many2one(related='version_id.company_id')
    currency_id = fields.Many2one(related='version_id.currency_id')

    # Draft copies of the version values: they are only written on the version
    # once the contract file is generated, so discarding the wizard changes nothing.
    legal_name = fields.Char(compute='_compute_legal_name', store=True, readonly=False, precompute=True, string='Legal Name')
    wage = fields.Monetary(compute='_compute_wage', store=True, readonly=False, precompute=True)
    contract_date_start = fields.Date(
        compute='_compute_contract_date_start', store=True, readonly=False, precompute=True, required=True,
        string='Contract Start Date')
    contract_date_end = fields.Date(
        compute='_compute_contract_date_end', store=True, readonly=False, precompute=True, string='Contract End Date')
    job_id = fields.Many2one(
        'hr.job', compute='_compute_job_id', store=True, readonly=False, precompute=True, string="Job Position",
        check_company=True)
    # Only printed on the contract, never written on the version
    working_hours = fields.Text(
        compute='_compute_working_hours', store=True, readonly=False, precompute=True, string="Working Hours")
    work_location = fields.Char(
        compute='_compute_work_location', store=True, readonly=False, precompute=True, string="Work Location")
    contract_lang_id = fields.Many2one(
        'res.lang', compute='_compute_contract_lang_id', store=True, readonly=False, precompute=True, required=True,
        string="Contract Language")
    duplicate_lang_id = fields.Many2one(
        'res.lang', string="Duplicate Language", ui_domain="[('id', '!=', contract_lang_id)]",
        help="Add a copy of the contract in this language, e.g. the language of the employee. "
             "It is given for information, the contract language prevails.")
    benefits = fields.Text()

    @api.model
    def _get_version_field_names(self):
        return [
            'wage',
            'contract_date_start',
            'contract_date_end',
            'job_id',
        ]

    @api.depends('employee_id')
    def _compute_legal_name(self):
        for wizard in self:
            wizard.legal_name = wizard.employee_id.legal_name

    @api.depends('version_id')
    def _compute_wage(self):
        for wizard in self:
            wizard.wage = wizard.version_id.wage

    @api.depends('version_id')
    def _compute_contract_date_start(self):
        for wizard in self:
            wizard.contract_date_start = wizard.version_id.contract_date_start or fields.Date.context_today(wizard)

    @api.depends('version_id')
    def _compute_contract_date_end(self):
        for wizard in self:
            wizard.contract_date_end = wizard.version_id.contract_date_end

    @api.depends('version_id')
    def _compute_job_id(self):
        for wizard in self:
            wizard.job_id = wizard.version_id.job_id

    @api.depends('version_id')
    def _compute_working_hours(self):
        for wizard in self:
            version = wizard.version_id
            wizard.working_hours = (version.resource_calendar_id or version.company_id.resource_calendar_id).name

    @api.depends('version_id')
    def _compute_work_location(self):
        for wizard in self:
            version = wizard.version_id
            wizard.work_location = (version.work_location_id.address_id or version.address_id).address_inline

    @api.depends('employee_id')
    def _compute_contract_lang_id(self):
        for wizard in self:
            lang_code = get_lang(self.env, wizard.employee_id.lang or wizard.employee_id.user_id.lang).code
            wizard.contract_lang_id = self.env['res.lang']._lang_get(lang_code)

    def _get_contract_benefits(self):
        """ Return the descriptions of the benefits of the version, printed on
        the contract in the language of the context before the ``benefits``
        typed in the wizard. Overridden by the modules managing the benefits.

        :rtype: list[str]
        """
        self.ensure_one()
        return []

    def _get_contract_langs(self):
        """ Return the languages to print the contract in: the language of the
        contract, then the language of its duplicate. """
        self.ensure_one()
        return self.contract_lang_id | self.duplicate_lang_id

    def _get_contract_report_template(self, lang):
        """ Return the xmlid of the template printing the contract in ``lang``,
        the localizations can return their own templates.

        :param lang: ``res.lang`` record, see `_get_contract_langs`
        """
        self.ensure_one()
        return 'hr.report_contract'

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.with_context(lang=self.contract_lang_id.code).env._("Employment Contract - %s", self.legal_name)

    def _get_version_changes(self, contract_dates=True):
        """ Return the write values of the fields edited in the wizard.

        :param bool contract_dates: whether to include the contract dates; they
            are never copied to other versions, as on the employee form.
        """
        self.ensure_one()
        changes = {}
        for fname in self._get_version_field_names():
            if not contract_dates and fname in ('contract_date_start', 'contract_date_end'):
                continue
            field = self._fields[fname]
            if self[fname] != self.version_id[fname]:
                changes[fname] = field.convert_to_write(self[fname], self)
        return changes

    def _get_future_versions(self):
        """ Return the later versions of the same contract, the contract file
        must not be copied to the versions of another contract. """
        self.ensure_one()
        version = self.version_id
        return self.employee_id.version_ids.filtered(
            lambda v: v.date_version > version.date_version and v.contract_date_start == version.contract_date_start,
        )

    def get_future_version_changes(self):
        """ Return the changes to display in the multi-version confirmation
        dialog, or an empty dict when there is no later version to update. The
        generated contract file is always proposed for the later versions. """
        self.ensure_one()
        # the button opens the document layout configurator first, ask once back from it
        if self._needs_document_layout() or not self._get_future_versions():
            return {}
        changes = self._get_version_changes(contract_dates=False)
        changes_to_display = self.employee_id.with_context(version_id=self.version_id.id).get_multi_version_changes(changes)
        # binary fields have no tracking display, describe the file by its name
        contract_file_field = self.env['ir.model.fields']._get('hr.version', 'contract_file')
        if current_file := self.version_id.contract_file:
            current_file_name = current_file.filename or self.env._("Current file")
        else:
            current_file_name = self.env._("None")
        changes_to_display[f'({contract_file_field.field_description})'] = (
            current_file_name,
            f'{self._get_report_base_filename()}.pdf',
        )
        return changes_to_display

    def _needs_document_layout(self):
        return (
            not self.env.context.get('discard_logo_check')
            and (self.env.su or self.env.user._is_admin())
            and not self.env.company.external_report_layout_id
        )

    def _get_document_layout_action(self):
        if not self._needs_document_layout():
            return False
        action = {
            'name': self.env._("Generate Contract"),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': self.env.context.get('dialog_size', 'medium')},
        }
        layout_action = self.env['ir.actions.report']._action_configure_external_report_layout(action)
        # Need to remove this context for windows action
        action.pop('close_on_report_download', None)
        return layout_action

    def _generate_contract(self):
        """ Render the contract and save it on the version, along with the values
        edited in the wizard.

        :return: the PDF content and its file name
        """
        self.ensure_one()
        self._install_contract_lang()
        pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf('hr.action_report_contract', self.ids)
        filename = f'{self._get_report_base_filename()}.pdf'
        contract_file = BinaryBytes(pdf_content, filename=filename)
        if self.env.context.get('hr_contract_update_future_versions'):
            self._get_future_versions().write({
                **self._get_version_changes(contract_dates=False),
                'contract_file': contract_file,
            })
        self.version_id.write({
            **self._get_version_changes(),
            'contract_file': contract_file,
        })
        if self.legal_name != self.employee_id.legal_name:
            self.employee_id.legal_name = self.legal_name
        return pdf_content, filename

    def action_generate_pdf(self):
        self.ensure_one()
        if layout_action := self._get_document_layout_action():
            return layout_action
        self._generate_contract()
        return {'type': 'ir.actions.act_window_close'}

    def _install_contract_lang(self):
        """ Install the languages of the contract if they are not active yet, e.g.
        the legal language of the work place, to print the contract in them. """
        self.ensure_one()
        if inactive_langs := self._get_contract_langs().filtered(lambda lang: not lang.active):
            # only the administrators manage the languages, but the contract must be written in these
            inactive_langs.sudo().action_unarchive()

    def action_preview_pdf(self):
        self.ensure_one()
        self._install_contract_lang()
        return self.env.ref('hr.action_report_contract').report_action(self)

    def action_send_pdf(self):
        self.ensure_one()
        if layout_action := self._get_document_layout_action():
            return layout_action
        pdf_content, filename = self._generate_contract()
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'raw': pdf_content,
            'res_model': 'mail.compose.message',
            'res_id': 0,
            'type': 'binary',
            'mimetype': 'application/pdf',
        })
        template = self.env.ref('hr.mail_template_employee_contract', raise_if_not_found=False)
        return {
            'name': self.env._("Send Contract"),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_composition_mode': 'comment',
                'default_model': 'hr.employee',
                'default_res_ids': self.employee_id.ids,
                'default_template_id': template.id if template else False,
                'default_attachment_ids': attachment.ids,
            },
        }
