import base64
from datetime import timedelta
from tempfile import NamedTemporaryFile

from markupsafe import Markup
from requests.exceptions import ConnectionError
from zeep.exceptions import Fault

from odoo import _, fields, models
from odoo.addons.l10n_nl_reports_sbr.wizard.l10n_nl_reports_sbr_tax_report_wizard import (
    _create_soap_client,
)


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
                cert_sudo = process.company_id.l10n_nl_reports_sbr_cert_id.sudo()
                cer_pem = base64.b64decode(cert_sudo.pem_certificate)
                key_pem = base64.b64decode(cert_sudo.private_key_id.pem_key)
                ongoing_processes_responses = {}
                wsdl = 'https://' + ('preprod-' if process.is_test else '') + 'dgp2.procesinfrastructuur.nl/wus/2.0/statusinformatieservice/1.2?wsdl'

                try:
                    delivery_client = _create_soap_client(wsdl, f, cer_pem, key_pem)
                    ongoing_processes_responses[process] = delivery_client.service.getStatussenProces(
                        kenmerk=process.kenmerk,
                        autorisatieAdres='http://geenausp.nl',
                    )
                except Fault as fault:
                    detail_fault = fault.detail.getchildren()[0]
                    error_description = detail_fault.find("fault:foutbeschrijving", namespaces={**fault.detail.nsmap, **detail_fault.nsmap}).text
                    process.is_done = True
                    if not process.is_test:
                        subject = _("%(report_name)s status retrieval failed") % {'report_name': process.report_name}
                        body = Markup(_(
                            "The status retrieval for the %(report_name)s with discussion id '%(id)s' failed with the error:<br/><br/><i>%(error)s</i><br/><br/>Try submitting your report again."
                            )) % {
                                'report_name': process.report_name,
                                'id': process.kenmerk,
                                'error': error_description,
                            }
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
                        subject = _("%(report_name)s submission failed") % {'report_name': process.report_name}
                        body = Markup(_(
                            "The submission for the %(report_name)s with discussion id '%(id)s' failed with the error:<br/><br/><i>%(error)s</i><br/><i>%(detailed_error)s</i><br/><br/>Try submitting your report again."
                            )) % {
                                'report_name': process.report_name,
                                'id': process.kenmerk,
                                'error': status.statusomschrijving,
                                'detailed_error': status.statusFoutcode.foutbeschrijving,
                            }
                        process.closing_entry_id.with_context(no_new_invoice=True).message_post(subject=subject, body=body, author_id=self.env.ref('base.partner_root').id, subtype_id=self.env.ref('mail.mt_comment').id)
                    break
                if status.statuscode == '500':
                    # See "Statussenflow - Aanleverproces Belastingdienst": https://aansluiten.procesinfrastructuur.nl/site/binaries/content/assets/documentatie/statussen-en-foutcodes/illustraties/statussenflow-sbr-bd-aanleveren-wus12.png
                    process.is_done = True
                    ongoing_processes -= process
                    if not process.is_test:
                        subject = _("%(report_name)s submission succeeded") % {'report_name': process.report_name}
                        body = Markup(_(
                            "The submission for the %(report_name)s with discussion id '%(id)s' was successfully received by Digipoort.",
                            )) % {
                                'report_name': process.report_name,
                                'id': process.kenmerk,
                            }
                        process.closing_entry_id.with_context(no_new_invoice=True).message_post(subject=subject, body=body, author_id=self.env.ref('base.partner_root').id, subtype_id=self.env.ref('mail.mt_comment').id)
                    break

        if ongoing_processes:
            # If there are still unfinished processes, we trigger a cron to check the status again in one minute
            statusinformatieservice_cron = self.env.ref('l10n_nl_reports_sbr_status_info.cron_l10n_nl_reports_status_process')
            statusinformatieservice_cron._trigger(fields.Datetime.now() + timedelta(minutes=1))
