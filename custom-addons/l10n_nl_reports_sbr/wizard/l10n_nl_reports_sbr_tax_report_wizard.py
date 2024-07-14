from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.misc import format_date

import json
import os
import re
import requests
import uuid
import xmlsec
from cryptography.hazmat.primitives.serialization import Encoding
from tempfile import NamedTemporaryFile
from odoo.tools import zeep
from odoo.tools.zeep import Client, wsse, wsa
from odoo.tools.zeep.exceptions import Fault
from lxml import etree
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from OpenSSL import crypto
from urllib3.util.ssl_ import create_urllib3_context
from urllib3.contrib.pyopenssl import inject_into_urllib3
from urllib3.connectionpool import HTTPSConnectionPool
from requests.exceptions import SSLError

server_leaf_cert = None

def _create_soap_client(wsdl_address, root_cert_file, client_cert, client_pkey):
    # The Zeep module uses a Client which will handle the creation and signature of the SOAP message sent to the government system.
    try:
        session = requests.Session()
        session.mount('https://', MemoryCertificateAndKeyHTTPAdapter())
        session.cert = (client_cert, client_pkey)
        session.verify = root_cert_file.name
        signature = BinarySignatureTimestamp(client_pkey, client_cert)
        plugins = [WsaSBR()]
        return Client(wsdl_address, wsse=signature, session=session, plugins=plugins)
    except SSLError as e:
        # The certificate was not accepted by the government server
        raise UserError(_("An error occured while using your certificate. Please verify the certificate you uploaded and try again.")) from e

def _sign_envelope_with_key_binary(envelope, key):
    """ Modifies the signature of the envelope to match the Dutch government system specification.
        Basically a copy of the original code from the zeep library with some adjustments.
    """
    security, sec_token_ref, x509_data = _signature_prepare(envelope, key)
    ref = etree.SubElement(sec_token_ref, etree.QName(zeep.ns.WSSE, 'Reference'),
                           {'ValueType': 'http://docs.oasis-open.org/wss/2004/01/'
                                         'oasis-200401-wss-x509-token-profile-1.0#X509v3'})
    ref_id = wsse.utils.get_unique_id()
    ref.set('URI', '#' + ref_id)
    bintok = etree.Element(etree.QName(zeep.ns.WSSE, 'BinarySecurityToken'), {
        etree.QName(zeep.ns.WSU, 'Id'): ref_id,
        'ValueType': 'http://docs.oasis-open.org/wss/2004/01/'
                     'oasis-200401-wss-x509-token-profile-1.0#X509v3',
        'EncodingType': 'http://docs.oasis-open.org/wss/2004/01/'
                        'oasis-200401-wss-soap-message-security-1.0#Base64Binary'})
    bintok.text = x509_data.find(etree.QName(zeep.ns.DS, 'X509Certificate')).text
    security.insert(0, bintok)
    x509_data.getparent().remove(x509_data)

def _signature_prepare(envelope, key):
    """ Prepare the envelope and sign.
        Basically a copy of the original code from the zeep library with some adjustments.
    """
    soap_env = wsse.signature.detect_soap_env(envelope)

    # Create the Signature node.
    signature = xmlsec.template.create(
        envelope,
        xmlsec.Transform.EXCL_C14N,
        xmlsec.Transform.RSA_SHA1,
    )

    key_info = xmlsec.template.ensure_key_info(signature)
    x509_data = xmlsec.template.add_x509_data(key_info)
    xmlsec.template.x509_data_add_issuer_serial(x509_data)
    xmlsec.template.x509_data_add_certificate(x509_data)

    security = wsse.utils.get_security_header(envelope)
    security.insert(0, signature)

    ctx = xmlsec.SignatureContext()
    ctx.key = key
    header = envelope.find(etree.QName(soap_env, 'Header'))
    wsse.signature._sign_node(ctx, signature, envelope.find(etree.QName(soap_env, 'Body')))
    wsse.signature._sign_node(ctx, signature, security.find(etree.QName(zeep.ns.WSU, 'Timestamp')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'Action')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'MessageID')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'To')))
    wsse.signature._sign_node(ctx, signature, header.find(etree.QName(zeep.ns.WSA, 'ReplyTo')))
    ctx.sign(signature)

    sec_token_ref = etree.SubElement(
        key_info, etree.QName(zeep.ns.WSSE, 'SecurityTokenReference'))
    return security, sec_token_ref, x509_data


