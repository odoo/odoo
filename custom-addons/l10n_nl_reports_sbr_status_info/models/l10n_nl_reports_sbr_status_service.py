from odoo import models, fields, _
from odoo.addons.l10n_nl_reports_sbr.wizard.l10n_nl_reports_sbr_tax_report_wizard import _create_soap_client
from datetime import timedelta
from tempfile import NamedTemporaryFile
from odoo.tools.zeep.exceptions import Fault
from requests.exceptions import ConnectionError

class L10nNlSBRStatusService(models.Model):
    _name = 'l10n_nl_reports_sbr.status.service'
    _description = 'Status checking service for Digipoort submission'

    kenmerk = fields.Char('Message Exchange ID')
    company_id = fields.Many2one('res.company', 'Company')
    report_name = fields.Char('Name of the submitted report')
    is_done = fields.Boolean('Is the cycle finished?', default=False)
    closing_entry_id = fields.Many2one('account.move', string='Related closing entry')
    is_test = fields.Boolean('Is it a test?')

    def _cron_process_submission_status(self):
        ongoing_processes = self.search([('is_done', '=', False)])
        if not ongoing_processes:
            return
        serv_root_cert = ongoing_processes[0].company_id._l10n_nl_get_server_root_certificate_bytes()   # The root certificate is the same for all processes
        with NamedTemporaryFile() as f:
            f.write(serv_root_cert)
            f.flush()

            for process in ongoing_processes:
                password = bytes(process.company_id.l10n_nl_reports_sbr_password or '', 'utf-8')
                certificate, private_key = process.company_id._l10n_nl_get_certificate_and_key_bytes(password or None)
                ongoing_processes_responses = {}
                wsdl = 'https://' + ('preprod-' if process.is_test else '') + 'dgp2.procesinfrastructuur.nl/wus/2.0/statusinformatieservice/1.2?wsdl'

                try:
                    delivery_client = _create_soap_client(wsdl, f, certificate, private_key)
                    ongoing_processes_responses[process] = delivery_client.service.getStatussenProces(
                        kenmerk=process.kenmerk,
                        autorisatieAdres='http://geenausp.nl',
                    )
                except Fault as fault:
                    detail_fault = fault.detail.getchildren()[0]
                    error_description = detail_fault.find("fault:foutbeschrijving", namespaces={**fault.detail.nsmap, **detail_fault.nsmap}).text
                    process.is_done = True
                    if not process.is_test:
                        subject = _("%s status retrieval failed", process.report_name)
                        body = _(
                            "The status retrieval for the %s with discussion id '%s' failed with the error:<br/><br/><i>%s</i><br/><br/>Try submitting your report again.",
                            process.report_name,
                            process.kenmerk,
                            error_description,
                        )
                        process.closing_entry_id.with_context(no_new_invoice=True).message_post(subject=subject, body=body, author_id=self.env.ref('base.partner_root').id, subtype_id=self.env.ref('mail.mt_comment').id)
                except ConnectionError:
                    # In case the server or the connection is not accessible at the moment,
                    # we'll just skip this process and trigger a new cron for later
                    pass

        for process, response in ongoing_processes_responses.items():
            for status in response:
                if status.statusFoutcode:
                    process.is_done = True
                    ongoing_processes -= process
                    if not process.is_test:
                        subject = _("%s submission failed", process.report_name)
                        body = _(
                            "The submission for the %s with discussion id '%s' failed with the error:<br/><br/><i>%s</i><br/><i>%s</i><br/><br/>Try submitting your report again.",
                            process.report_name,
                            process.kenmerk,
                            status.statusomschrijving,
                            status.statusFoutcode.foutbeschrijving,
                        )
                        process.closing_entry_id.with_context(no_new_invoice=True).message_post(subject=subject, body=body, author_id=self.env.ref('base.partner_root').id, subtype_id=self.env.ref('mail.mt_comment').id)
                    break
                if status.statuscode == '500':
                    # See "Statussenflow - Aanleverproces Belastingdienst": https://aansluiten.procesinfrastructuur.nl/site/binaries/content/assets/documentatie/statussen-en-foutcodes/illustraties/statussenflow-sbr-bd-aanleveren-wus12.png
                    process.is_done = True
                    ongoing_processes -= process
                    if not process.is_test:
                        subject = _("%s submission succeeded", process.report_name)
                        body = _(
                            "The submission for the %s with discussion id '%s' was successfully received by Digipoort.",
                            process.report_name,
                            process.kenmerk,
                        )
                        process.closing_entry_id.with_context(no_new_invoice=True).message_post(subject=subject, body=body, author_id=self.env.ref('base.partner_root').id, subtype_id=self.env.ref('mail.mt_comment').id)
                    break

        if ongoing_processes:
            # If there are still unfinished processes, we trigger a cron to check the status again in one minute
            statusinformatieservice_cron = self.env.ref('l10n_nl_reports_sbr_status_info.cron_l10n_nl_reports_status_process')
            statusinformatieservice_cron._trigger(fields.Datetime.now() + timedelta(minutes=1))

