from odoo import api, fields, models
from odoo.tools.binary import BinaryBytes


class HrContractPDFWizard(models.TransientModel):
    _name = 'hr.contract.pdf.wizard'
    _description = 'Generate Contract'

    version_id = fields.Many2one('hr.version', required=True, readonly=True)
    employee_id = fields.Many2one(related='version_id.employee_id')
    company_id = fields.Many2one(related='version_id.company_id')
    company_country_id = fields.Many2one(related='version_id.company_country_id')
    parent_company_id = fields.Many2one(related='version_id.company_id.parent_id')
    address_id = fields.Many2one(related='version_id.address_id')
    currency_id = fields.Many2one(related='version_id.currency_id')

    # Draft copies of the version values: they are only written on the version
    # once the contract file is generated, so discarding the wizard changes nothing.
    legal_name = fields.Char(compute='_compute_from_version', store=True, readonly=False, string='Legal Name')
    wage = fields.Monetary(compute='_compute_from_version', store=True, readonly=False)
    resource_calendar_id = fields.Many2one(
        'resource.calendar', compute='_compute_from_version', store=True, readonly=False, string="Working Hours",
        domain="['|', ('company_id', '=', False), ('company_id.id', 'parent_of', company_id)]")
    contract_date_start = fields.Date(
        compute='_compute_from_version', store=True, readonly=False, required=True, string='Contract Start Date')
    contract_date_end = fields.Date(compute='_compute_from_version', store=True, readonly=False, string='Contract End Date')
    job_title = fields.Char(compute='_compute_from_version', store=True, readonly=False)
    employee_type_id = fields.Many2one(
        'hr.employee.type', compute='_compute_from_version', store=True, readonly=False, string="Employee Type",
        domain="[('country_id', 'in', [company_country_id, False]), '|', ('company_id', 'in', [company_id, False]), ('company_id', '=', parent_company_id)]")
    work_location_id = fields.Many2one(
        'hr.work.location', compute='_compute_from_version', store=True, readonly=False, string="Work Location",
        domain="[('address_id', '=', address_id)]")

    @api.model
    def _get_version_field_names(self):
        return [
            'wage',
            'resource_calendar_id',
            'contract_date_start',
            'contract_date_end',
            'job_title',
            'employee_type_id',
            'work_location_id',
        ]

    @api.depends('version_id')
    def _compute_from_version(self):
        for wizard in self:
            version = wizard.version_id
            wizard.legal_name = wizard.employee_id.legal_name
            for fname in self._get_version_field_names():
                wizard[fname] = version[fname]
            wizard.contract_date_start = version.contract_date_start or fields.Date.context_today(wizard)
            wizard.resource_calendar_id = version.resource_calendar_id or version.company_id.resource_calendar_id

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.with_context(lang=self.employee_id.lang).env._("Employment Contract - %s", self.legal_name)

    def _get_version_changes(self, propagate=False):
        """ Return the write values of the fields edited in the wizard.

        :param bool propagate: only keep the values that can be copied to other
            versions; the contract dates are never copied, as on the employee form.
        """
        self.ensure_one()
        changes = {}
        for fname in self._get_version_field_names():
            if propagate and fname in ('contract_date_start', 'contract_date_end'):
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
        changes = self._get_version_changes(propagate=True)
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
            and self.env.is_admin()
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
            'context': {'dialog_size': 'medium'},
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
        pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf('hr.action_report_contract', self.ids)
        filename = f'{self._get_report_base_filename()}.pdf'
        contract_file = BinaryBytes(pdf_content, filename=filename)
        if self.env.context.get('hr_contract_update_future_versions'):
            self._get_future_versions().write({
                **self._get_version_changes(propagate=True),
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

    def action_preview_pdf(self):
        self.ensure_one()
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