class PatchedHTTPSConnectionPool(HTTPSConnectionPool):
    def _make_request(
        self, conn, method, url, timeout=object(), chunked=False, **httplib_request_kw
    ):
        # OVERRIDE
        # We want to store the certificate we get from the server at the moment of the handshake (and after verificiation)
        # as we want to use it further in the process (for signature verification).
        httplib_response = super()._make_request(
            conn=conn,
            method=method,
            url=url,
            timeout=timeout,
            chunked=chunked,
            **httplib_request_kw
        )
        # pylint: disable=global-statement
        global server_leaf_cert
        server_leaf_cert = conn.sock.connection.get_peer_certificate().to_cryptography().public_bytes(Encoding.PEM)
        return httplib_response

class MemoryCertificateAndKeyHTTPAdapter(requests.adapters.HTTPAdapter):
    """ This adapter allows the use of in-memory cert and key, as we want to load them not as files, but from database. """

    def init_poolmanager(self, *args, **kwargs):
        # We need inject_into_urllib3 as it forces the adapter to use PyOpenSSL.
        # With PyOpenSSL, we can further patch the code to make it do what we want (with the use of SSLContext).
        inject_into_urllib3()
        kwargs["ssl_context"] = create_urllib3_context()
        return super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        # OVERRIDE
        # The original method wants to check for an existing file
        # at the cert location. As we use in-memory objects,
        # we skip the check and assign it manually.
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = None

    def get_connection(self, url, proxies=None):
        # OVERRIDE
        # Patch the OpenSSLContext to decode the certificate in-memory.
        self.poolmanager.pool_classes_by_scheme['https'] = PatchedHTTPSConnectionPool
        connection = super().get_connection(url, proxies=proxies)
        context = connection.conn_kw['ssl_context']

        def patched_load_cert_chain(certfile, keyfile=None, password=None):
            context._ctx.use_certificate(crypto.load_certificate(crypto.FILETYPE_PEM, certfile[0]))
            context._ctx.use_privatekey(crypto.load_privatekey(crypto.FILETYPE_PEM, certfile[1]))

        context.load_cert_chain = patched_load_cert_chain
        return connection

class BinarySignatureTimestamp(wsse.signature.BinarySignature):
    """
        This signature use in-memory certificate and private key
        and applies a different timestamp and modified signature format.
    """
    def __init__(
        self,
        key_file,
        certfile,
        password=None,
    ):
        # The init method from BinarySignature wants filepath, not stored-in-memory values.
        # The alternative to keep using in-memory certificate and key is with MemorySignature.
        # pylint: disable=super-init-not-called
        # pylint: disable=non-parent-init-called
        wsse.signature.MemorySignature.__init__(
            self,
            key_file,
            certfile,
            password,
        )

    def apply(self, envelope, headers):
        # OVERRIDE
        # Change the timestamp format and apply the new signature
        security = wsse.utils.get_security_header(envelope)

        created = datetime.utcnow()
        expired = created + timedelta(seconds=10 * 60)

        timestamp = wsse.utils.WSU('Timestamp')
        timestamp.append(wsse.utils.WSU('Created', created.isoformat()+'Z'))
        timestamp.append(wsse.utils.WSU('Expires', expired.isoformat()+'Z'))

        security.append(timestamp)

        key = wsse.signature._make_sign_key(self.key_data, self.cert_data, self.password)
        _sign_envelope_with_key_binary(envelope, key)

        return envelope, headers

    def verify(self, envelope):
        # Verify the server message signature with the server certificate that we grabbed during the first handshake.
        key = wsse.signature._make_verify_key(server_leaf_cert)
        soap_env = wsse.signature.detect_soap_env(envelope)

        header = envelope.find(etree.QName(soap_env, 'Header'))
        if header is None:
            raise wsse.signature.SignatureVerificationFailed()

        security = header.find(etree.QName(zeep.ns.WSSE, 'Security'))
        if security is None and envelope.find(etree.QName(soap_env, "Body")) and envelope.find(etree.QName(soap_env, "Body")).find(etree.QName(soap_env, "Fault")):
            # In case of a Fault response, the message is not signed. If the message contains the Fault tag, then the signature verification is skipped.
            return envelope
        signature = security.find(etree.QName(zeep.ns.DS, 'Signature'))

        ctx = xmlsec.SignatureContext()

        # Find each signed element and register its ID with the signing context.
        refs = signature.iterfind('ds:SignedInfo/ds:Reference', namespaces={'ds': zeep.ns.DS})
        for ref in refs:
            # Get the reference URI and cut off the initial '#'
            referenced_id = ref.get('URI')[1:]
            referenced = envelope.find(".//*[@wsu:Id='%s']" % referenced_id, namespaces={'wsu': zeep.ns.WSU})
            ctx.register_id(referenced, 'Id', zeep.ns.WSU)

        ctx.key = key

        try:
            ctx.verify(signature)
        except xmlsec.Error:
            raise wsse.signature.SignatureVerificationFailed()
        return envelope

