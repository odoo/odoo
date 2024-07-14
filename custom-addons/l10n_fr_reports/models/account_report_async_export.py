# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, _lt
from odoo.exceptions import UserError
from odoo.addons.iap.tools import iap_tools

from datetime import timedelta
import json

ENDPOINT = "https://l10n-fr-aspone.api.odoo.com"

# Allows to translate the errors returned by IAP
ERROR_CODE_TO_MSG = {
    'invalid_xml': _lt("The structure of the xml document is invalid."),
    'missing_deposit': _lt("No deposit_uid was provided."),
    'missing_declaration': _lt("No declaration_uid was provided."),
    'unknown_deposit': _lt("This deposit is unknown from Odoo."),
    'unknown_declaration': _lt("This declaration is unknown from Odoo."),
    'error_subscription': _lt("An error has occurred when trying to verify your subscription."),
    'dbuuid_not_exist': _lt("Your database uuid does not exist"),
    'not_enterprise': _lt("You do not have an Odoo enterprise subscription."),
    'not_prod_env': _lt("Your database is not used for a production environment."),
    'not_active_db': _lt("Your database is not yet activated."),
    'add_document': _lt("An error occurred while trying to send the document: "),
    'get_interchange': _lt("An error occurred while getting the interchange details: "),
    'get_declaration': _lt("An error occurred while getting the declaration details: "),
    'get_attachment': _lt("An error occurred while getting the attachments: "),
}


