# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import json
from ast import literal_eval
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from werkzeug.exceptions import NotFound

from asn1crypto import cms
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12, pkcs7
from cryptography.x509.oid import NameOID

from odoo.addons.base.tests.common import BaseCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import Response
from odoo.tests import new_test_user, tagged
from odoo.tools import BinaryBytes

from ..controllers.main import WebsiteEventWalletController


@tagged('post_install', '-at_install')
class TestEventWallet(BaseCommon):
    _test_user_groups = ('base.group_system', 'event.group_event_manager')

    @classmethod
    def setup_independent_company(cls):
        return cls.env['res.company'].create({'name': 'Wallet Test Company'})

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.website = cls.env['website'].create({
            'name': 'Wallet Website', 'company_id': cls.env.company.id,
        })
        cls.website.company_id.allow_add_to_wallet = True
        now = datetime.now(timezone.utc)
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Test WWDR')])
        cls.ca = (
            x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
            .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=90))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, 'Test Event Pass'),
            x509.NameAttribute(NameOID.USER_ID, 'pass.com.example.event'),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 'EXAMPLETEAM'),
        ])
        cls.leaf = (
            x509.CertificateBuilder().subject_name(subject).issuer_name(ca_name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=30))
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        bundle = pkcs12.serialize_key_and_certificates(
            b'Event pass', key, cls.leaf, [cls.ca], serialization.BestAvailableEncryption(b'test-password'),
        )
        cls.certificate = cls.env['certificate.certificate'].create({
            'name': 'Apple Wallet Test', 'company_id': cls.website.company_id.id,
            'scope': 'event', 'wallet_type': 'apple', 'content': BinaryBytes(bundle), 'pkcs12_password': 'test-password',
        })
        cls.event = cls.env['event.event'].create({
            'name': 'Wallet Test Event', 'company_id': cls.website.company_id.id,
            'website_id': cls.website.id,
            'date_begin': now.replace(tzinfo=None),
            'date_end': (now + timedelta(hours=2)).replace(tzinfo=None),
        })

    def test_imported_identity_signs_pass(self):
        self.assertTrue(self.certificate.private_key_id)
        self.assertTrue(self.certificate.issuer_cert_id)
        self.assertEqual(self.certificate.issuer_cert_id.scope, 'ca')
        self.assertTrue(self.certificate._is_wallet_certificate_ready('event'))
        self.assertEqual(self.website.company_id._get_available_wallet_providers(), ['apple'])
        wallet_pass = self.certificate._generate_wallet_event_pass({
            'event_name': 'Conference', 'attendee': 'Ada', 'ticket_type': 'General',
            'start': '2027-01-01T12:00:00+00:00', 'end': '2027-01-01T13:00:00+00:00',
            'barcode': '123456', 'registration_id': '42',
        }, provider_code='apple')
        wallet_pass = json.loads(json.dumps(wallet_pass))
        self.assertEqual(wallet_pass['mimetype'], 'application/vnd.apple.pkpass')
        self.assertEqual(wallet_pass['extension'], 'pkpass')
        payload = base64.b64decode(wallet_pass['content'], validate=True)
        with ZipFile(BytesIO(payload)) as archive:
            document = json.loads(archive.read('pass.json'))
            self.assertEqual(document['passTypeIdentifier'], 'pass.com.example.event')
            self.assertEqual(document['teamIdentifier'], 'EXAMPLETEAM')
            for name, digest in json.loads(archive.read('manifest.json')).items():
                self.assertEqual(hashlib.sha1(archive.read(name), usedforsecurity=False).hexdigest(), digest)
            signature = archive.read('signature')
            certificates = pkcs7.load_der_pkcs7_certificates(signature)
            self.assertEqual({cert.serial_number for cert in certificates}, {self.leaf.serial_number, self.ca.serial_number})
            self._assert_signed_manifest(signature, archive.read('manifest.json'))

    def _assert_signed_manifest(self, signature, manifest):
        signed_data = cms.ContentInfo.load(signature)['content']
        self.assertIsNone(signed_data['encap_content_info']['content'].native)
        signer = signed_data['signer_infos'][0]
        attributes = signer['signed_attrs']
        values = {attribute['type'].native: attribute['values'][0].native for attribute in attributes}
        self.assertEqual(values['message_digest'], hashlib.sha256(manifest).digest())
        self.assertIn('signing_time', values)
        self.leaf.public_key().verify(
            signer['signature'].native, attributes.untag().dump(),
            padding.PKCS1v15(), hashes.SHA256(),
        )

    def test_manifest_signing_uses_encrypted_odoo_key(self):
        key = self.certificate.private_key_id
        private_key = serialization.load_pem_private_key(key.pem_key.content, password=None)
        key.write({
            'content': BinaryBytes(private_key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.BestAvailableEncryption(b'odoo-key-password'),
            )),
            'password': 'odoo-key-password',
        })
        manifest = b'{"pass.json": "test-digest"}'
        self._assert_signed_manifest(self.certificate._sign_apple_wallet_manifest(manifest), manifest)

    def test_manifest_signing_rejects_issuer_identifier_fallback(self):
        wrong_issuer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        forged = (
            x509.CertificateBuilder().subject_name(self.leaf.subject).issuer_name(self.ca.subject)
            .public_key(self.leaf.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=30))
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.ca.public_key()), critical=False)
            .sign(wrong_issuer_key, hashes.SHA256())
        )
        self.certificate.write({
            'content': BinaryBytes(forged.public_bytes(serialization.Encoding.PEM)),
            'private_key_id': self.certificate.private_key_id.id,
        })
        self.assertEqual(self.certificate.issuer_cert_id.subject_common_name, 'Test WWDR')
        with self.assertRaises(UserError):
            self.certificate._generate_wallet_event_pass({
                'event_name': 'Conference', 'attendee': 'Ada', 'ticket_type': 'General',
                'start': '2027-01-01T12:00:00+00:00', 'end': '2027-01-01T13:00:00+00:00',
                'barcode': '123456', 'registration_id': '42',
            }, provider_code='apple')

    def test_provider_is_selected_by_current_website_company_and_code(self):
        controller = WebsiteEventWalletController()
        env = self.env

        class WebsiteEnvironment:
            website = self.website

            def __getitem__(self, name):
                return env[name]

        request = SimpleNamespace(env=WebsiteEnvironment())
        with patch('odoo.addons.website_event_wallet.controllers.main.request', request):
            self.assertEqual(controller._get_wallet_certificate(self.event, 'apple'), self.certificate)
            self.assertFalse(controller._get_wallet_certificate(self.event, 'unknown'))
            # Websites in the same company use that company's certificate.
            request.env.website = self.website.copy({'name': 'Another Website'})
            self.assertEqual(controller._get_wallet_certificate(self.event, 'apple'), self.certificate)
            # A different website company cannot sign this company's tickets.
            other_company = self.env['res.company'].create({'name': 'Other Wallet Company'})
            request.env.website = self.website.copy({'name': 'Other Company Website', 'company_id': other_company.id})
            self.assertFalse(controller._get_wallet_certificate(self.event, 'apple'))

    def test_scope_and_archived_certificate(self):
        self.certificate.scope = 'general'
        self.assertFalse(self.website.company_id._get_available_wallet_providers())
        self.certificate.scope = 'event'
        self.certificate.active = False
        self.assertFalse(self.certificate._is_wallet_certificate_ready('event'))
        with self.assertRaises(UserError):
            self.certificate._generate_wallet_event_pass({}, provider_code='apple')

    def test_event_pass_requires_wallet_type(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.certificate.wallet_type = False
        self.certificate.write({'scope': 'general', 'wallet_type': False})
        self.assertFalse(self.certificate.wallet_type)

    def test_other_wallet_types_are_selectable_but_not_implemented(self):
        for wallet_type in ('samsung', 'google'):
            with self.subTest(wallet_type=wallet_type):
                self.certificate.wallet_type = wallet_type
                self.assertFalse(self.website.company_id._get_available_wallet_providers())
                self.assertFalse(self.certificate._is_wallet_provider_certificate_ready('apple'))
                for provider_code in ('apple', wallet_type):
                    self.assertFalse(self.env['certificate.certificate']._get_wallet_certificate(
                        self.website.company_id, provider_code,
                    ))
                with self.assertRaisesRegex(UserError, 'Unsupported wallet provider: ' + wallet_type):
                    self.certificate._generate_wallet_event_pass({}, provider_code=wallet_type)
                with self.assertRaises(UserError):
                    self.certificate._generate_wallet_event_pass({}, provider_code='apple')

    def test_settings_action_uses_removable_event_filter(self):
        action = self.env.ref('website_event_wallet.certificate_event_pass_action')
        domain = literal_eval(action.domain)
        self.assertEqual(domain, [])
        context = literal_eval(action.context)
        self.assertEqual(context['search_default_scope_event'], 1)
        certificates = self.env['certificate.certificate'].search(domain)
        self.assertIn(self.certificate, certificates)
        self.certificate.scope = 'general'
        self.assertIn(self.certificate, self.env['certificate.certificate'].search(domain))
        self.assertEqual(literal_eval(action.context)['default_scope'], 'event')

    def test_additional_provider_uses_its_scope_without_apple_issuer(self):
        self.certificate.issuer_cert_id.unlink()
        self.certificate.invalidate_recordset(['issuer_cert_id'])
        self.certificate.scope = 'general'
        self.assertFalse(self.certificate.issuer_cert_id)
        self.assertTrue(self.certificate._is_wallet_certificate_ready('general'))
        self.assertFalse(self.certificate._is_wallet_certificate_ready('event'))

        self.certificate.write({'scope': 'event', 'wallet_type': 'google'})
        Certificate = type(self.certificate)
        get_provider_scopes = Certificate._get_wallet_provider_scopes

        def additional_provider_scopes(certificates, **kwargs):
            return {**get_provider_scopes(certificates, **kwargs), 'google': 'event'}

        with patch.object(Certificate, '_get_wallet_provider_scopes', additional_provider_scopes):
            self.assertEqual(self.website.company_id._get_available_wallet_providers(), ['google'])
            self.assertEqual(
                self.env['certificate.certificate']._get_wallet_certificate(self.website.company_id, 'google'),
                self.certificate,
            )
            self.assertFalse(self.certificate._is_wallet_provider_certificate_ready('unknown'))

    def test_apple_provider_still_requires_wwdr_issuer(self):
        self.certificate.issuer_cert_id.unlink()
        self.certificate.invalidate_recordset(['issuer_cert_id'])
        self.assertTrue(self.certificate._is_wallet_certificate_ready('event'))
        self.assertFalse(self.certificate._is_wallet_provider_certificate_ready('apple'))
        self.assertFalse(self.website.company_id._get_available_wallet_providers())
        with self.assertRaises(UserError):
            self.certificate._generate_wallet_event_pass({}, provider_code='apple')

    def test_unsupported_provider_does_not_report_apple_configuration(self):
        for active in (True, False):
            with self.subTest(active=active):
                self.certificate.active = active
                with self.assertRaisesRegex(UserError, 'Unsupported wallet provider: other_wallet') as error:
                    self.certificate._generate_wallet_event_pass({}, provider_code='other_wallet')
                self.assertNotIn('Apple', str(error.exception))

    def test_generation_requires_explicit_provider(self):
        with self.assertRaises(TypeError):
            self.certificate._generate_wallet_event_pass({})

    def test_provider_extension_accepts_keyword_options(self):
        Certificate = type(self.certificate)
        generate_apple_pass = Certificate._generate_apple_wallet_event_pass

        def generate_with_reference(certificate, event_data, *, reference, **kwargs):
            result = generate_apple_pass(certificate, event_data, **kwargs)
            result['reference'] = reference
            return result

        with patch.object(Certificate, '_generate_apple_wallet_event_pass', generate_with_reference):
            result = self.certificate._generate_wallet_event_pass({
                'event_name': 'Conference', 'attendee': 'Ada', 'ticket_type': 'General',
                'start': '2027-01-01T12:00:00+00:00', 'end': '2027-01-01T13:00:00+00:00',
                'barcode': '123456', 'registration_id': '42',
            }, provider_code='apple', reference='custom-ticket', code_type='barcode', lang='en_US')
        self.assertEqual(json.loads(json.dumps(result))['reference'], 'custom-ticket')
        with ZipFile(BytesIO(base64.b64decode(result['content'], validate=True))) as archive:
            document = json.loads(archive.read('pass.json'))
            self.assertEqual(document['barcodes'][0]['format'], 'PKBarcodeFormatCode128')

    def test_download_requires_valid_ticket_and_website(self):
        env = self.env
        controller = WebsiteEventWalletController()

        class WebsiteEnvironment:
            website = self.website

            def __getitem__(self, name):
                return env[name]

            def __getattr__(self, name):
                return getattr(env, name)

        registration = self.env['event.registration'].create({
            'name': 'Ada', 'event_id': self.event.id, 'state': 'open',
        })
        request = SimpleNamespace(
            env=WebsiteEnvironment(),
            make_response=lambda payload, headers: Response(payload, headers=headers),
        )
        ticket_hash = self.event._get_tickets_access_hash(registration.ids)
        with patch('odoo.addons.website_event_wallet.controllers.main.request', request):
            with self.assertRaises(NotFound):
                controller.registration_wallet(self.event.id, registration.id, 'apple', tickets_hash='invalid')
            with self.assertRaises(NotFound):
                controller.registration_wallet(self.event.id, registration.id + 1, 'apple', tickets_hash=ticket_hash)
            with self.assertRaises(NotFound):
                controller.registration_wallet(self.event.id, registration.id, 'unknown', tickets_hash=ticket_hash)
            response = controller.registration_wallet(
                self.event.id, registration.id, 'apple', tickets_hash=ticket_hash,
            )
            self.assertTrue(response.get_data().startswith(b'PK'))
            self.assertEqual(response.headers['Content-Type'], 'application/vnd.apple.pkpass')
            self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
            other_company = self.env['res.company'].create({'name': 'Wrong Company'})
            request.env.website = self.website.copy({'name': 'Wrong Website', 'company_id': other_company.id})
            with self.assertRaises(NotFound):
                controller.registration_wallet(self.event.id, registration.id, 'apple', tickets_hash=ticket_hash)

    def test_certificate_is_not_exposed_to_event_users(self):
        user = new_test_user(
            self.env, login='wallet_event_user', groups='event.group_event_user',
            company_id=self.website.company_id.id, company_ids=self.website.company_id.ids,
        )
        with self.assertRaises(AccessError):
            self.certificate.with_user(user).read(['content', 'private_key_id'])

    def test_settings_activate_wallet_for_company(self):
        settings = self.env['res.config.settings'].create({
            'company_id': self.website.company_id.id, 'allow_add_to_wallet': False,
        })
        self.assertFalse(self.website.company_id.allow_add_to_wallet)
        settings.allow_add_to_wallet = True
        self.assertTrue(self.website.company_id.allow_add_to_wallet)