class WsaSBR(wsa.WsAddressingPlugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        # The Dutch government wants an additional address in the envelope header
        senvelope, shttp_headers = super().egress(envelope, http_headers, operation, binding_options)
        header = zeep.wsdl.utils.get_or_create_header(senvelope)
        header.extend([wsa.WSA.ReplyTo(wsa.WSA.Address('http://www.w3.org/2005/08/addressing/anonymous'))])
        return senvelope, shttp_headers

class L10nNlTaxReportSBRWizard(models.TransientModel):
    _name = 'l10n_nl_reports_sbr.tax.report.wizard'
    _description = 'L10n NL Tax Report for SBR Wizard'

    def _get_default_initials(self):
        user_name = self.env.user.name
        return ''.join([name[0].upper() for name in re.split(r"[- ']", user_name)])

    def _get_default_infix(self):
        # The infix is the "little names" in-between the surname and last name (typically "van de")
        user_name = self.env.user.name
        user_names = user_name.split()
        return ' '.join(user_names[1:-1]) if len(user_names) > 2 else False

    date_from = fields.Date(string="Period Starting Date")
    date_to = fields.Date(string="Period Ending Date")
    can_report_be_sent = fields.Boolean(compute='_compute_sending_conditions')

    contact_initials = fields.Char(string="Contact Initials", default=_get_default_initials)
    contact_prefix = fields.Char(string="Contact Name Infix", default=_get_default_infix)
    contact_surname = fields.Char(string="Contact Last Name", default=lambda self: self.env.user.name.split()[-1])
    contact_phone = fields.Char(string="Contact Phone", default=lambda self: self.env.user.phone)
    contact_type = fields.Selection([('BPL', 'Taxpayer (BPL)'), ('INT', 'Intermediary (INT)')], string="Contact Type", default='BPL', required=True,
        help="BPL: if the taxpayer files a turnover tax return as an individual entrepreneur."
        "INT: if the turnover tax return is made by an intermediary.")
    tax_consultant_number = fields.Char(string="Tax Consultant Number", help="The tax consultant number of the office aware of the content of this report.")
    password = fields.Char(string="Certificate or private key password", help="The password is not needed for just printing the XBRL file.")
    is_test = fields.Boolean(string="Is Test", help="Check this if you want the system to use the pre-production environment with test certificates.")

    @api.depends('date_to', 'date_from', 'is_test')
    def _compute_sending_conditions(self):
        for wizard in self:
            wizard.can_report_be_sent = wizard.is_test or \
                wizard.env.company.tax_lock_date and wizard.env.company.tax_lock_date >= wizard.date_to \
                and (
                    not wizard.env.company.l10n_nl_reports_sbr_last_sent_date_to\
                    or wizard.date_from > wizard.env.company.l10n_nl_reports_sbr_last_sent_date_to\
                    or wizard.date_to < wizard.env.company.l10n_nl_reports_sbr_last_sent_date_to + relativedelta(months=1)  # Users can send their report multiple times: the newest submission will replace the older ones.
                )

    def _check_values(self):
        if self.env.company.account_representative_id:
            if not self.env.company.account_representative_id.vat:
                raise RedirectWarning(
                    _('Your Accounting Firm does not have a VAT set. Please set it up before trying to send the report.'),
                    self.env.ref('base.action_res_company_form'),
                    _('Company settings')
                )
        elif not self.env.company.vat:
            raise RedirectWarning(
                _('Your company does not have a VAT set. Please set it up before trying to send the report.'),
                self.env.ref('base.action_res_company_form'),
                _('Company settings')
            )

    def _get_sbr_identifier(self):
        return self.env.company.vat[2:] if self.env.company.vat.startswith('NL') else self.env.company.vat

    def _additional_processing(self, options, kenmerk, closing_move):
        # TO BE OVERRIDEN by additional service(s)
        pass

    def action_download_xbrl_file(self):
        options = self.env.context['options']
        options['codes_values'] = self._generate_general_codes_values(options)
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xbrl',
            }
        }

    def send_xbrl(self):
        # Send the XBRL file to the government with the use of a Zeep client.
        # The wsdl address points to a wsdl file on the government server.
        # It contains the definition of the 'aanleveren' function, which actually sends the message.
        options = self.env.context['options']
        report_handler = self.env['l10n_nl.tax.report.handler']
        closing_move = report_handler._get_tax_closing_entries_for_closed_period(self.env.ref('account.generic_tax_report'), options, self.env.company, posted_only=False)
        if not self.is_test:
            if not closing_move:
                raise RedirectWarning(
                    _('No Closing Entry was found for the selected period. Please create one and post it before sending your report.'),
                    self.env.ref('l10n_nl_reports_sbr.action_open_closing_entry').id,
                    _('Create Closing Entry'),
                    {'options': options},
                )
            if closing_move.state == 'draft':
                raise RedirectWarning(
                    _('The Closing Entry for the selected period is still in draft. Please post it before sending your report.'),
                    self.env.ref('l10n_nl_reports_sbr.action_open_closing_entry').id,
                    _('Closing Entry'),
                    {'options': options},
                )
        options['codes_values'] = self._generate_general_codes_values(options)
        xbrl_data = report_handler.export_tax_report_to_xbrl(options)
        report_file = xbrl_data['file_content']

        serv_root_cert = self.env.company._l10n_nl_get_server_root_certificate_bytes()
        certificate, private_key = self.env.company._l10n_nl_get_certificate_and_key_bytes(bytes(self.password or '', 'utf-8') or None)
        try:
            with NamedTemporaryFile(delete=False) as f:
                f.write(serv_root_cert)
            wsdl = 'https://' + ('preprod-' if self.is_test else '') + 'dgp2.procesinfrastructuur.nl/wus/2.0/aanleverservice/1.2?wsdl'
            delivery_client = _create_soap_client(wsdl, f, certificate, private_key)
            factory = delivery_client.type_factory('ns0')
            aanleverkenmerk = wsse.utils.get_unique_id()

            response = delivery_client.service.aanleveren(
                berichtsoort='Omzetbelasting',
                aanleverkenmerk=aanleverkenmerk,
                identiteitBelanghebbende=factory.identiteitType(nummer=self._get_sbr_identifier(), type='BTW'),
                rolBelanghebbende='Bedrijf',
                berichtInhoud=factory.berichtInhoudType(mimeType='application/xml', bestandsnaam='TaxReport.xbrl', inhoud=report_file),
                autorisatieAdres='http://geenausp.nl',
            )
            kenmerk = response.kenmerk
        except Fault as fault:
            detail_fault = fault.detail.getchildren()[0]
            raise RedirectWarning(
                message=_("The Tax Services returned the error hereunder. Please upgrade your module and try again before submitting a ticket.") + "\n\n" + detail_fault.find("fault:foutbeschrijving", namespaces={**fault.detail.nsmap, **detail_fault.nsmap}).text,
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_nl_reports_sbr',
                    'search_default_extra': True,
                },
            )
        finally:
            os.unlink(f.name)

        if not self.is_test:
            self.env.company.l10n_nl_reports_sbr_last_sent_date_to = self.date_to
            subject = _("Tax report sent")
            body = _(
                "The tax report from %s to %s was sent to Digipoort.<br/>We will post its processing status in this chatter once received.<br/>Discussion id: %s",
                format_date(self.env, self.date_from),
                format_date(self.env, self.date_to),
                kenmerk,
            )
            filename = f'tax_report_{self.date_to.year}_{self.date_to.month}.xbrl'
            closing_move.with_context(no_new_invoice=True).message_post(subject=subject, body=body, attachments=[(filename, report_file)])
            closing_move.message_subscribe(partner_ids=[self.env.user.id])

        self._additional_processing(options, kenmerk, closing_move)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sending your report'),
                'type': 'success',
                'message': _("Your tax report is being sent to Digipoort. Check its status in the closing entry's chatter."),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _generate_general_codes_values(self, options):
        self._check_values()
        report = self.env['account.report'].browse(options['report_id'])
        vat = report.get_vat_for_export(options)
        return {
            'identifier': self._get_sbr_identifier() or (vat[2:] if vat.startswith('NL') else vat),
            'startDate': fields.Date.to_string(self.date_from),
            'endDate': fields.Date.to_string(self.date_to),
            'ContactInitials': self.contact_initials or '',
            'ContactPrefix': self.contact_prefix,
            'ContactSurname': self.contact_surname,
            'ContactTelephoneNumber': re.sub(r"[^\+\d]", "", self.contact_phone or ''),
            'ContactType': self.contact_type,
            'DateTimeCreation': fields.Datetime.now().strftime("%Y%m%d%H%M"),
            'MessageReferenceSupplierVAT': ((self.env.company.account_representative_id.vat or vat) + '-' + str(uuid.uuid4()))[:20],
            'ProfessionalAssociationForTaxServiceProvidersName': self.env.company.account_representative_id.name or '',
            'SoftwarePackageName': 'Odoo',
            'SoftwarePackageVersion': '.'.join(self.sudo().env.ref('base.module_base').latest_version.split('.')[0:3]),
            'SoftwareVendorAccountNumber': 'swo02770',
            'TaxConsultantNumber': self.tax_consultant_number,
        }
