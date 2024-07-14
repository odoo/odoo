# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class WorkflowActionRule(models.Model):
    _name = "documents.workflow.rule"
    _description = "A set of condition and actions which will be available to all attachments matching the conditions"
    _order = "sequence"

    domain_folder_id = fields.Many2one('documents.folder', string="Related Workspace", required=True, ondelete='cascade')
    name = fields.Char(required=True, string="Action Button Name", translate=True)
    note = fields.Char(string="Tooltip")
    sequence = fields.Integer('Sequence', default=10)

    # Conditions
    condition_type = fields.Selection([
        ('criteria', "Criteria"),
        ('domain', "Domain"),
    ], default='criteria', string="Condition type")

    # Domain
    domain = fields.Char()

    # Criteria
    criteria_partner_id = fields.Many2one('res.partner', string="Contact")
    criteria_owner_id = fields.Many2one('res.users', string="Owner")
    required_tag_ids = fields.Many2many('documents.tag', 'required_tag_ids_rule_table', string="Required Tags")
    excluded_tag_ids = fields.Many2many('documents.tag', 'excluded_tag_ids_rule_table', string="Excluded Tags")
    limited_to_single_record = fields.Boolean(string="One record limit", compute='_compute_limited_to_single_record')

    # Actions
    partner_id = fields.Many2one('res.partner', string="Set Contact")
    user_id = fields.Many2one('res.users', string="Set Owner")
    tag_action_ids = fields.One2many('documents.workflow.action', 'workflow_rule_id', string='Set Tags')
    folder_id = fields.Many2one('documents.folder', string="Move to Workspace")
    create_model = fields.Selection([('link.to.record', 'Link to record')], string="Create")
    link_model = fields.Many2one('ir.model', string="Specific Model Linked",
                                 domain=[('model', '!=', 'documents.document'), ('is_mail_thread', '=', 'True')])

    # Activity
    remove_activities = fields.Boolean(string='Mark all as Done')
    activity_option = fields.Boolean(string='Schedule Activity')
    activity_type_id = fields.Many2one('mail.activity.type', string="Activity type")
    activity_summary = fields.Char('Summary')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_note = fields.Html(string="Activity Note")
    has_owner_activity = fields.Boolean(string="Set the activity on the document owner")
    activity_user_id = fields.Many2one('res.users', string='Responsible')

    @api.onchange('domain_folder_id')
    def _on_domain_folder_id_change(self):
        if self.domain_folder_id != self.required_tag_ids.mapped('folder_id'):
            self.required_tag_ids = False
        if self.domain_folder_id != self.excluded_tag_ids.mapped('folder_id'):
            self.excluded_tag_ids = False

    def _compute_limited_to_single_record(self):
        """
        Overwritten by bridge modules to define whether the rule is only available for one record at a time.
        """
        self.update({'limited_to_single_record': False})

    def create_record(self, documents=None):
        """
        implemented by each link module to define specific fields for the new business model (create_values)

        When creating/copying/writing an ir.attachment with a res_model and a res_id, add no_document=True
        to the context to prevent the automatic creation of a document.

        :param documents: the list of the documents of the selection
        :return: the action dictionary that will be called after the workflow action is done or True.
        """
        self.ensure_one()
        if self.create_model == 'link.to.record':
            return self.link_to_record(documents)

        return True

    def link_to_record(self, documents=None):
        """
        :param documents: the list of the documents of the selection
        :return: the action dictionary that will activate a wizard to create a link between the documents of the selection and a record.
        """
        context = {
                    'default_document_ids': documents.ids,
                    'default_resource_ref': False,
                    'default_is_readonly_model': False,
                    'default_model_ref': False,
                    }

        documents_link_record = [d for d in documents if (d.res_model != 'documents.document')]
        if documents_link_record:
            return {
                    'warning': {
                            'title': _("Already linked Documents"),
                            'documents': [d.name for d in documents_link_record],
                            }
                    }
        elif self.link_model:
            # Throw a warning if the user does not have access to the model.
            link_model_sudo = self.link_model.sudo()
            self.env[link_model_sudo.model].check_access_rights('write')
            context['default_is_readonly_model'] = True
            context['default_model_id'] = link_model_sudo.id
            first_valid_id = self.env[link_model_sudo.model].search([], limit=1).id
            context['default_resource_ref'] = f'{link_model_sudo.model},{first_valid_id}'

        link_to_record_action = {
                'name': _('Choose a record to link'),
                'type': 'ir.actions.act_window',
                'res_model': 'documents.link_to_record_wizard',
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, "form")],
                'context': context,
            }
        return link_to_record_action

    @api.model
    def unlink_record(self, document_ids=None):
        """
        Removes the link with its record for all the documents having is id in document_ids
        """
        documents = self.env['documents.document'].browse(document_ids)
        documents.write({
            'res_model': 'documents.document',
            'res_id': False,
            'is_editable_attachment': False,
        })

    def apply_actions(self, document_ids):
        """
        called by the front-end Document Inspector to apply the actions to the selection of ID's.

        :param document_ids: the list of documents to apply the action.
        :return: if the action was to create a new business object, returns an action to open the view of the
                newly created object, else returns True.
        """
        documents = self.env['documents.document'].browse(document_ids)

        # partner/owner/share_link/folder changes
        document_dict = {}
        if self.user_id:
            document_dict['owner_id'] = self.user_id.id
        if self.partner_id:
            document_dict['partner_id'] = self.partner_id.id
        if self.folder_id:
            document_dict['folder_id'] = self.folder_id.id

        # Use sudo if user has write access on document else allow to do the
        # other workflow actions(like: schedule activity, send mail etc...)
        try:
            documents.check_access_rights('write')
            documents.check_access_rule('write')
            documents = documents.sudo()
        except AccessError:
            pass

        documents.write(document_dict)

        for document in documents:
            if self.remove_activities:
                document.activity_ids.action_feedback(
                    feedback="completed by rule: %s. %s" % (self.name, self.note or '')
                )

            # tag and facet actions
            for tag_action in self.tag_action_ids:
                tag_action.execute_tag_action(document)

        if self.activity_option and self.activity_type_id:
            documents.documents_set_activity(settings_record=self)

        if self.create_model:
            return self.with_company(documents.company_id).create_record(documents=documents)

        return True