class AccountReportAsyncExport(models.Model):
    _name = 'account.report.async.export'
    _description = "Account Report Async Export"

    name = fields.Char()
    date_from = fields.Date()
    date_to = fields.Date()
    report_id = fields.Many2one('account.report')
    attachment_ids = fields.Many2many('ir.attachment')
    deposit_uid = fields.Char()  # ASPOne "Interchange" identifier
    declaration_uid = fields.Char()  # ASPOne identifier (an interchange might have several declarations)
    recipient = fields.Selection([
        ("DGI_EDI_TVA", "DGFiP"),
        ("CEC_EDI_TVA", "Expert Accountant"),
        ("OGA_EDI_TVA", "OGA"),
    ], readonly=True)
    state = fields.Selection([
        ("to_send", "To send"),  # nothing was sent to ASPone
        ("sent", "Sent"),  # xml sent to ASPone (via AddDocument)
        ("accepted", "Accepted"),  # GetDeclaration returned "ACCEPTED_BY_DESTINATATION"
        ("rejected", "Rejected"),  # GetDeclaration returned "REJECTED_BY_DESTINATION" OR "TRANSLATED_KO"
    ], default="to_send")
    step_1_logs = fields.Char()
    step_2_logs = fields.Char()
    message = fields.Html(compute="_compute_message")

    @api.depends("step_1_logs", "step_2_logs", "state")
    def _compute_message(self):
        for report in self:
            full_logs = json.loads(report.step_1_logs or '[]') + json.loads(report.step_2_logs or '[]')
            msg = report._get_message(full_logs)
            if report.state == 'to_send':
                report.message = ""
            elif report.state == 'accepted':
                report.message = _("<b> The report has been fully processed by the recipient </b>") + msg
            elif report.state == 'rejected':
                report.message = _("<b> The report has been rejected </b>") + msg
            else:
                report.message = _(
                    "<b> Warning, the report has not been fully processed by the recipient yet </b>") + msg

    @api.model
    def _get_message(self, logs):
        """ Recursively build the message from the logs. See '_collect_errors_in_history'. """
        if not logs:
            return ""
        msg = "<ul>"
        for log in logs:
            if log['is_error']:
                msg += "<li style='color: red;'>"
            else:
                msg += "<li>"
            msg += log['name'] + ": " + log['label'] + "</li>"
            # handle details
            if log.get('details'):
                msg += self._get_message(log['details'])
        msg += "</ul>"
        return msg

    @api.model
    def _cron_process_all_reports_async_export(self):
        async_exports = self.search([('state', 'in', ('to_send', 'sent'))])
        async_exports._process_reports_async_exports()

        # Trigger the CRON again if there are remainineg jobs to process
        if async_exports.mapped(lambda export: export.state in ('to_send', 'sent')).count(True) > 0:
            self.env.ref('l10n_fr_reports.ir_cron_l10n_fr_reports')._trigger(fields.Datetime.now() + timedelta(minutes=30))

    def _process_reports_async_exports(self):
        """
        The ASPOne API returns a depositID when sending a document through `AddDocument`.
        Using this depositID, we call `getInterchangesByDepositID` to get the list of "interchanges" associated to this
        document. Each "interchange" contains 1 to n declarations (they each have a declarationID).
        The details of a declaration are then obtained by calling `getDeclarationDetails` with the declarationID.

        In this module, each document creates one interchange (deposit_uid) linked to one declaration (declaration_uid).

        The API will first process the xml: validate it, convert it to an edifact file and validate the edifact (this
        is the 1st step, using `getInterchangesByDepositID`).
        Then, it will send the edifact to the recipient, and obtain its acknowledgment (this is the 2nd step, using
        `getDeclarationDetails`).

        If the 1st step returns an error (for instance: invalid xml/edifact), the flow will be stopped, and there is
        no need to call the 2nd step. In addition, the 2nd step is only executed when the 1st was done (i.e. when it
        received a final state and was not in error).
        """
        for export in self:
            # Avoid calling the first step again if its state is already final
            first_step_state_final = False
            if export.step_1_logs:
                first_step_state_final = any(status['is_final'] for status in json.loads(export.step_1_logs))

            # First step
            if not first_step_state_final:
                response = export._get_interchanges_by_deposit_id()
                step_1_logs = export._process_interchanges_response(response)
                export.step_1_logs = json.dumps(step_1_logs)
                if any([status['is_error'] for status in step_1_logs]):
                    export.state = 'rejected'
                first_step_state_final = any([status['is_final'] for status in step_1_logs])

            # Second step
            if first_step_state_final and export.state != 'rejected' and export.declaration_uid:
                response = export._get_declaration_details()
                step_2_logs = export._process_declaration_response(response)

                export.step_2_logs = json.dumps(step_2_logs)
                if any([status['is_error'] for status in step_2_logs]):
                    export.state = 'rejected'
                elif any([status['is_final'] for status in step_2_logs]):
                    export.state = 'accepted'

    # ------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------

    def button_fetch_attachments(self):
        # DEPRECATED : This button will be removed in master
        self.ensure_one()
        attachments = self.attachment_ids.filtered(lambda a: a.name.endswith(".xml"))
        if attachments:
            return {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachments.ids[0]}?download=true",
            }

    def button_process_report(self):
        self.env.ref('l10n_fr_reports.ir_cron_l10n_fr_reports').method_direct_trigger()

    # ------------------------------------------------------------
    # Helper functions
    # ------------------------------------------------------------

    @api.model
    def _collect_errors_in_history(self, history, logs):
        """ The ASPOne API returns a list of events associated with the xml file sent. Each event has a status, a label,
        flags indicating the state is in error, is final, etc. A final state indicates the xml file has been approved
        by the recipient (e.g. the DGFiP) or has raised a fatal error.

        This function collects the events contained in a stateHistory ('history') into 'logs'.

        :param logs: has the following structure:
        [
            {'name': 'status_1', 'label': 'blabla', 'is_error': False, 'details': []},
            {'name': 'status_2', 'label': 'blabla', 'is_error': True, 'details': [
                {'name': 'status_2.A', 'label': 'more detailed blabla', 'is_error': True},
                {'name': 'status_2.B', 'label': 'more detailed blabla', 'is_error': True},
            ]},
        ]
        """
        log = {
            'name': history['name'],
            'label': history['label'],
            'is_error': history['isError'],
            'is_final': history['isFinal'],
            'details': [],
        }

        if history['stateDetailsHistory']:
            for sub_history in history['stateDetailsHistory']['stateDetail']:
                label = sub_history['label']
                if sub_history['detailledLabel']:
                    label += ": " + sub_history['detailledLabel']
                sub_log = {
                    'name': sub_history['name'],
                    'label': label,
                    'is_error': sub_history['isError'],
                    'is_final': sub_history['isFinal'],
                }
                log['details'].append(sub_log)

        logs.append(log)

    @api.model
    def _get_fr_webservice_answer(self, url, params):
        """ Post the request and catch known Exceptions, return the content of the response as a dict. """
        response = iap_tools.iap_jsonrpc(url, params=params)

        # Error from IAP
        if response.get('error'):
            err = response['error']
            if isinstance(response['error'], str):
                msg = ERROR_CODE_TO_MSG[err]
            else:
                msg = ERROR_CODE_TO_MSG[err[0]] + err[1]
            raise UserError(msg)

        # Error from ASPOne
        if response['responseType'] != 'SUCCESS':
            raise UserError(_(
                "Unexpected response from proxy: '%s %s'.\nPlease contact the support.",
                response['responseType'],
                response['response']['errorResponse']['message']),
            )

        return response

    # ------------------------------------------------------------
    # Processing the ASPOne responses
    # ------------------------------------------------------------

    def _process_interchanges_response(self, response):
        if not response['response']['successfullResponse']['interchanges']:
            raise Exception(_("Unexpected result: the response should contain an interchange."))
        if len(response['response']['successfullResponse']['interchanges']['interchange']) != 1:
            raise Exception(_("Unexpected result: the response should contain at most one interchange."))
        interchange = response['response']['successfullResponse']['interchanges']['interchange'][0]

        logs = []
        # The events are logged in reversed order (last event in 1st position)
        for history in reversed(interchange['statesHistory']['stateHistory']):
            self._collect_errors_in_history(history, logs)
        # Get the declaration_uid, NB: it will only be available when no errors were returned at this step
        if interchange['declarationIds'] \
                and interchange['declarationIds']['declarationId'] \
                and not self.declaration_uid:
            if len(interchange['declarationIds']['declarationId']) > 1:
                # Can occur if we send a document to more than one recipient (e.g. DGFiP + OGA)
                raise Exception(_("Unexpected result: the interchange should contain at most one declarationId."))
            self.declaration_uid = interchange['declarationIds']['declarationId'][0]
        return logs

    def _process_declaration_response(self, response):
        logs = []
        for history in reversed(response['response']['successfullResponse']['declarationTva']['statesHistory']['stateHistory']):
            self._collect_errors_in_history(history, logs)
            if history['isError']:
                self.state = 'rejected'
            if history['name'] == 'ACCEPTED_BY_DESTINATION':
                self.state = 'accepted'
        return logs

    def _process_recipient_reports_response(self, response):
        attachments_vals = []
        for recipient_report in response['response']['successfullResponse']['RecipientReports']:
            for report in recipient_report['report']:
                if 'data' not in report:
                    continue
                attachments_vals.append({
                    'name': report['filename'],
                    'res_model': 'account.report.async.export',
                    'res_id': self.id,
                    'type': 'binary',
                    'raw': report['data'].replace("'", "\n").encode(),  # format the edifact file
                    'mimetype': 'application/text',
                })
        return attachments_vals

    # ------------------------------------------------------------
    # Calls to ASPOne (via IAP)
    # ------------------------------------------------------------

    def _get_interchanges_by_deposit_id(self):
        """ First step: get the interchanges linked to a deposit_uid (possibly several interchanges per deposit). """
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return self._get_fr_webservice_answer(
            url=ENDPOINT + "/api/l10n_fr_aspone/1/get_interchanges_by_deposit_id",
            params={'db_uuid': db_uuid, 'deposit_uid': self.deposit_uid},
        )

    def _get_declaration_details(self):
        """ Second step: get info of a single declaration/interchange. """
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return self._get_fr_webservice_answer(
            url=ENDPOINT + "/api/l10n_fr_aspone/1/get_declaration_details",
            params={'db_uuid': db_uuid, 'declaration_uid': self.declaration_uid},
        )
