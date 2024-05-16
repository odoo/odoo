# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from io import StringIO
from urllib.parse import urlparse, parse_qsl

from freezegun import freeze_time

from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.purchase.controllers.portal import (
    CustomerPortal,
    VERIFIED_SESSION_DURATION_S,
    MAX_CREATED_BANK_RECORDS,
)
from odoo.addons.purchase.models.purchase_order import VERIFICATION_URL_DURATION_S
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestPurchaseUploadBill(HttpCaseWithUserPortal, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.controller = CustomerPortal()

        cls.company_admin.allow_vendor_bill_upload = True

        cls.product = cls.env["product.product"].create(
            {
                "name": "Product",
                "standard_price": 10.0,
                "type": "service",
            }
        )

        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner_portal.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                        },
                    )
                ],
            }
        )

        cls.our_other_po = cls.po.copy()

        cls.bank_account = (
            cls.env["res.partner.bank"]
            .with_user(cls.user_portal)
            .sudo()
            .create(
                {
                    "acc_number": "1232135479",
                    "acc_holder_name": "holder name",
                    "partner_id": cls.partner_portal.id,
                    "bank_id": cls.env["res.bank"].create({"name": "bank name"}).id,
                }
            )
        )

        cls.our_ar_responsible_partner = cls.env["res.partner"].create(
            {"name": "our AR responsible", "parent_id": cls.partner_portal.id}
        )
        cls.our_ar_responsible_user = cls.user_portal.with_context(no_reset_password=True).copy(
            {"login": "ar_responsible", "password": "ar_responsible", "partner_id": cls.our_ar_responsible_partner.id}
        )

        cls.other_partner = cls.env["res.partner"].create({"name": "someone else"})
        cls.other_user = cls.user_portal.with_context(no_reset_password=True).copy(
            {"login": "portal2", "password": "portal2_pwd", "partner_id": cls.other_partner.id}
        )
        cls.someone_elses_po = cls.po.copy({"partner_id": cls.other_partner.id})
        cls.someone_elses_bank_account = cls.bank_account.with_user(cls.user_root).copy(
            {"partner_id": cls.other_partner.id, "acc_number": "9745312321"}
        )

    # Helper methods.
    def _reloaded_session_is_verified(self, partner, session):
        """New Session objects are created by _get_session_and_dbname() during url_open(). Existing in-memory
        sessions may not be up-to-date. The opposite problem happens when the session is modified by self.controller.
        To work around this, always force the session to be saved to disk. Ideally MockRequest's session would be used,
        but it's not compatible with url_open()."""
        session = http.root.session_store.get(session.sid)
        verified = self.controller._session_is_verified(self.company_admin, partner.commercial_partner_id, session=session)
        http.root.session_store.save(session)
        return verified

    def _create_verified_session(self, po, session, add_access_token=False, error_if_not_verified=True):
        """Simulates clicking on verification link emailed for the specified PO."""
        self.assertFalse(self._reloaded_session_is_verified(po.partner_id, session), "Session should not be verified.")

        url = self.po._portal_get_upload_bill_signed_url()
        if add_access_token:
            url += f"&access_token={po._portal_ensure_token()}"

        response = self.url_open(url)
        self.assertEqual(response.status_code, 200, "Loading the page should have succeeded.")

        if error_if_not_verified:
            self.assertTrue(self._reloaded_session_is_verified(po.partner_id, session), "Session should be verified.")

        return response

    def _generate_mock_pdf(self, file_name):
        return f"{file_name}.pdf", StringIO(f"{file_name} content."), "application/pdf"

    def _upload_bill(self, po=None, add_access_token=False):
        if not po:
            po = self.po

        data = {"csrf_token": http.Request.csrf_token(self), "bank_account": self.bank_account.id}
        files = {"bill_pdf": self._generate_mock_pdf("bill_pdf")}
        url = f"/my/purchase/{po.id}"

        if add_access_token:
            url += f"?access_token={po._portal_ensure_token()}"

        return self.url_open(url, data=data, files=files)

    def _get_session_verification_params(self):
        parsed = urlparse(self.po._portal_get_upload_bill_signed_url())
        return dict(parse_qsl(parsed.query))

    # Signature link tests.
    def test_purchase_order_session_verification_url(self):
        """Session verification URLs should be specific to a (partner, PO) combination."""
        params = self._get_session_verification_params()
        self.assertTrue(
            self.po._portal_verify_upload_bill_session(self.po.partner_id, **params), "Signature link should be valid."
        )
        self.assertFalse(
            self.po._portal_verify_upload_bill_session(self.other_partner, **params),
            "Signature link should be invalid for this partner.",
        )
        self.assertFalse(
            self.our_other_po._portal_verify_upload_bill_session(self.po.partner_id, **params),
            "Signature link should be invalid for this other PO.",
        )

    def test_purchase_order_session_verification_url_expiration(self):
        """Session verification URLs should expire."""
        with freeze_time() as freeze:
            params = self._get_session_verification_params()
            self.assertTrue(
                self.po._portal_verify_upload_bill_session(self.po.partner_id, **params),
                "Signature link should be valid.",
            )
            freeze.tick(delta=datetime.timedelta(seconds=VERIFICATION_URL_DURATION_S + 1))
            self.assertFalse(
                self.po._portal_verify_upload_bill_session(self.po.partner_id, **params),
                "Signature link should have expired.",
            )

    # Session tests.
    def test_portal_session_expiration_invalid_partner(self):
        """Sessions should expire when viewing a PO belonging to another partner."""
        session = self.authenticate("portal", "portal")
        self._create_verified_session(self.po, session)
        self.assertFalse(
            self._reloaded_session_is_verified(self.other_partner, session), "Shouldn't be verified for this partner."
        )
        self.assertFalse(
            self._reloaded_session_is_verified(self.po.partner_id, session), "Session should have expired."
        )

    def test_portal_session_creation_public_user(self):
        """Public users can't have verified sessions."""
        session = self.authenticate(None, None)
        self._create_verified_session(self.po, session, error_if_not_verified=False)
        self.assertFalse(self._reloaded_session_is_verified(self.other_partner, session), "Shouldn't be verified.")

        self._create_verified_session(self.po, session, add_access_token=True, error_if_not_verified=False)
        self.assertFalse(self._reloaded_session_is_verified(self.other_partner, session), "Shouldn't be verified.")

    def test_portal_session_expiration_time(self):
        """Sessions should expire after VERIFIED_SESSION_DURATION_S."""
        session = self.authenticate("portal", "portal")

        with freeze_time() as freeze:
            self._create_verified_session(self.po, session)
            freeze.tick(delta=datetime.timedelta(seconds=VERIFIED_SESSION_DURATION_S + 1))
            self.assertFalse(
                self._reloaded_session_is_verified(self.po.partner_id, session), "Session should have expired."
            )

    def test_portal_session_swap_commercial_partner(self):
        """Sessions shouldn't be valid after you change commercial partner."""
        session = self.authenticate("portal", "portal")
        self._create_verified_session(self.po, session)
        self.partner_portal.parent_id = self.other_partner
        self.assertFalse(
            self._reloaded_session_is_verified(self.other_partner, session),
            "Session shouldn't be valid for this new company.",
        )

    # /my/purchase/<int:order_id> tests.
    def _upload_bill_flow(self, user, password):
        """Uploading a bill should only be possible with a verified session on confirmed POs belonging to us."""
        session = self.authenticate(user, password)

        response = self._upload_bill()
        self.assertEqual(response.status_code, 200, "Response should have succeeded.")
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my.")
        self.assertFalse(self.po.invoice_ids, "A vendor bill should not have been created.")

        self._create_verified_session(self.po, session)
        with mute_logger("odoo.http"):
            response = self._upload_bill()
        self.assertEqual(response.status_code, 400, "Bills can't be uploaded on draft POs.")

        self.po.button_confirm()
        response = self._upload_bill()
        self.assertEqual(response.status_code, 200, "Response should have succeeded.")
        bill = self.po.invoice_ids
        self.assertTrue(bill, "A vendor bill should have been created.")
        self.assertEqual(
            self.po.invoice_ids.partner_bank_id, self.bank_account, "Bill should have the correct bank account."
        )

        with mute_logger("odoo.http"):
            response = self._upload_bill()
        self.assertEqual(response.status_code, 200, "Uploading another bill should succeed and replace the first.")
        self.assertNotEqual(bill, self.po.invoice_ids, "The first bill should have been replaced.")

        self.our_other_po.button_confirm()
        response = self._upload_bill(po=self.our_other_po)
        self.assertEqual(response.status_code, 200, "Response should have succeeded.")
        self.assertTrue(self.our_other_po.invoice_ids, "A vendor bill should have been created.")
        self.assertEqual(
            self.our_other_po.invoice_ids.partner_bank_id,
            self.bank_account,
            "Bill should have the correct bank account.",
        )

        response = self._upload_bill(po=self.someone_elses_po)
        self.assertEqual(response.status_code, 200, "Response should have succeeded.")
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my.")
        self.assertFalse(self.someone_elses_po.invoice_ids, "A vendor bill should not have been created.")

        response = self._upload_bill(po=self.someone_elses_po, add_access_token=True)
        self.assertEqual(response.status_code, 200, "Response should have succeeded.")
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my.")
        self.assertFalse(self.someone_elses_po.invoice_ids, "A vendor bill should not have been created.")

    def test_portal_my_purchase_order_verify_session_upload_bill_main_partner(self):
        """Uploading a bill should only be possible with a verified session on confirmed POs belonging to us."""
        self._upload_bill_flow("portal", "portal")

    def test_portal_my_purchase_order_verify_session_upload_bill_ar_responsible(self):
        """Uploading a bill should only be possible with a verified session on confirmed POs belonging to our company."""
        self._upload_bill_flow("ar_responsible", "ar_responsible")

    def _upload_bill_view_confidential_data_flow(self, user, password):
        session = self.authenticate(user, password)
        response = self.url_open(f"/my/purchase/{self.po.id}")
        self.assertEqual(
            response.text.count(self.bank_account.masked_acc_number),
            0,
            "Our bank account should not be in the DOM (no verified session, and no existing bill).",
        )
        self.assertEqual(
            response.text.count(self.someone_elses_bank_account.masked_acc_number),
            0,
            "Other people's bank not be in the DOM.",
        )

        self.po.button_confirm()
        self._create_verified_session(self.po, session)
        response = self._upload_bill()
        self.assertEqual(
            response.text.count(self.bank_account.masked_acc_number),
            2,
            "Our bank account should be in the DOM twice, in the payment card and the upload bill modal.",
        )

        self.env["res.partner.bank"].create({"acc_number": "x", "partner_id": self.partner_portal.id})
        response = self.url_open(f"/my/purchase/{self.po.id}")
        self.assertEqual(
            response.text.count(self.bank_account.masked_acc_number),
            2,
            "The used bank account on the bill should still be shown twice, in the payment card and the upload bill modal.",
        )

        def assert_no_bank_account(with_access_token):
            response = self.url_open(
                self.someone_elses_po.get_portal_url()
                if with_access_token
                else f"/my/purchase/{self.someone_elses_po.id}"
            )
            self.assertEqual(
                response.text.count(self.bank_account.masked_acc_number),
                0,
                "Our bank account should not be in DOM on someone else's PO.",
            )
            self.assertEqual(
                response.text.count(self.someone_elses_bank_account.masked_acc_number),
                0,
                "Other people's bank should not be in the DOM.",
            )

        assert_no_bank_account(with_access_token=False)
        self.someone_elses_po.button_confirm()
        assert_no_bank_account(with_access_token=False)

        self.someone_elses_po.button_draft()
        assert_no_bank_account(with_access_token=True)
        self.someone_elses_po.button_confirm()
        assert_no_bank_account(with_access_token=True)

    def test_portal_my_purchase_order_confidential_data_main_partner(self):
        """Confidential bank account information should only be present on POs belonging to us."""
        self._upload_bill_view_confidential_data_flow("portal", "portal")

    def test_portal_my_purchase_order_confidential_data_main_ar_responsible(self):
        """Confidential bank account information should only be present on POs belonging to us or our company."""
        self._upload_bill_view_confidential_data_flow("ar_responsible", "ar_responsible")

    def test_portal_my_purchase_order_switch_partner_after_verified_session(self):
        """A valid session should no longer be usable when the PO was assigned to another partner."""
        session = self.authenticate("portal", "portal")
        self._create_verified_session(self.po, session)

        self.po.partner_id = self.other_partner
        response = self._upload_bill()
        self.assertEqual(response.status_code, 200, "Response should have succeeded.")
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my.")
        self.assertFalse(self.po.invoice_ids, "A vendor bill should not have been created.")
        self.assertFalse(
            self._reloaded_session_is_verified(self.po.partner_id, session), "Should not be verified for this partner."
        )

    def test_portal_my_purchase_order_wrong_user(self):
        """Partners shouldn't be able to upload bills on POs not belonging to them."""

        def test_with_user(user, password):
            self.authenticate(user, password)
            response = self.url_open(self.po._portal_get_upload_bill_signed_url())
            self.assertEqual(response.status_code, 200, "Loading the page should have succeeded.")
            self.assertNotIn(str(self.po.id), response.url, "Should have redirected.")

            response = self._upload_bill()
            self.assertEqual(response.status_code, 200, "Response should have succeeded.")
            self.assertNotIn(str(self.po.id), response.url, "Should have redirected.")
            self.assertFalse(self.po.invoice_ids, "A vendor bill should not have been created.")

        test_with_user(None, None)  # public user
        test_with_user("portal2", "portal2_pwd")

    # /my/purchase/<int:order_id>/verify tests.
    def _send_verification_mail_flow(self, user, password):
        def verify(url):
            most_recent_mail = self.env["mail.mail"].search([], limit=1)
            data = {"csrf_token": http.Request.csrf_token(self)}
            with self.mock_mail_gateway():
                self.url_open(url, data=data)

            verification_mail = self.env["mail.mail"].search([], limit=1)
            if verification_mail != most_recent_mail:
                self.assertEqual(
                    verification_mail.partner_ids,
                    self.po.partner_id,
                    "Verification emails should always be sent to the partner on the PO, not who requests them.",
                )
                return verification_mail
            return None

        self.authenticate(user, password)

        response = self.url_open(f"/my/purchase/{self.po.id}")
        self.assertTrue(
            "Verify your email address at" in response.text, "The email verification modal should be present."
        )

        url = f"/my/purchase/{self.po.id}/verify"
        self.po.button_confirm()
        verification_mail = verify(url)
        self.assertIsNotNone(verification_mail, "An email should have been sent.")
        self.assertIn("Upload Your Bill", verification_mail.body, "Verification button should be present on RFQs.")

        url = self.someone_elses_po.get_portal_url(suffix="/verify")
        self.someone_elses_po.button_confirm()
        self.assertIsNone(verify(url), "Shouldn't send verification emails on POs we can't access.")

    def test_portal_my_purchase_verify_main_company(self):
        """A logged-in user should be able to request email verification on their own PO."""
        self._send_verification_mail_flow("portal", "portal")

    def test_portal_my_purchase_verify_ar_responsible(self):
        """A logged-in user should be able to request email verification on their company's PO."""
        self._send_verification_mail_flow("ar_responsible", "ar_responsible")

    # /my/bill/<int:move_id>/cancel tests.
    def _cancel_bill_flow(self, user, password):
        """A logged in and verified user should be able to cancel draft bills linked to their own POs."""

        def cancel_bill(po, invoice=None):
            if not invoice:
                invoice = po.invoice_ids[-1]
            data = {"csrf_token": http.Request.csrf_token(self), "purchase_order_id": po.id}
            response = self.url_open(f"/my/bill/{invoice.id}/cancel", data=data)
            return response

        url = f"/my/purchase/{self.po.id}"
        session = self.authenticate(user, password)
        user = self.env["res.users"].browse(session.uid)

        self.po.button_confirm()
        self.po.with_user(user).sudo()._create_invoices()

        response = self.url_open(url)
        self.assertIn("Delete invoice", response.text, "The invoice should have a trash button.")
        self.assertIn(
            "bill_deletion_verification_button", response.text, "Trash button should open the verification modal."
        )
        response = cancel_bill(self.po)
        self.assertNotIn(str(self.po.id), response.url, "Cancelling without being verified should have redirected.")
        self.assertEqual(self.po.invoice_ids[0].state, "draft", "Bill should have remained draft.")

        self._create_verified_session(self.po, session)
        response = self.url_open(url)
        self.assertIn("Delete invoice", response.text, "The invoice should have a trash button.")
        self.assertIn("bill_deletion_submit_button", response.text, "Trash button should submit the form.")
        response = cancel_bill(self.po)
        self.assertEqual(response.status_code, 200, "Cancelling should have succeeded.")
        self.assertEqual(self.po.invoice_ids[-1].state, "cancel", "Bill should be cancelled.")
        self.po.invoice_ids.unlink()

        self.po.with_user(self.user_admin)._create_invoices()
        response = self.url_open(url)
        self.assertTrue(
            "Delete invoice" not in response.text,
            "The invoice shouldn't have a trash button, we can't delete bills not created by us.",
        )
        response = cancel_bill(self.po)
        self.assertNotIn(str(self.po.id), response.url, "Should have redirected.")
        self.assertEqual(self.po.invoice_ids[-1].state, "draft", "Invoice should have remained in draft.")
        self.po.invoice_ids.unlink()

        self.po.with_user(self.user_portal).sudo()._create_invoices()
        invoice = self.po.invoice_ids[-1]
        invoice.invoice_date = "2024-01-01"
        invoice.action_post()
        response = cancel_bill(self.po)
        self.assertNotIn(str(self.po.id), response.url, "Should have redirected, we can't cancel posted bills.")
        self.assertEqual(self.po.invoice_ids[-1].state, "posted", "Invoice should have remained posted.")

        self.someone_elses_po.button_confirm()
        self.someone_elses_po._create_invoices()
        response = self.url_open(self.someone_elses_po.get_portal_url())
        self.assertNotIn(
            "Delete invoice", response.text, "A PO not belonging to us should not have any invoice trash button."
        )
        response = cancel_bill(self.someone_elses_po)
        self.assertNotIn(str(self.someone_elses_po.id), response.url, "Should have redirected.")
        self.assertEqual(self.someone_elses_po.invoice_ids[0].state, "draft", "Invoice should have remained in draft.")

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": user.partner_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                        },
                    )
                ],
            }
        )
        response = cancel_bill(self.po, invoice=invoice)
        self.assertNotIn(str(self.po.id), response.url, "Should have redirected, we can only cancel vendor bills.")
        self.assertEqual(invoice.state, "draft", "Invoice should have remained in draft.")

    def test_portal_my_bill_cancel_main_company(self):
        self._cancel_bill_flow("portal", "portal")

    def test_portal_my_bill_cancel_ar_responsible(self):
        self._cancel_bill_flow("ar_responsible", "ar_responsible")

    # /my/bank_account tests.
    def _get_bank_account_flow(self, user, password):
        session = self.authenticate(user, password)
        response = self.url_open("/my/bank_account")
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my because we are not verified.")

        self._create_verified_session(self.po, session)
        response = self.url_open("/my/bank_account")
        self.assertTrue(self.bank_account.masked_acc_number in response.text, "Our own bank account should be visible.")

    def test_portal_my_bank_account_get(self):
        """A logged in and verified user should be able to see their own bank accounts."""
        self.authenticate(None, None)
        response = self.url_open("/my/bank_account")
        self.assertIn("/web/login", response.url, "Should have redirected to /web/login.")

        self._get_bank_account_flow("portal", "portal")
        self._get_bank_account_flow("ar_responsible", "ar_responsible")

    def _create_bank_account_request(self, omit_required_fields=False, extra_data=None):
        data = {"csrf_token": http.Request.csrf_token(self)}
        files = {}
        if not omit_required_fields:
            # res.bank required fields
            data.update(
                {
                    "bic": "bic value",
                    "name": "name value",
                    "street": "street value",
                    "city": "city value",
                    "zip": "zip value",
                    "country": self.env.ref("base.us").id,
                }
            )

            # res.partner.bank required fields
            ResPartnerBank = self.env["res.partner.bank"]
            country_code = "US"
            frontend_fields = ResPartnerBank._get_frontend_bank_account_fields_for_country(country_code)
            data.update(
                {
                    field.name: field.placeholder or f"{field.name} value"
                    for field in frontend_fields
                    if field.required and field.type == "text"
                }
            )
            if extra_data:
                data.update(extra_data)

            files.update(
                {
                    field.name: self._generate_mock_pdf(field.name)
                    for field in frontend_fields
                    if field.required and field.type == "file"
                }
            )

        return self.url_open("/my/bank_account", data=data, files=files)

    def _bank_account_creation_flow(self, user, password):
        initial_banks = self.env["res.bank"].search([])
        initial_bank_accounts = self.env["res.partner.bank"].search([])

        session = self.authenticate(user, password)
        response = self._create_bank_account_request()
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my because we are not verified.")
        self.assertFalse(self.env["res.bank"].search([]) - initial_banks, "No banks should have been created.")
        self.assertFalse(
            self.env["res.partner.bank"].search([]) - initial_bank_accounts,
            "No bank accounts should have been created.",
        )

        self._create_verified_session(self.po, session)
        with mute_logger("odoo.http"):
            response = self._create_bank_account_request(omit_required_fields=True)
        self.assertTrue(response.url.endswith("/my/bank_account"), "Should have redirected back to /my/bank_account.")
        self.assertTrue(
            "Missing required bank fields." in response.text, "Should have raised an error indicated missing field."
        )

        response = self._create_bank_account_request()
        self.assertTrue(response.url.endswith("/my/bank_account"), "Should have redirected back to /my/bank_account.")

        new_bank = self.env["res.bank"].search([]) - initial_banks
        self.assertTrue(new_bank, "A new bank should have been created.")
        self.assertEqual(new_bank.create_uid.login, user, "New bank should be created by the logged in user.")

        commercial_partner = self.partner_portal
        new_bank_account = self.env["res.partner.bank"].search([]) - initial_bank_accounts
        self.assertTrue(new_bank_account, "A new bank account should have been created.")
        self.assertEqual(
            new_bank_account.partner_id, commercial_partner, "Bank account should belong to our commercial partner."
        )
        self.assertEqual(
            new_bank_account.create_uid.login, user, "New bank account should be created by the logged in user."
        )
        self.assertTrue(new_bank_account.masked_acc_number in response.text, "Bank account should be displayed.")
        self.assertEqual(new_bank_account, commercial_partner.bank_ids[0], "The new bank should be first.")
        new_bank_account.unlink()

        self._create_bank_account_request(extra_data={"partner_id": self.other_partner.id})
        new_bank_account = self.env["res.partner.bank"].search([]) - initial_bank_accounts
        self.assertEqual(
            new_bank_account.partner_id,
            commercial_partner,
            "It shouldn't be possible to create a bank account not belonging to us.",
        )

    def test_portal_my_bank_account_create_public(self):
        """A public user shouldn't be able to create bank accounts."""
        self.authenticate(None, None)
        response = self._create_bank_account_request()
        self.assertIn("/web/login", response.url, "Should have redirected to /web/login.")

    def test_portal_my_bank_account_create_portal(self):
        """A logged in and verified user should be able to create a bank account for their own company."""
        self._bank_account_creation_flow("portal", "portal")

    def test_portal_my_bank_account_create_ar_responsible(self):
        """A logged in and verified user should be able to create a bank account for their company."""
        self._bank_account_creation_flow("ar_responsible", "ar_responsible")

    def test_portal_my_bank_account_create_sanity(self):
        """A logged in verified user should only be able to create banks with a plausible SWIFT code. They should also
        be limited to creating at most MAX_CREATED_BANK_RECORDS res.bank and res.partner.bank records."""

        def assert_at_limit(model):
            self.assertEqual(
                self.env[model]
                .with_context(active_test=False)
                .search_count([("create_uid", "=", self.user_portal.id)]),
                MAX_CREATED_BANK_RECORDS,
                f"The portal partner should have created 20 {model} records now.",
            )

        session = self.authenticate("portal", "portal")
        self._create_verified_session(self.po, session)

        with mute_logger("odoo.http"):
            # 12 digit bank account number instead of swift
            response = self._create_bank_account_request(extra_data={"bic": "012345678900"})
            self.assertEqual(response.status_code, 400, "The provided BIC isn't a valid SWIFT.")

            # bank name instead of swift
            response = self._create_bank_account_request(extra_data={"bic": "Bank of America"})
            self.assertEqual(response.status_code, 400, "The provided BIC isn't a valid SWIFT.")

        self._create_bank_account_request(extra_data={"street": "  spurious spaces "})
        bank = self.partner_portal.bank_ids[0].bank_id
        self.assertEqual(
            bank.street, "spurious spaces", "Spaces should have been stripped."
        )
        self.partner_portal.bank_ids[0].unlink()
        bank.unlink()

        vals_list = []
        for i in range(MAX_CREATED_BANK_RECORDS):
            vals_list.append({"name": "bank name", "active": i > 10})
        banks = self.env["res.bank"].with_user(self.user_portal).sudo().create(vals_list)
        assert_at_limit("res.bank")

        with mute_logger("odoo.http"):
            response = self._create_bank_account_request(extra_data={"name": "new name"})
        self.assertEqual(response.status_code, 400, "The portal partner shouldn't be able to create >20 banks.")
        banks.unlink()

        vals_list = []
        for i in range(MAX_CREATED_BANK_RECORDS - len(self.partner_portal.bank_ids)):
            vals_list.append({"partner_id": self.partner_portal.id, "acc_number": f"test {i}", "active": i > 10})

        self.env["res.partner.bank"].with_user(self.user_portal).sudo().create(vals_list)
        assert_at_limit("res.partner.bank")

        with mute_logger("odoo.http"):
            response = self._create_bank_account_request()
        self.assertEqual(response.status_code, 400, "The portal partner shouldn't be able to create >20 bank accounts.")

    # /my/bank_account/<int:bank_account_id>/archive tests.
    def _archive_bank_account_request(self, bank_account):
        return self.url_open(
            f"/my/bank_account/{bank_account.id}/archive", data={"csrf_token": http.Request.csrf_token(self)}
        )

    def _bank_account_archive_flow(self, user, password):
        session = self.authenticate(user, password)
        response = self._archive_bank_account_request(self.bank_account)
        self.assertTrue(response.url.endswith("/my"), "Should have redirected to /my because we are not verified.")
        self.assertTrue(self.bank_account.active, "Bank account should not have been archived.")

        self._create_verified_session(self.po, session)
        response = self._archive_bank_account_request(self.bank_account)
        self.assertTrue(response.url.endswith("/my/bank_account"), "Should have redirected back to /my/bank_account.")
        self.assertTrue(
            self.bank_account.masked_acc_number not in response.text, "Bank account should no longer be visible."
        )
        self.assertFalse(self.bank_account.active, "Bank account should have been archived.")

        response = self._archive_bank_account_request(self.someone_elses_bank_account)
        self.assertTrue(response.url.endswith("/my"), "Should have redirected back to /my.")
        self.assertTrue(
            self.someone_elses_bank_account.active, "We shouldn't be able to archive other's bank accounts."
        )

    def test_portal_my_bank_account_archive_public(self):
        """A public user shouldn't be able to archive their own bank accounts."""
        self.authenticate(None, None)
        response = self._archive_bank_account_request(self.bank_account)
        self.assertIn("/web/login", response.url, "Should have redirected to /web/login.")
        self.assertTrue(self.bank_account.active, "Bank account should not have been archived.")

    def test_portal_my_bank_account_archive_portal(self):
        """A logged in and verified user should be able to archive their own bank accounts."""
        self._bank_account_archive_flow("portal", "portal")

    def test_portal_my_bank_account_archive_ar_responsible(self):
        """A logged in and verified user should be able to archive their company's bank accounts."""
        self._bank_account_archive_flow("ar_responsible", "ar_responsible")

    # /my/bank_account/get_banks tests.
    def test_my_portal_get_banks(self):
        """Logged in and verified users can get res.bank records."""

        def get_banks(query):
            url = f"/my/bank_account/get_banks?bic={query}"
            return self.url_open(url)

        self.env["res.bank"].create(
            [
                {"name": "Bank of America", "bic": "BOFAUS6NXXX"},
                {"name": "ING", "bic": "BBRUBEBB10"},
                {"name": "Chase", "bic": "CHASUS33XXX"},
                {"name": "Chase", "bic": "CHASUS33"},
            ]
        )

        self.authenticate(None, None)
        response = get_banks("CHAS")
        self.assertIn("/web/login", response.url, "Should have redirected to /web/login.")

        session = self.authenticate("portal", "portal")
        with mute_logger("odoo.http"):
            response = get_banks("CHAS")
        self.assertEqual(response.status_code, 403, "Should have raised an AccessError.")
        self.assertTrue("Please verify your email address" in response.text, "Should have raised an AccessError.")

        self._create_verified_session(self.po, session)
        response = get_banks("CHAS")
        json = response.json()
        self.assertEqual(len(json), 2, "Should have returned the two Chase banks.")
        self.assertEqual(response.text.count("CHASUS33"), 2, "Should have returned the two Chase banks.")

        response = get_banks("")
        json = response.json()
        self.assertEqual(len(json), 0, "Should have returned no banks, 4 characters are required to perform a search.")

        response = get_banks("%%%%")
        json = response.json()
        self.assertEqual(len(json), 0, "Should have returned no banks, 'like' patterns should have been removed.")

        response = get_banks("____")
        json = response.json()
        self.assertEqual(len(json), 0, "Should have returned no banks, 'like' patterns should have been removed.")
