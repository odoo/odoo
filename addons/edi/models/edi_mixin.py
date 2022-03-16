# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EdiDocumentMixin(models.AbstractModel):
    """ This mixin is to be inherited by models wishing to use the edi system.

    It will centralize the logic to link a document (model) to edi flows, and as many helpers as possible
    so that the code needed to implement the edi system on a new model is kept as minimalistic as possible.
    """
    _name = 'edi.document.mixin'
    _description = 'EDI Document Mixin'

    edi_flow_ids = fields.One2many(
        comodel_name='edi.flow',
        inverse_name='res_id',
        domain=lambda d: [('res_model', '=', d._name)],  # Will use the model name of the model inheriting this mixin.
    )
    edi_error_count = fields.Integer(
        compute='_compute_edi_error_count',
        help='How many EDIs are in error for this move ?')
    edi_blocking_level = fields.Selection(
        selection=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
        compute='_compute_edi_error_message')
    edi_error_message = fields.Html(
        compute='_compute_edi_error_message')
    edi_web_services_to_process = fields.Text(
        compute='_compute_edi_web_services_to_process',
        help="Technical field to display the documents that will be processed by the CRON")
    edi_show_cancel_button = fields.Boolean(
        compute='_compute_edi_show_cancel_button')
    edi_show_abandon_cancel_button = fields.Boolean(
        compute='_compute_edi_show_abandon_cancel_button')

    def _get_document_type(self):
        """ To be overriden if needed to specialize the types. For example, we want to differentiate moves linked to
        payment from moves linked to an invoice.
        """
        self.ensure_one()
        return self._name

    @api.depends('edi_flow_ids.error')
    def _compute_edi_error_count(self):
        for document in self:
            document.edi_error_count = len(document.edi_flow_ids.filtered(lambda f: f.error))

    @api.depends('edi_error_count', 'edi_flow_ids.error', 'edi_flow_ids.blocking_level')
    def _compute_edi_error_message(self):
        for document in self:
            if document.edi_error_count == 0:
                document.edi_error_message = None
                document.edi_blocking_level = None
            elif document.edi_error_count == 1:
                error_doc = document.edi_flow_ids.filtered(lambda d: d.error)
                document.edi_error_message = error_doc.error
                document.edi_blocking_level = error_doc.blocking_level
            else:
                error_levels = set([flow.blocking_level for flow in document.edi_flow_ids])
                if 'error' in error_levels:
                    document.edi_blocking_level = 'error'
                elif 'warning' in error_levels:
                    document.edi_blocking_level = 'warning'
                else:
                    document.edi_blocking_level = 'info'
                document.edi_error_message = _(
                    "%s Electronic invoicing %s(s)",
                    str(document.edi_error_count),
                    document.edi_blocking_level
                )

    @api.depends(
        'edi_flow_ids',
        'edi_flow_ids.state',
        'edi_flow_ids.blocking_level',
        'edi_flow_ids.edi_format_id',
        'edi_flow_ids.edi_format_id.name')
    def _compute_edi_web_services_to_process(self):
        for document in self:
            to_process = document.edi_flow_ids._get_relevants().filtered(lambda f: f.state in ['to_send', 'to_cancel'] and f.blocking_level != 'error')
            format_web_services = to_process.edi_format_id.filtered(lambda f: f._get_edi_format_settings().get('needs_web_services'))
            document.edi_web_services_to_process = ', '.join(f.name for f in format_web_services)

    @api.depends('state', 'edi_flow_ids.state')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()  # todo this is account move function, move it there
        for document in self:
            for flow in document.edi_flow_ids._get_relevants():
                if (flow._get_edi_format_settings().get('needs_web_services')
                        and flow.state in ('sent', 'to_cancel')
                        and flow.edi_format_id._is_format_required(document, self._get_document_type())):
                    document.show_reset_to_draft_button = False
                    break

    @api.depends('edi_flow_ids.state', 'edi_flow_ids.aborted')  # state
    def _compute_edi_show_cancel_button(self):
        for document in self:
            # if document.state != 'posted':  # todo the mixin cannot assume a field will exists on the model using it. override this in account
            #     document.edi_show_cancel_button = False
            #     continue

            document.edi_show_cancel_button = any([
                flow._get_edi_format_settings().get('needs_web_services')
                and flow.state == 'sent'
                and flow.edi_format_id._is_format_required(document, self._get_document_type())
                for flow in document.edi_flow_ids._get_relevants()
            ])

    @api.depends('edi_flow_ids.state')
    def _compute_edi_show_abandon_cancel_button(self):
        for document in self:
            document.edi_show_abandon_cancel_button = any(
                flow._get_edi_format_settings().get('needs_web_services')
                and flow.state == 'to_cancel'
                and flow.edi_format_id._is_format_required(document, self._get_document_type())
                for flow in document.edi_flow_ids._get_relevants()
            )

    ####################################################
    # Hooks
    ####################################################

    @api.model
    def _hook_initiate_flows(self, documents):
        """ Hook to be called when a document should create its flows.
        This method is to be overriden by EDI's to create the EDI flows if needed."""

    def _hook_cancel_flows(self):
        """ Hook to be called when a document is cancelled.
        This method is to be overriden by EDI's to add additional logic if needed.
        The default behavior is as such:
            - Flows in the send mode but not yet sent are aborted.
            - Flows in the send mode but already sent are aborted, and trigger the creation of a cancellation flow.
        """
        existing_flows = self.edi_flow_ids._get_relevants(flow_type='send')
        existing_flows.filtered(lambda f: f.state != 'sent')._cancel()
        existing_flows.filtered(lambda f: f.state == 'sent')._cancel(with_cancellation_flow=True)

    def _hook_request_flow_cancellation(self):
        """ Hook to be called when a document should cancel its web service flows only.
        This method is to be overriden by EDI's to add additional logic if needed.
        The default behavior is as such:
            - Start the cancellation of all flows that needs web services, create a cancellation flow for each of them.
        """
        to_abort_flows = self.env['edi.flow']
        for document in self:
            is_document_marked = False
            for flow in document.edi_flow_ids._get_relevants(flow_type='send'):
                if (flow._get_edi_format_settings().get('needs_web_services')
                        and flow.edi_file_ids
                        and flow.edi_format_id._is_format_required(document, self._get_document_type())):
                    to_abort_flows |= flow
                    is_document_marked = True
            if is_document_marked:
                document.message_post(body=_("A cancellation of the EDI has been requested."))

        to_abort_flows._cancel(with_cancellation_flow=True)

    ####################################################
    # Export
    ####################################################

    def _is_ready_to_be_sent(self):
        res = super()._is_ready_to_be_sent()
        if not res:
            return False
        edi_documents_to_send = self.edi_flow_ids.filtered(lambda x: x.state == 'to_send')
        return not bool(edi_documents_to_send)

    def _get_edi_format_by_code(self, edi_format_code):
        """ Return the EDI format corresponding to the given code.
        To be inherited to filter on specific formats, such as the ones in a journal for account moves.
        """
        self.ensure_one()
        return self.env['edi.format'].search([('code', '=', edi_format_code)], limit=1)

    @api.model
    def _create_flow_for_format_code(self, edi_format_code, documents):
        edi_flow_vals_list = []
        for document in documents:
            edi_format = document._get_edi_format_by_code(edi_format_code)
            if edi_format and edi_format._is_format_required(document, document._get_document_type()):
                errors = edi_format._check_document_configuration(document)
                if errors:
                    raise UserError(_("Invalid document configuration:\n\n%s") % '\n'.join(errors))

                # Existing flows are aborted, and a new send flow is created. Most likely we abort a cancel flow if any.
                document.edi_flow_ids._get_relevants(edi_format)._cancel()
                edi_flow_vals_list.append({
                    'edi_format_id': edi_format.id,
                    'flow_type': 'send',
                    'res_id': document.id,
                    'res_model': document._name,
                })
        self.env['edi.flow'].create(edi_flow_vals_list)

    def abandon_edi_cancellation(self):
        '''Cancel the request for cancellation of the EDI.
        '''
        self.env['edi.flow']._abandon_cancel_flow(documents=self)

    def _get_edi_flows(self, edi_format, flow_type=False):
        return self.edi_flow_ids._get_relevants(edi_format=edi_format, flow_type=flow_type)

    def _get_edi_files(self, edi_format, flow_type=False):
        return self._get_edi_flows(edi_format, flow_type).edi_file_ids

    ####################################################
    # Business operations
    ####################################################

    def action_process_edi_web_services(self, with_commit=True):
        flows = self.edi_flow_ids._get_relevants().filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
        flows._process_documents_web_services(with_commit=with_commit)

    def _retry_edi_documents_error_hook(self):
        ''' Hook called when an edi document are retried. For example, when it's needed to clean a field.
        TO OVERRIDE
        '''
        return

    def action_retry_edi_documents_error(self):
        self._retry_edi_documents_error_hook()
        self.edi_flow_ids.write({'error': False, 'blocking_level': False})
        self.action_process_edi_web_services()

    def unlink(self):
        """ Override unlink to delete the flows related to a document before deleting it. """
        self.edi_flow_ids.unlink()
        return super().unlink()
