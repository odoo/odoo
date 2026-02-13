import logging

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

from ..tools import (
    _mer_api_query_inbox,
    _mer_api_query_document_process_status_outbox,
    _mer_api_query_document_process_status_inbox,
    _mer_api_check_fiscalization_status_outbox,
    _mer_api_check_fiscalization_status_inbox,
    _mer_api_receive_document,
    _mer_api_notify_import,
    MojEracunServiceError,
)

BATCH_SIZE = 50
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_hr_mer_username = fields.Char("MojEracun username", groups="account.group_account_manager")
    l10n_hr_mer_password = fields.Char("MojEracun password", groups="account.group_account_manager")
    l10n_hr_mer_company_ident = fields.Char("MojEracun CompanyId", groups="account.group_account_manager")
    l10n_hr_mer_software_ident = fields.Char("MojEracun SoftwareId", default='Saodoo-001', help="Default SoftwareID for Odoo is 'Saodoo-001'")
    l10n_hr_mer_connection_state = fields.Selection(
        selection=[
            ('inactive', 'Inactive'),
            ('active', 'Active'),
        ],
        string='MojEracun connection status',
        required=True,
        default='inactive',
        compute='_compute_l10n_hr_mojeracun_state',
        store=True,
    )
    l10n_hr_mer_connection_mode = fields.Selection(
        selection=[
            ('prod', 'Production'),
            ('test', 'Test'),
            ('demo', 'Demo'),
        ],
        string='MojEracun Operating mode',
        default='test',
    )
    l10n_hr_mer_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='eracun Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_l10n_hr_mer_purchase_journal_id', store=True, readonly=False,
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('l10n_hr_mer_purchase_journal_id')
    def _check_l10n_hr_mer_purchase_journal_id(self):
        for company in self:
            if company.l10n_hr_mer_purchase_journal_id and company.l10n_hr_mer_purchase_journal_id.type != 'purchase':
                raise ValidationError(self.env._("A purchase journal must be used to receive eRacun document via MojEracun."))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_hr_mer_connection_state')
    def _compute_l10n_hr_mer_purchase_journal_id(self):
        for company in self:
            if not company.l10n_hr_mer_purchase_journal_id and company.l10n_hr_mer_connection_state == 'active':
                company.l10n_hr_mer_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                ], limit=1)
            else:
                company.l10n_hr_mer_purchase_journal_id = company.l10n_hr_mer_purchase_journal_id

    @api.depends('l10n_hr_mer_username', 'l10n_hr_mer_password')
    def _compute_l10n_hr_mojeracun_state(self):
        for company in self:
            if any(not field for field in [
                company.l10n_hr_mer_username,
                company.l10n_hr_mer_password,
            ]):
                company.l10n_hr_mer_connection_state = 'inactive'

    # -------------------------------------------------------------------------
    # MOJERACUN PARTICIPANT MANAGEMENT
    # -------------------------------------------------------------------------

    def _l10n_hr_activate_mojeracun(self):
        for company in self:
            if company.l10n_hr_mer_username and company.l10n_hr_mer_password:
                company.l10n_hr_mer_connection_state = 'active'

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_mer_get_new_documents(self):
        edi_user_companies = self.search([('l10n_hr_mer_connection_state', '=', 'active')])
        for company in edi_user_companies:
            company._l10n_hr_mer_get_new_documents(from_cron=True)

    def _cron_mer_update_document_status(self):
        edi_user_companies = self.search([('l10n_hr_mer_connection_state', '=', 'active')])
        for company in edi_user_companies:
            company._l10n_hr_mer_fetch_document_status_company(from_cron=True)

    def _cron_mer_archive_signed_xmls(self):
        edi_user_companies = self.search([('l10n_hr_mer_connection_state', '=', 'active')])
        for company in edi_user_companies:
            company._l10n_hr_mer_archive_signed_xmls(from_cron=True)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _l10n_hr_mer_import_invoice(self, attachment, document):
        """
        Save new documents in an accounting journal, when one is specified on the company.
        If the document is not an invoice but a rejection notice, log a note on the related move instead.
        :param attachment: the new document
        :param document: a dictionary of MER and fiscalization related values for the document
        :return: `True` if the document was saved, `False` if it was not
        """
        self.ensure_one()
        original_document_id = self.env['account.edi.xml.ubl_hr']._retrieve_rejection_reference(attachment)
        if original_document_id == 'not_found':
            _logger.error("Failed to find origin document for rejection note %s", document['mer_document_eid'])
            return False
        elif original_document_id:
            original_addendum = self.env['l10n_hr_edi.addendum'].search([
                ('mer_document_eid', '=', original_document_id[0]),
                ('business_document_status', '!=', '1'),
                ('move_id.company_id', '=', self.id)], limit=1)
            if original_addendum:
                original_addendum.move_id.message_post(body=self.env._(
                    "eRacun rejected by document with Electronic ID: %(eid)s\n\"%(reason)s\"",
                    eid=document['mer_document_eid'], reason=original_document_id[1]))
                original_addendum.business_document_status = '1'
            return True
        journal = self.l10n_hr_mer_purchase_journal_id
        if not journal:
            return False

        move = self.env['account.move'].create({
            'state': 'draft',
            'journal_id': journal.id,
            'move_type': 'in_invoice',
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        move.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({'move_id': move.id, **document})
        move._extend_with_attachments(move._to_files_data(attachment), new=True)
        move._message_log(
            body=self.env._(
                "eRacun document (ElectroicId: %(electronic_id)s) has been received from MojEracun successfully.",
                electronic_id=document['mer_document_eid'],
            ),
            attachment_ids=attachment.ids,
        )
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        _logger.info("Successfully imported MER document %s", document['mer_document_eid'])
        return move

    def _l10n_hr_mer_get_new_documents(self, undelivered_only=True, slc=False, from_cron=False):
        """
        Import documents from MojEracun. Additional arguments included for testing.
        :param undelivered_only (bool, optional): Import only undelivered documents. Defaults to True.
        :param slc (tuple of two ints, optional): Import only a slice of the list of documents for testing. Defaults to False.
        """
        job_count = self.env.context.get('mer_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        imported_documents = {}
        for company in self.filtered(lambda c: c.l10n_hr_mer_connection_state == 'active'):
            try:
                response = _mer_api_query_inbox(company, 'Undelivered' if undelivered_only else None)
            except MojEracunServiceError as e:
                _logger.error('MojEracun service error: %s', e.message)
                continue

            error = False
            if isinstance(response, list):
                if not len(response):
                    # Case 1: empty list - no documents in the inbox
                    _logger.info("MojEracun inbox is empty for company: %s", company.name)
                    continue
                elif any(not (item.get('ElectronicId') and item.get('StatusId')) for item in response):
                    # Case 2: a list with elements that appear to not be valid document dicts
                    error = ("Incorrect multiple document response format while querying inbox for company: %s", company.name)
                else:
                    # Case 3: a list of valid document dicts
                    pass
            elif isinstance(response, dict):
                if not (response.get('ElectronicId') and response.get('StatusId')):
                    # Case 4: a single dict that doesn't appear to be a valid document
                    error = ("Incorrect multiple document response format while querying inbox for company: %s", company.name)
                else:
                    # Case 5: a single valid document dict
                    response = [response]
            else:
                # Case 6: unrecognizeable response
                error = ("Incorrect response format while querying inbox for company: %s", company.name)
            if error:
                if from_cron:
                    _logger.error("MojEracun service error: %s", error)
                    continue
                else:
                    raise MojEracunServiceError('service_error', error)
            documents = [{'mer_document_eid': str(document['ElectronicId']), 'mer_document_status': str(document['StatusId'])} for document in response][::-1]
            if not documents:
                continue

            need_retrigger = need_retrigger or len(documents) > job_count
            documents = documents[:job_count]

            existing_documents = self.env['l10n_hr_edi.addendum'].search([
                ("mer_document_eid", "in", [i['mer_document_eid'] for i in documents]),
                ('move_id.company_id', '=', company.id)])
            documents_to_import = [i for i in documents if i['mer_document_eid'] not in existing_documents.mapped('mer_document_eid')]
            proxy_acks = []
            # Retrieve attachments for the document IDs received
            if slc:
                documents_to_import = documents_to_import[slc[0]:slc[1]]
            for document in documents_to_import:
                try:
                    fisc_data = _mer_api_check_fiscalization_status_inbox(company, electronic_id=document['mer_document_eid'])
                    if fisc_data == []:
                        _logger.info("Fiscalization data for document eID %s is not available on MojEracun server.", document['mer_document_eid'])
                    else:
                        fisc_data = fisc_data[0]
                except (MojEracunServiceError, UserError):
                    _logger.error("Failed to retreive fisc data for document eID %s", document['mer_document_eid'])
                    if from_cron:
                        continue
                    elif company.l10n_hr_mer_connection_mode == 'test':
                        # Bypassing randomness of MER test server responce
                        fisc_data = {'messages': [{
                                'status': '0',
                                'errorCode': None,
                                'errorCodeDescription': 'Nema greške',
                                'fiscalizationRequestId': '00001-test',
                                'businessStatusReason': None,
                            }],
                            'channelType': '0',
                        }
                    else:
                        raise
                if fisc_data:
                    document.update({
                        'fiscalization_status': str(fisc_data['messages'][-1].get('status')),
                        'fiscalization_error': str(fisc_data['messages'][-1].get('errorCode')) + ' - ' + str(fisc_data['messages'][-1].get('errorCodeDescription')),
                        'fiscalization_request': str(fisc_data['messages'][-1].get('fiscalizationRequestId')),
                        'business_status_reason': str(fisc_data['messages'][-1].get('businessStatusReason')),
                        'fiscalization_channel_type': str(fisc_data.get('channelType')),
                    })
                    if document['fiscalization_status'] != '0':
                        _logger.warning("Document eID %s is not successfully fiscalized by MojEracun.", document['mer_document_eid'])
                try:
                    business_data = _mer_api_query_document_process_status_inbox(company, electronic_id=document['mer_document_eid'])[0]
                except (MojEracunServiceError, UserError):
                    _logger.error("Failed to retreive business data for document: %s", document['mer_document_eid'])
                    if from_cron:
                        continue
                    elif company.l10n_hr_mer_connection_mode == 'test':
                        # Bypassing randomness of MER test server responce
                        business_data = {
                            'DocumentProcessStatusId': '0',
                        }
                    else:
                        raise
                document.update({
                    'business_document_status': str(business_data.get('DocumentProcessStatusId')),
                })
                try:
                    document_xml = _mer_api_receive_document(company, document['mer_document_eid'])
                except MojEracunServiceError as e:
                    _logger.error("Failed to retrieve document: %s", e.message)
                    continue

                attachment = self.env["ir.attachment"].create(
                    {
                        "name": f"mojeracun_{document['mer_document_eid']}_attachment.xml",
                        "raw": document_xml,
                        "type": "binary",
                        "mimetype": "application/xml",
                    }
                )
                if self._l10n_hr_mer_import_invoice(attachment, document):
                    # Only acknowledge on successful import
                    proxy_acks.append(document['mer_document_eid'])
                if not tools.config['test_enable']:
                    self.env.cr.commit()
                    _mer_api_notify_import(company, document['mer_document_eid'])

            imported_documents.update({company.id: proxy_acks})
        if need_retrigger:
            self.env.ref('l10n_hr_edi.ir_cron_mer_get_new_documents')._trigger()
        # Return the documents that were successfully imported
        return imported_documents

    def _l10n_hr_mer_fetch_document_status_company(self, from_cron=False):
        """
        Fetch and update the status of up to 20000 documents belonging to a company on MojEracun.
        """
        for company in self.filtered(lambda c: c.l10n_hr_mer_connection_state == 'active'):
            for query_function, check_function in [
                (_mer_api_query_document_process_status_outbox, _mer_api_check_fiscalization_status_outbox),
                (_mer_api_query_document_process_status_inbox, _mer_api_check_fiscalization_status_inbox)
            ]:
                response_mer = query_function(company, by_update_date=True)
                documents = {
                    str(item['ElectronicId']): {
                        'mer_document_status': str(item.get('StatusId')),
                        'business_document_status': str(item.get('DocumentProcessStatusId')),
                    } for item in response_mer
                }
                try:
                    response_fisc = check_function(company)
                except (MojEracunServiceError, UserError):
                    _logger.error("Failed to retreive fiscalization data for company %s", company.name)
                    if from_cron or company.l10n_hr_mer_connection_mode == 'test':
                        response_fisc = []
                    else:
                        raise
                for item in response_fisc:
                    # As we can't fetch all the data with a single query, it's either this or making calls move-by-move
                    # Currently, because of the random nature of responses received from fisc endpoints, this breaks tests
                    if item.get('ElectronicId') in documents:
                        documents[item['ElectronicId']].update({
                            'fiscalization_status': str(item['messages'][-1].get('status')),
                            'fiscalization_error': str(item['messages'][-1].get('errorCode')) + ' - ' + str(item['messages'][-1].get('errorCodeDescription')),
                            'fiscalization_request': str(item['messages'][-1].get('fiscalizationRequestId')),
                            'business_status_reason': str(item['messages'][-1].get('fiscalizationRequestId')),
                            'fiscalization_channel_type': str(item.get('channelType')),
                        })
                addendums = self.env['l10n_hr_edi.addendum'].search([
                    ("mer_document_eid", "in", list(documents.keys())),
                    ('move_id.company_id', '=', company.id),
                ])
                for addendum in addendums:
                    addendum.write(documents[addendum.mer_document_eid])

    def _l10n_hr_mer_archive_signed_xmls(self, from_cron=False):
        """
        Download and archive signed XMLs for sent invoices that haven't been archived yet.
        :param company: The company record
        :param from_cron: If True, continue on errors instead of raising
        """
        moves = self.env['l10n_hr_edi.addendum'].search([
            ('mer_signed_xml_archived', '=', False),
            ('mer_document_eid', '!=', False),
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.company_id', '=', self.id),
        ]).mapped('move_id')
        for move in moves:
            try:
                signed_xml = _mer_api_receive_document(self, move.l10n_hr_mer_document_eid)
            except MojEracunServiceError as e:
                _logger.error("Failed to archive signed XML for %s: %s", move.l10n_hr_mer_document_eid, e.message)
                if not from_cron:
                    raise
                continue
            except UserError as e:
                _logger.error("Failed to archive signed XML for %s: %s", move.l10n_hr_mer_document_eid, str(e))
                if not from_cron:
                    raise
                continue
            attachment = self.env["ir.attachment"].create({
                "name": f"{move.name.replace('/', '_')}_signed.xml",
                "raw": signed_xml,
                "type": "binary",
                "mimetype": "application/xml",
                "res_model": "account.move",
                "res_id": move.id,
                "description": f"Signed XML from MojEracun (ElectronicId: {move.l10n_hr_mer_document_eid})",
            })
            move.l10n_hr_edi_addendum_id.mer_signed_xml_archived = True
            move._message_log(
                body=self.env._(
                    "Successfully archived signed XML for eRacun document (ElectroicId: %(eid)s)",
                    eid=move.l10n_hr_mer_document_eid,
                ),
                attachment_ids=attachment.ids,
            )
