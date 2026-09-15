from base64 import b64decode

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """
    Fix base64-encoded PDF attachments that were incorrectly stored during the
    previous version.

    The Nilvera client returns base64-encoded PDF content from the GET pdf endpoint.
    The previous code stored this base64 string directly into the ir.attachment.raw
    field without decoding. Since raw is binary, the base64 ASCII text was UTF-8
    encoded, resulting in files on disk containing base64 text instead of PDF bytes.

    This migration:
    1. Finds all invoices with l10n_tr_nilvera_uuid
    2. Gets their PDF attachments
    3. Identifies corrupted PDFs (those with raw starting with b'JVBERi0')
    4. Decodes the base64 content and updates the attachment
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    invoice_query = env['account.move']._search([
        ('l10n_tr_nilvera_uuid', '!=', False),
    ])
    attachments = env['ir.attachment'].search([
        ('res_model', '=', 'account.move'),
        ('res_id', 'in', invoice_query),
        ('mimetype', '=', 'application/pdf'),
    ])

    for attachment in attachments:
        # `raw` may be plain bytes, or (in some versions) a LocalBinaryFile-like
        # object; `bytes(...)` normalizes either case to the actual content.
        raw_data = attachment.raw
        if raw_data is None:
            continue
        raw_data = bytes(raw_data)

        # Check if this is a base64-encoded PDF (starts with 'JVBERi0' which is '%PDF-' in base64).
        if raw_data.startswith(b'JVBERi0'):
            # Decode the base64 string to get the actual PDF bytes.
            attachment.raw = b64decode(raw_data)
