import base64
from contextlib import contextmanager, nullcontext
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from freezegun import freeze_time

from odoo import Command, fields
from odoo.models import Model

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_LOCAL_SIGNING_KEY = None


def _local_signing_key():
    global _LOCAL_SIGNING_KEY  # noqa: PLW0603
    if _LOCAL_SIGNING_KEY is None:
        _LOCAL_SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    return _LOCAL_SIGNING_KEY


def _local_sign_records(env, docs_to_sign, model):
    """In-process stand-in for the IAP signing service: RSA-1024/SHA-1 over the AT message, a batch
    chained by `sorting_key` as the service does."""
    res, previous = {}, None
    for doc in sorted(docs_to_sign, key=lambda d: d['sorting_key']):
        previous_signature = doc['previous_signature'] if previous is None else previous
        message = f"{doc['date']};{doc['system_entry_date']};{doc['name']};{doc['gross_total']};{previous_signature or ''}"
        previous = base64.b64encode(_local_signing_key().sign(message.encode(), padding.PKCS1v15(), hashes.SHA1())).decode()
        res[env[model].browse(int(doc['id']))] = f"$1${previous}"
    return res


def _local_public_keys(env):
    return {1: _local_signing_key().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()}


class TestL10nPtCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pt')
    def setUpClass(cls):
        def create_at_series(year):
            sale_journal = cls.company_data['default_journal_sale']
            bank_journal = cls.company_data['default_journal_bank']
            series = cls.env['l10n_pt.at.series'].create([{
                'name': year,
                'company_id': cls.company_pt.id,
                'training_series': True,
                'company_exclusive_series': True,
                'date_start': f"{year}-01-01",
                'date_end': f"{year}-12-31",
                'journal_id': bank_journal.id if series_type == 'payment_receipt' else sale_journal.id,
                'document_type': series_type,
                'prefix': prefix,
                'at_code': f'AT-TEST{prefix}{year}',
            } for series_type, prefix in (('out_invoice', 'INV'), ('out_receipt', 'FS'), ('out_refund', 'RINV'), ('payment_receipt', 'PAY'))])
            return series

        super().setUpClass()
        if 'standard' in cls.test_tags:
            # Posting a PT invoice signs it through IAP; standard runs sign in-process instead, with
            # real signatures, so the integrity checks still detect tampering.
            cls.startClassPatcher(patch('odoo.addons.l10n_pt_certification.utils.hashing.sign_records', _local_sign_records))
            cls.startClassPatcher(patch('odoo.addons.l10n_pt_certification.utils.hashing.get_public_keys', _local_public_keys))
        cls.company_pt = cls.company_data['company']
        cls.company_pt.write({
            'street': '25 Avenida da Liberdade',
            'city': 'Lisboa',
            'zip': '9415-343',
            'company_registry': '123456',
            'phone': '+351 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
            'vat': 'PT123456789',
        })
        cls.partner_a.vat = 'PT123456789'
        cls.company_data_2 = cls.setup_other_company()
        cls.series_2017 = create_at_series('2017')
        cls.series_2024 = create_at_series('2024')
        cls.tax_sale_23 = cls.env['account.chart.template'].ref('iva_pt_sale_normal')
        cls.tax_sale_0 = cls.env['account.chart.template'].ref('iva_pt_sale_eu_isenta')

    @classmethod
    def create_invoice(cls, move_type='out_invoice', invoice_date='2024-01-01', post=True, l10n_pt_hashed_on=None, amount=1000.0,
                       quantity=1, tax=None, product_id=False, do_hash=False, mock_hash=False):
        invoice_data = {
            'company_id': cls.company_pt.id,
            'move_type': move_type,
            'partner_id': cls.partner_a.id,
            'invoice_date': fields.Date.from_string(invoice_date),
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    # A PT invoice line needs a product (D-4)
                    'product_id': product_id or cls.product_a.id,
                    'quantity': quantity,
                    'price_unit': amount,
                    'tax_ids': [tax.id if tax else cls.tax_sale_23.id],
                }),
            ],
        }
        year = str(invoice_data['invoice_date'].year)
        series_for_year = cls.series_2017 if year == '2017' else cls.series_2024
        invoice_data['l10n_pt_at_series_id'] = series_for_year.filtered(lambda s: s.document_type == move_type).id

        move = cls.env['account.move'].with_company(cls.company_pt).create(invoice_data)
        # The tests take a posted invoice as issued: it is issued right after posting, as its first
        # print would (PT-105), so `l10n_pt_hashed_on` is the time it is posted at.
        with (
            freeze_time(l10n_pt_hashed_on or fields.Date.today()) if do_hash else nullcontext(),
            cls._mock_sign_records() if mock_hash else nullcontext(),
        ):
            if post:
                move.action_post()
                move._l10n_pt_issue()
            if do_hash and not move.inalterable_hash:
                move.button_hash()
        return move

    @classmethod
    @contextmanager
    def _mock_ws(cls, return_code=None, side_effect=None):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.bind.return_value = mock_service

        kwargs = {'return_value': return_code} if side_effect is None else {'side_effect': side_effect}

        with patch(
            'odoo.addons.base.models.res_company.ResCompany._get_zeep_client__',
            return_value=mock_client,
        ), patch(
            'odoo.addons.l10n_pt_certification.models.l10n_pt_at_series.L10nPtATSeries._registar_serie',
            **kwargs,
        ) as mock_reg:
            yield mock_reg

    @classmethod
    @contextmanager
    def _mock_sign_records(cls):
        def fake_sign(env, docs_to_sign, model):
            return {env[model].browse(int(d['id'])): f"$1${'A' * 40}" for d in docs_to_sign}
        with patch('odoo.addons.l10n_pt_certification.utils.hashing.sign_records', fake_sign):
            yield

    @classmethod
    def _inject_fake_hash(cls, move, hash_str=None):
        hash_str = hash_str or ('A' * 40)
        Model.write(move, {'inalterable_hash': f'$1${hash_str}'})
        move.flush_recordset()
