import base64
import contextlib
import textwrap
import uuid

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged, RecordCapturer

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mimetypes.tests.test_guess_mimetypes import contents


class TestAccountInvoiceImportMixin:
    """ Helpers for uploading attachments on invoices by various means and asserting how they are decoded. """

    @classmethod
    def _get_dummy_pdf_vals(cls):
        rawpdf_base64 = b'JVBERi0xLjYNJeLjz9MNCjI0IDAgb2JqDTw8L0ZpbHRlci9GbGF0ZURlY29kZS9GaXJzdCA0L0xlbmd0aCAyMTYvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjePI9RS8MwFIX/yn1bi9jepCQ6GYNpFBTEMsW97CVLbjWYNpImmz/fVsXXcw/f/c4SEFarepPTe4iFok8dU09DgtDBQx6TMwT74vaLTE7uSPDUdXM0Xe/73r1FnVwYYEtHR6d9WdY3kX4ipRMV6oojSmxQMoGyac5RLBAXf63p38aGA7XPorLewyvFcYaJile8rB+D/YcwiRdMMGScszO8/IW0MdhsaKKYGA46gXKTr/cUQVY4We/cYMNpnLVeXPJUXHs9fECr7kAFk+eZ5Xr9LcAAfKpQrA0KZW5kc3RyZWFtDWVuZG9iag0yNSAwIG9iag08PC9GaWx0ZXIvRmxhdGVEZWNvZGUvRmlyc3QgNC9MZW5ndGggNDkvTiAxL1R5cGUvT2JqU3RtPj5zdHJlYW0NCmjeslAwULCx0XfOL80rUTDU985MKY42NAIKBsXqh1QWpOoHJKanFtvZAQQYAN/6C60NCmVuZHN0cmVhbQ1lbmRvYmoNMjYgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDkvTGVuZ3RoIDQyL04gMi9UeXBlL09ialN0bT4+c3RyZWFtDQpo3jJTMFAwVzC0ULCx0fcrzS2OBnENFIJi7eyAIsH6LnZ2AAEGAI2FCDcNCmVuZHN0cmVhbQ1lbmRvYmoNMjcgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0ZpcnN0IDUvTGVuZ3RoIDEyMC9OIDEvVHlwZS9PYmpTdG0+PnN0cmVhbQ0KaN4yNFIwULCx0XfOzytJzSspVjAyBgoE6TsX5Rc45VdEGwB5ZoZGCuaWRrH6vqkpmYkYogGJRUCdChZgfUGpxfmlRcmpxUAzA4ryk4NTS6L1A1zc9ENSK0pi7ez0g/JLEktSFQz0QyoLUoF601Pt7AACDADYoCeWDQplbmRzdHJlYW0NZW5kb2JqDTIgMCBvYmoNPDwvTGVuZ3RoIDM1MjUvU3VidHlwZS9YTUwvVHlwZS9NZXRhZGF0YT4+c3RyZWFtDQo8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjQtYzAwNSA3OC4xNDczMjYsIDIwMTIvMDgvMjMtMTM6MDM6MDMgICAgICAgICI+CiAgIDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnBkZj0iaHR0cDovL25zLmFkb2JlLmNvbS9wZGYvMS4zLyIKICAgICAgICAgICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICAgICAgICAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgICAgICAgICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIj4KICAgICAgICAgPHBkZjpQcm9kdWNlcj5BY3JvYmF0IERpc3RpbGxlciA2LjAgKFdpbmRvd3MpPC9wZGY6UHJvZHVjZXI+CiAgICAgICAgIDx4bXA6Q3JlYXRlRGF0ZT4yMDA2LTAzLTA2VDE1OjA2OjMzLTA1OjAwPC94bXA6Q3JlYXRlRGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdG9yVG9vbD5BZG9iZVBTNS5kbGwgVmVyc2lvbiA1LjIuMjwveG1wOkNyZWF0b3JUb29sPgogICAgICAgICA8eG1wOk1vZGlmeURhdGU+MjAxNi0wNy0xNVQxMDoxMjoyMSswODowMDwveG1wOk1vZGlmeURhdGU+CiAgICAgICAgIDx4bXA6TWV0YWRhdGFEYXRlPjIwMTYtMDctMTVUMTA6MTI6MjErMDg6MDA8L3htcDpNZXRhZGF0YURhdGU+CiAgICAgICAgIDx4bXBNTTpEb2N1bWVudElEPnV1aWQ6ZmYzZGNmZDEtMjNmYS00NzZmLTgzOWEtM2U1Y2FlMmRhMmViPC94bXBNTTpEb2N1bWVudElEPgogICAgICAgICA8eG1wTU06SW5zdGFuY2VJRD51dWlkOjM1OTM1MGIzLWFmNDAtNGQ4YS05ZDZjLTAzMTg2YjRmZmIzNjwveG1wTU06SW5zdGFuY2VJRD4KICAgICAgICAgPGRjOmZvcm1hdD5hcHBsaWNhdGlvbi9wZGY8L2RjOmZvcm1hdD4KICAgICAgICAgPGRjOnRpdGxlPgogICAgICAgICAgICA8cmRmOkFsdD4KICAgICAgICAgICAgICAgPHJkZjpsaSB4bWw6bGFuZz0ieC1kZWZhdWx0Ij5CbGFuayBQREYgRG9jdW1lbnQ8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6QWx0PgogICAgICAgICA8L2RjOnRpdGxlPgogICAgICAgICA8ZGM6Y3JlYXRvcj4KICAgICAgICAgICAgPHJkZjpTZXE+CiAgICAgICAgICAgICAgIDxyZGY6bGk+RGVwYXJ0bWVudCBvZiBKdXN0aWNlIChFeGVjdXRpdmUgT2ZmaWNlIG9mIEltbWlncmF0aW9uIFJldmlldyk8L3JkZjpsaT4KICAgICAgICAgICAgPC9yZGY6U2VxPgogICAgICAgICA8L2RjOmNyZWF0b3I+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgog' + 682 * b'ICAg' + b'Cjw/eHBhY2tldCBlbmQ9InciPz4NCmVuZHN0cmVhbQ1lbmRvYmoNMTEgMCBvYmoNPDwvTWV0YWRhdGEgMiAwIFIvUGFnZUxhYmVscyA2IDAgUi9QYWdlcyA4IDAgUi9UeXBlL0NhdGFsb2c+Pg1lbmRvYmoNMjMgMCBvYmoNPDwvRmlsdGVyL0ZsYXRlRGVjb2RlL0xlbmd0aCAxMD4+c3RyZWFtDQpIiQIIMAAAAAABDQplbmRzdHJlYW0NZW5kb2JqDTI4IDAgb2JqDTw8L0RlY29kZVBhcm1zPDwvQ29sdW1ucyA0L1ByZWRpY3RvciAxMj4+L0ZpbHRlci9GbGF0ZURlY29kZS9JRFs8REI3Nzc1Q0NFMjI3RjZCMzBDNDQwREY0MjIxREMzOTA+PEJGQ0NDRjNGNTdGNjEzNEFCRDNDMDRBOUU0Q0ExMDZFPl0vSW5mbyA5IDAgUi9MZW5ndGggODAvUm9vdCAxMSAwIFIvU2l6ZSAyOS9UeXBlL1hSZWYvV1sxIDIgMV0+PnN0cmVhbQ0KaN5iYgACJjDByGzIwPT/73koF0wwMUiBWYxA4v9/EMHA9I/hBVCxoDOQeH8DxH2KrIMIglFwIpD1vh5IMJqBxPpArHYgwd/KABBgAP8bEC0NCmVuZHN0cmVhbQ1lbmRvYmoNc3RhcnR4cmVmDQo0NTc2DQolJUVPRg0K'
        return {
            'raw': base64.b64decode(rawpdf_base64),
            'type': 'binary',
            'mimetype': 'application/pdf',
        }

    @classmethod
    def _get_dummy_pdf_with_embedded_file_vals(cls):
        """ This PDF has an embedded file with filename 'embedded.xml' and the following content
        <?xml version="1.0" encoding="UTF-8"?>
        <TestFileFormat>
            <PartnerName>partner_a</PartnerName>
        </TestFileFormat>
        """
        rawpdf_base64 = b'JVBERi0xLjYKJeLjz9MKMyAwIG9iaiAKPDwKL1R5cGUgL0VtYmVkZGVkRmlsZQovRmlsdGVyIC9GbGF0ZURlY29kZQovUGFyYW1zIDEgMCBSCi9MZW5ndGggMiAwIFIKPj4Kc3RyZWFtCnics7GvyM1RKEstKs7Mz7NVMtQzUFJIzUvOT8nMS7dVCg1x07VQsrfjsglJLS5xy8xJdcsvyk0sseNSAAKbgMSikrzUIr/E3FS7Agg7PtFGH1mYy0YfXSsAc6MmMgplbmRzdHJlYW0gCmVuZG9iaiAKMiAwIG9iaiA5MwplbmRvYmogCjEgMCBvYmogCjw8Ci9TaXplIDExNQo+PgplbmRvYmogCjQgMCBvYmogCjw8Ci9UeXBlIC9GCi9GIChlbWJlZGRlZC54bWwpCi9FRiAKPDwKL0YgMyAwIFIKPj4KL1VGICj+/wBlAG0AYgBlAGQAZABlAGQALgB4AG0AbCkKPj4KZW5kb2JqIAo1IDAgb2JqIAo8PAovTmFtZXMgWyj+/wBlAG0AYgBlAGQAZABlAGQALgB4AG0AbCkgNCAwIFJdCj4+CmVuZG9iaiAKNiAwIG9iaiAKPDwKL0VtYmVkZGVkRmlsZXMgNSAwIFIKPj4KZW5kb2JqIAo3IDAgb2JqIAo8PAovU3VidHlwZSAvWE1MCi9UeXBlIC9NZXRhZGF0YQovTGVuZ3RoIDM1MjUKPj4Kc3RyZWFtCjw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+Cjx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNC1jMDA1IDc4LjE0NzMyNiwgMjAxMi8wOC8yMy0xMzowMzowMyAgICAgICAgIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6cGRmPSJodHRwOi8vbnMuYWRvYmUuY29tL3BkZi8xLjMvIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iCiAgICAgICAgICAgIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIgogICAgICAgICAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iPgogICAgICAgICA8cGRmOlByb2R1Y2VyPkFjcm9iYXQgRGlzdGlsbGVyIDYuMCAoV2luZG93cyk8L3BkZjpQcm9kdWNlcj4KICAgICAgICAgPHhtcDpDcmVhdGVEYXRlPjIwMDYtMDMtMDZUMTU6MDY6MzMtMDU6MDA8L3htcDpDcmVhdGVEYXRlPgogICAgICAgICA8eG1wOkNyZWF0b3JUb29sPkFkb2JlUFM1LmRsbCBWZXJzaW9uIDUuMi4yPC94bXA6Q3JlYXRvclRvb2w+CiAgICAgICAgIDx4bXA6TW9kaWZ5RGF0ZT4yMDE2LTA3LTE1VDEwOjEyOjIxKzA4OjAwPC94bXA6TW9kaWZ5RGF0ZT4KICAgICAgICAgPHhtcDpNZXRhZGF0YURhdGU+MjAxNi0wNy0xNVQxMDoxMjoyMSswODowMDwveG1wOk1ldGFkYXRhRGF0ZT4KICAgICAgICAgPHhtcE1NOkRvY3VtZW50SUQ+dXVpZDpmZjNkY2ZkMS0yM2ZhLTQ3NmYtODM5YS0zZTVjYWUyZGEyZWI8L3htcE1NOkRvY3VtZW50SUQ+CiAgICAgICAgIDx4bXBNTTpJbnN0YW5jZUlEPnV1aWQ6MzU5MzUwYjMtYWY0MC00ZDhhLTlkNmMtMDMxODZiNGZmYjM2PC94bXBNTTpJbnN0YW5jZUlEPgogICAgICAgICA8ZGM6Zm9ybWF0PmFwcGxpY2F0aW9uL3BkZjwvZGM6Zm9ybWF0PgogICAgICAgICA8ZGM6dGl0bGU+CiAgICAgICAgICAgIDxyZGY6QWx0PgogICAgICAgICAgICAgICA8cmRmOmxpIHhtbDpsYW5nPSJ4LWRlZmF1bHQiPkJsYW5rIFBERiBEb2N1bWVudDwvcmRmOmxpPgogICAgICAgICAgICA8L3JkZjpBbHQ+CiAgICAgICAgIDwvZGM6dGl0bGU+CiAgICAgICAgIDxkYzpjcmVhdG9yPgogICAgICAgICAgICA8cmRmOlNlcT4KICAgICAgICAgICAgICAgPHJkZjpsaT5EZXBhcnRtZW50IG9mIEp1c3RpY2UgKEV4ZWN1dGl2ZSBPZmZpY2Ugb2YgSW1taWdyYXRpb24gUmV2aWV3KTwvcmRmOmxpPgogICAgICAgICAgICA8L3JkZjpTZXE+CiAgICAgICAgIDwvZGM6Y3JlYXRvcj4KICAgICAgPC9yZGY6RGVzY3JpcHRpb24+CiAgIDwvcmRmOlJERj4KPC94OnhtcG1ldGE+CiAg' + 681 * b'ICAg' + b'ICAKPD94cGFja2V0IGVuZD0idyI/PgplbmRzdHJlYW0gCmVuZG9iaiAKOCAwIG9iaiAKPDwKL051bXMgWzAgOSAwIFJdCj4+CmVuZG9iaiAKOSAwIG9iaiAKPDwKL1MgL0QKPj4KZW5kb2JqIAoxMCAwIG9iaiAKPDwKL0tpZHMgWzExIDAgUl0KL1R5cGUgL1BhZ2VzCi9Db3VudCAxCj4+CmVuZG9iaiAKMTIgMCBvYmogCjw8Ci9NZXRhZGF0YSA3IDAgUgovUGFnZUxhYmVscyA4IDAgUgovTmFtZXMgNiAwIFIKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEwIDAgUgo+PgplbmRvYmogCjExIDAgb2JqIAo8PAovUm90YXRlIDAKL1Jlc291cmNlcyAKPDwKL1Byb2NTZXQgWy9QREYgL1RleHRdCj4+Ci9UeXBlIC9QYWdlCi9QYXJlbnQgMTAgMCBSCi9Db250ZW50cyAxMyAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KL0Nyb3BCb3ggWzAgMCA2MTIgNzkyXQo+PgplbmRvYmogCjEzIDAgb2JqIAo8PAovRmlsdGVyIC9GbGF0ZURlY29kZQovTGVuZ3RoIDEwCj4+CnN0cmVhbQpIiQIIMAAAAAABCmVuZHN0cmVhbSAKZW5kb2JqIAoxNCAwIG9iaiAKPDwKL01vZERhdGUgKEQ6MjAxNjA3MTUxMDEyMjErMDgnMDAnKQovQ3JlYXRpb25EYXRlIChEOjIwMDYwMzA2MTUwNjMzLTA1JzAwJykKL0F1dGhvciAoRGVwYXJ0bWVudCBvZiBKdXN0aWNlIFwoRXhlY3V0aXZlIE9mZmljZSBvZiBJbW1pZ3JhdGlvbiBSZXZpZXdcKSkKL1RpdGxlIChCbGFuayBQREYgRG9jdW1lbnQpCi9DcmVhdG9yIChBZG9iZVBTNS5kbGwgVmVyc2lvbiA1LjIuMikKL1Byb2R1Y2VyIChBY3JvYmF0IERpc3RpbGxlciA2LjAgXChXaW5kb3dzXCkpCj4+CmVuZG9iaiB4cmVmCjAgMTUKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMjM4IDAwMDAwIG4gCjAwMDAwMDAyMTkgMDAwMDAgbiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMjcxIDAwMDAwIG4gCjAwMDAwMDAzNzQgMDAwMDAgbiAKMDAwMDAwMDQ0MSAwMDAwMCBuIAowMDAwMDAwNDg1IDAwMDAwIG4gCjAwMDAwMDQwOTUgMDAwMDAgbiAKMDAwMDAwNDEzNCAwMDAwMCBuIAowMDAwMDA0MTYzIDAwMDAwIG4gCjAwMDAwMDQzMjQgMDAwMDAgbiAKMDAwMDAwNDIyNCAwMDAwMCBuIAowMDAwMDA0NDg5IDAwMDAwIG4gCjAwMDAwMDQ1NzQgMDAwMDAgbiAKdHJhaWxlcgoKPDwKL0luZm8gMTQgMCBSCi9JRCBbPGRiNzc3NWNjZTIyN2Y2YjMwYzQ0MGRmNDIyMWRjMzkwPiA8YmZjY2NmM2Y1N2Y2MTM0YWJkM2MwNGE5ZTRjYTEwNmU+XQovUm9vdCAxMiAwIFIKL1NpemUgMTUKPj4Kc3RhcnR4cmVmCjQ4NTkKJSVFT0YK'
        return {
            'raw': base64.b64decode(rawpdf_base64),
            'type': 'binary',
            'mimetype': 'application/pdf',
        }

    @classmethod
    def _get_dummy_xml_vals(cls):
        return {
            'raw': b"""<?xml version="1.0" encoding="UTF-8"?>
                <TestFileFormat>
                    <PartnerName>partner_a</PartnerName>
                </TestFileFormat>
            """,
            'mimetype': 'application/xml',
        }

    @classmethod
    def _get_dummy_gif_vals(cls):
        return {
            'raw': base64.b64decode("R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="),
            'mimetype': 'image/gif',
        }

    @classmethod
    def _get_dummy_xlsx_vals(cls):
        return {
            'raw': contents('xlsx'),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

    @classmethod
    def _get_dummy_docx_vals(cls):
        return {
            'raw': contents('docx'),
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }

    def assert_attachment_import(self, origin, attachments_vals, expected_invoices):
        """ Simulate the upload and import of one or more attachments and assert that the
            created attachments were linked to the expected messages and invoices.

            :param origin: The source from which the attachments came (see `_upload_and_import_attachments`).

            :param attachments_vals: A list of values representing the attachments to be uploaded to Odoo

            :param expected_invoices: a dict {
                invoice_index (int): {
                    filename: {
                        'on_invoice': (bool) whether it should be attached on the invoice,
                        'on_message': (bool) whether it should be attached to a message in the chatter,
                        'is_decoded': (bool) whether it should have been decoded on the invoice,
                        'is_new': (bool) whether the call to the decoder should have `new=True`
                    }
                }
            }

            which for each newly-created invoice indicates:
                (1) which of the files it should be linked to, and, for each file
                    (a) whether it should be attached to the invoice or merely to a message on the invoice.
                    (b) whether it should have been decoded on the invoice
        """
        # Because no decoders are defined in `account` itself, if we want to test the decoder flow we need
        # to define a fictional format that will be decoded, and patch the `_get_import_file_type`
        # and `_get_edi_decoder` methods to accept it.

        with self._patch_import_methods() as decoder_calls:
            created_attachments, created_messages, created_invoices = self._upload_and_import_attachments(origin, attachments_vals)

        # Check that no two attachments were created with the same filename (needed for the rest of the test to work properly)
        self.assertEqual(len(created_attachments), len(created_attachments.grouped('name')))

        # Construct a dict representing the way the attachments were linked to new invoices and messages.
        actual_invoices = {}

        for message in created_messages.filtered(lambda m: m.model == 'account.move'):
            for attachment in message.attachment_ids:
                actual_invoices.setdefault(message.res_id, {}).setdefault(attachment.name, {})['on_message'] = True

        for attachment in created_attachments:
            if attachment.res_model == 'account.move':
                actual_invoices.setdefault(attachment.res_id, {}).setdefault(attachment.name, {})['on_invoice'] = True

        for decoder_call in decoder_calls:
            invoice = decoder_call[0]
            filename = decoder_call[1]['name']
            actual_invoices.setdefault(invoice.id, {}).setdefault(filename, {})['is_decoded'] = True

            if decoder_call[2]:
                actual_invoices[invoice.id][filename]['is_new'] = True

        # Map the invoice IDs to the invoice indexes of the expected_invoices.
        index_by_invoice_id = {
            invoice_id: index
            for index, invoice_id in enumerate(created_invoices.mapped('id'), start=1)
        }
        actual_invoices = {
            index_by_invoice_id[invoice_id]: attachment_info
            for invoice_id, attachment_info in actual_invoices.items()
        }
        self.assertDictEqual(actual_invoices, expected_invoices)

    @contextlib.contextmanager
    def _patch_import_methods(self):
        """ Patch the `_get_import_file_type` and `_get_edi_decoder` methods to accept the 'test_xml' format.
        """

        original_get_import_file_type = self.env.registry['account.move']._get_import_file_type

        def patched_get_import_file_type(self, file_data):
            """ Patch _get_import_file_type in order to recognize the 'test_xml' format
            which is an XML whose root tag is 'TestFileFormat'.
            """
            if file_data['xml_tree'] is not None and file_data['xml_tree'].tag == 'TestFileFormat':
                return 'test_xml'
            return original_get_import_file_type(self, file_data)

        decoder_calls = []

        original_get_edi_decoder = self.env.registry['account.move']._get_edi_decoder

        def patched_get_edi_decoder(self, file_data, new):
            if file_data['import_file_type'] == 'test_xml':
                def decoder(invoice, file_data, new):
                    if invoice.invoice_line_ids:
                        return invoice._reason_cannot_decode_has_invoice_lines()
                    decoder_calls.append((invoice, file_data, new))
                    partner_name = file_data['xml_tree'].findtext('.//PartnerName')
                    if partner_name and (partner := self.env['res.partner'].search([('name', '=', partner_name)], limit=1)):
                        invoice.partner_id = partner.id
                    else:
                        raise ValidationError('Could not identify partner!')
                return {
                    'decoder': decoder,
                    'priority': 20,
                }
            elif file_data['import_file_type'] == 'pdf':
                def decoder(invoice, file_data, new):
                    if invoice.invoice_line_ids:
                        return invoice._reason_cannot_decode_has_invoice_lines()
                    decoder_calls.append((invoice, file_data, new))
                return {
                    'decoder': decoder,
                    'priority': 10,
                }
            else:
                original_decoder_info = original_get_edi_decoder(self, file_data, new)
                if original_decoder_info is None:
                    return None

                def decoder(invoice, file_data, new):
                    decoder_calls.append((invoice, file_data, new))
                    return original_decoder_info['decoder'](invoice, file_data, new)
                return {
                    **original_decoder_info,
                    'decoder': decoder,
                }

        with (
            patch.object(self.env.registry['account.move'], '_get_import_file_type', patched_get_import_file_type),
            patch.object(self.env.registry['account.move'], '_get_edi_decoder', patched_get_edi_decoder),
        ):
            yield decoder_calls

    def _upload_and_import_attachments(self, origin, attachments_vals):
        """ Simulate the upload of one or more attachments and their processing by the import framework.
            Keeps track of the created attachments, messages and invoices, and returns them.

            :param origin: The source from which the attachments should be introduced into Odoo.
                           Possible values:
                                - 'chatter_message': Simulates a message posted on the chatter of an existing vendor bill.
                                - 'chatter_upload': Simulates attachments uploaded on the chatter of an existing vendor bill.
                                - 'chatter_email': Simulates an incoming e-mail on the chatter of an existing vendor bill.
                                - 'mail_alias': Simulates an incoming e-mail on a purchase journal mail alias.
                                - 'journal': Simulates attachments uploaded on a purchase journal in the dashboard.

            :param attachments_vals: A list of values representing attachments to upload into Odoo.

            :return: a dict {
                'ir.attachment': created_attachments,
                'mail.message': created_messages,
                'account.move': created_invoices,
            }
        """

        with (
            RecordCapturer(self.env['ir.attachment'].sudo()) as attachment_capturer,
            RecordCapturer(self.env['mail.message'].sudo()) as message_capturer,
            RecordCapturer(self.env['account.move']) as move_capturer,
        ):
            journal = self.company_data['default_journal_purchase']
            init_vals = {'move_type': 'in_invoice', 'journal_id': journal.id}

            if origin not in {'chatter_email', 'mail_alias'}:
                attachments = self.env['ir.attachment'].create(attachments_vals)

            if origin in {'chatter_upload', 'chatter_message', 'chatter_email'}:
                move = self.env['account.move'].create(init_vals)

            match origin:
                case 'chatter_message':
                    move.message_post(message_type='comment', attachment_ids=attachments.ids)
                case 'chatter_upload':
                    attachments.write({'res_model': 'account.move', 'res_id': move.id})
                    attachments._post_add_create()
                case 'chatter_email':
                    email_raw = self._get_raw_mail_message_str(attachments_vals, email_to='someone@example.com')
                    self.env['mail.thread'].message_process('account.move', email_raw, custom_values=init_vals, thread_id=move.id)
                case 'mail_alias':
                    email_raw = self._get_raw_mail_message_str(attachments_vals, email_to=journal.alias_id.display_name)
                    self.env['mail.thread'].message_process('account.move', email_raw, custom_values=init_vals)
                case 'journal':
                    journal.create_document_from_attachment(attachments.ids)
                case _:
                    raise ValueError(f"Unknown origin: {origin}")

        return attachment_capturer.records, message_capturer.records, move_capturer.records

    def _get_raw_mail_message_str(self, attachments_vals, email_to, message_id=None):
        """
        :param attachments_vals: list of attachment values.
        :param email_to: string that will fill email_to field in the email, probably you'll want to use some journal alias here.
        :param message_id: Optional. Custom message ID for the email. If not provided, a UUID will be generated.

        Returns:
            Formatted email string.
        """
        if not message_id:
            message_id = str(uuid.uuid4())

        attachment_parts = []
        for attachment in attachments_vals:
            encoded_attachment = base64.b64encode(attachment['raw']).decode()
            attachment_part = textwrap.dedent(f"""\
                --000000000000a47519057e029630
                Content-Type: {attachment['mimetype']}
                Content-Transfer-Encoding: base64
                Content-Disposition: attachment; filename="{attachment['name']}"

                {encoded_attachment}
            """)
            attachment_parts.append(attachment_part)

        email_raw = textwrap.dedent(f"""\
            MIME-Version: 1.0
            Date: Fri, 26 Nov 2021 16:27:45 +0100
            Message-ID: {message_id}
            Subject: Incoming bill
            From: Someone <someone@some.company.com>
            To: {email_to}
            Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

            --000000000000a47519057e029630
            Content-Type: text/plain; charset="UTF-8"

            Here is your requested document(s).
        """)
        email_raw += "\n".join(attachment_parts)
        email_raw += "\n--000000000000a47519057e029630--"
        return email_raw


@tagged('post_install', '-at_install', 'mail_gateway')
class TestAccountIncomingSupplierInvoice(AccountTestInvoicingCommon, TestAccountInvoiceImportMixin, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Disable OCR
        company = cls.company_data['company']
        if 'extract_in_invoice_digitalization_mode' in company._fields:
            company.extract_in_invoice_digitalization_mode = 'no_send'
            company.extract_out_invoice_digitalization_mode = 'no_send'

        cls.internal_user = cls._create_new_internal_user(login='internal.user@test.odoo.com')

        cls.supplier_partner = cls.env['res.partner'].create({
            'name': 'Your Supplier',
            'email': 'supplier@other.company.com',
            'supplier_rank': 10,
        })

        cls.journal = cls.company_data['default_journal_purchase']

        cls.pdf1_vals = {'name': 'invoice1.pdf', **cls._get_dummy_pdf_vals()}
        cls.pdf2_vals = {'name': 'invoice2.pdf', **cls._get_dummy_pdf_vals()}
        cls.pdf3_vals = {'name': 'invoice3.pdf', **cls._get_dummy_pdf_with_embedded_file_vals()}
        cls.gif1_vals = {'name': 'gif1.gif', **cls._get_dummy_gif_vals()}
        cls.gif2_vals = {'name': 'gif2.gif', **cls._get_dummy_gif_vals()}
        cls.xml1_vals = {'name': 'invoice1.xml', **cls._get_dummy_xml_vals()}
        cls.xml2_vals = {'name': 'invoice2.xml', **cls._get_dummy_xml_vals()}
        # These have deliberately similar names to `invoice2.pdf` to test grouping by name similarity
        # when coming from the mail alias.
        cls.docx_vals = {'name': 'invoice2.docx', **cls._get_dummy_docx_vals()}
        cls.xlsx_vals = {'name': 'invoice2.xlsx', **cls._get_dummy_xlsx_vals()}

        cls.all_attachment_vals = [cls.pdf1_vals, cls.pdf2_vals, cls.pdf3_vals, cls.gif1_vals, cls.gif2_vals, cls.xml1_vals, cls.xml2_vals, cls.docx_vals, cls.xlsx_vals]

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    def test_supplier_invoice_mailed_from_supplier(self):
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'message_type': 'email',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.supplier_partner.name, self.supplier_partner.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "You know, that thing that you bought.",
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        self.assertRegex(invoice.name_placeholder, r'BILL/\d{4}/\d{2}/0001')

    def test_supplier_invoice_forwarded_by_internal_user_without_supplier(self):
        """ In this test, the bill was forwarded by an employee,
            but no partner email address is found in the body."""
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'message_type': 'email',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.internal_user.name, self.internal_user.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "You know, that thing that you bought.",
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})
        self.assertFalse(invoice.partner_id)

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        self.assertEqual(invoice.message_partner_ids, self.env.user.partner_id)

    def test_supplier_invoice_forwarded_by_internal_with_supplier_in_body(self):
        """ In this test, the bill was forwarded by an employee,
            and the partner email address is found in the body."""
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'message_type': 'email',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.internal_user.name, self.internal_user.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "Mail sent by %s <%s>:\nYou know, that thing that you bought." % (self.supplier_partner.name, self.supplier_partner.email),
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})
        self.assertEqual(invoice.partner_id, self.supplier_partner)

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        following_partners = invoice.message_follower_ids.mapped('partner_id')
        self.assertEqual(following_partners, self.env.user.partner_id)

    def test_supplier_invoice_forwarded_by_internal_with_internal_in_body(self):
        """ In this test, the bill was forwarded by an employee,
            and the internal user email address is found in the body."""
        message_parsed = {
            'message_id': 'message-id-dead-beef',
            'message_type': 'email',
            'subject': 'Incoming bill',
            'from': '%s <%s>' % (self.internal_user.name, self.internal_user.email),
            'to': '%s@%s' % (self.journal.alias_id.alias_name, self.journal.alias_id.alias_domain),
            'body': "Mail sent by %s <%s>:\nYou know, that thing that you bought." % (self.internal_user.name, self.internal_user.email),
            'attachments': [b'Hello, invoice'],
        }

        invoice = self.env['account.move'].message_new(message_parsed, {'move_type': 'in_invoice', 'journal_id': self.journal.id})
        self.assertEqual(invoice.partner_id, self.internal_user.partner_id)

        message_ids = invoice.message_ids
        self.assertEqual(len(message_ids), 1, 'Only one message should be posted in the chatter')
        self.assertEqual(message_ids.body, '<p>Vendor Bill Created</p>', 'Only the invoice creation should be posted')

        following_partners = invoice.message_follower_ids.mapped('partner_id')
        self.assertEqual(following_partners, self.env.user.partner_id)

    def test_einvoice_notification(self):
        self.company_data['default_journal_purchase'].incoming_einvoice_notification_email = 'oops_another_bill@example.com'

        with self.mock_mail_gateway():
            self.assert_attachment_import(
                origin='mail_alias',
                attachments_vals=[self.pdf1_vals],
                expected_invoices={
                    1: {'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                },
            )

        self.assertSentEmail(
            self.company_data['company'].email_formatted,
            ['oops_another_bill@example.com'],
            subject='New Electronic Invoices Received',
        )

    def test_01_decoder_called(self):
        move = self.env['account.move'].create({'move_type': 'in_invoice'})
        attachment = self.env['ir.attachment'].create(self.xml1_vals)
        with self._patch_import_methods():
            move.message_post(message_type='comment', attachment_ids=attachment.ids)
        self.assertEqual(move.partner_id, self.partner_a)

    def test_02_decoder_not_called_if_invoice_has_lines(self):
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_line_ids': [
                Command.create({
                    'balance': 100,
                })
            ]
        })
        attachment = self.env['ir.attachment'].create(self.xml1_vals)
        with self._patch_import_methods():
            move.message_post(message_type='comment', attachment_ids=attachment.ids)
        self.assertFalse(move.partner_id)

    def test_10_chatter_upload_pdfs(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'is_decoded': True},
                    'invoice2.pdf': {'on_invoice': True},
                }
            },
        )

    def test_11_chatter_message_pdfs(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                }
            },
        )

    def test_12_chatter_email_pdfs(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                }
            },
        )

    def test_13_journal_upload_pdfs(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals],
            expected_invoices={
                1: {'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                2: {'invoice2.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
            },
        )

    def test_14_mail_alias_pdfs(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals],
            expected_invoices={
                1: {'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                2: {'invoice2.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
            },
        )

    def test_20_chatter_upload_pdfs_and_gifs(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals, self.gif1_vals, self.gif2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'is_decoded': True},
                    'invoice2.pdf': {'on_invoice': True},
                    'gif1.gif': {'on_invoice': True},
                    'gif2.gif': {'on_invoice': True},
                },
            },
        )

    def test_21_chatter_message_pdfs_and_gifs(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals, self.gif1_vals, self.gif2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                    'gif1.gif': {'on_message': True},
                    'gif2.gif': {'on_message': True},
                },
            },
        )

    def test_22_chatter_email_pdfs_and_gifs(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals, self.gif1_vals, self.gif2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                    'gif1.gif': {'on_message': True},
                    'gif2.gif': {'on_message': True},
                },
            },
        )

    def test_23_journal_upload_pdfs_and_gifs(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals, self.gif1_vals, self.gif2_vals],
            expected_invoices={
                1: {'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                2: {'invoice2.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                3: {'gif1.gif': {'on_invoice': True, 'on_message': True}},
                4: {'gif2.gif': {'on_invoice': True, 'on_message': True}},
            },
        )

    def test_24_mail_alias_pdfs_and_gifs(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=[self.pdf1_vals, self.pdf2_vals, self.gif1_vals, self.gif2_vals],
            expected_invoices={
                1: {
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True},
                    'gif1.gif': {'on_message': True},
                    'gif2.gif': {'on_message': True},
                },
                2: {'invoice2.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
            },
        )

    def test_30_chatter_upload_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=[self.pdf1_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_invoice': True, 'is_decoded': True},
                    'invoice1.pdf': {'on_invoice': True},
                },
            },
        )

    def test_31_chatter_message_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=[self.pdf1_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True, 'is_decoded': True},
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_32_chatter_email_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=[self.pdf1_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True},
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_33_journal_upload_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=[self.pdf1_vals, self.xml1_vals],
            expected_invoices={
                1: {'invoice1.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                2: {'invoice1.xml': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
            },
        )

    def test_34_mail_alias_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=[self.pdf1_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True, 'is_decoded': True, 'is_new': True},
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_40_chatter_upload_xmls(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=[self.xml1_vals, self.xml2_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_invoice': True, 'is_decoded': True},
                    'invoice2.xml': {'on_invoice': True},
                },
            },
        )

    def test_41_chatter_message_xmls(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=[self.xml1_vals, self.xml2_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True, 'is_decoded': True},
                    'invoice2.xml': {'on_message': True},
                },
            },
        )

    def test_42_chatter_email_xmls(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=[self.xml1_vals, self.xml2_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True},
                    'invoice2.xml': {'on_message': True},
                },
            },
        )

    def test_43_journal_upload_xmls(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=[self.xml1_vals, self.xml2_vals],
            expected_invoices={
                1: {'invoice1.xml': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
                2: {'invoice2.xml': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True}},
            },
        )

    def test_44_mail_alias_xmls(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=[self.xml1_vals, self.xml2_vals],
            expected_invoices={
                1: {'invoice1.xml': {'on_message': True, 'is_decoded': True, 'is_new': True}},
                2: {'invoice2.xml': {'on_message': True, 'is_decoded': True, 'is_new': True}},
            },
        )

    def test_50_chatter_upload_embedded_pdf(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=[self.pdf3_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'embedded.xml': {'is_decoded': True},
                    'invoice3.pdf': {'on_invoice': True},
                    'invoice2.pdf': {'on_invoice': True},
                },
            },
        )

    def test_51_chatter_message_embedded_pdf(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=[self.pdf3_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'embedded.xml': {'is_decoded': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_52_chatter_email_embedded_pdf(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=[self.pdf3_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_53_journal_upload_embedded_pdf(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=[self.pdf3_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'embedded.xml': {'is_decoded': True, 'is_new': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
                2: {
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True},
                },
            },
        )

    def test_54_mail_alias_embedded_pdf(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=[self.pdf3_vals, self.pdf2_vals],
            expected_invoices={
                1: {
                    'embedded.xml': {'is_decoded': True, 'is_new': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
                2: {
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True},
                },
            },
        )

    def test_60_chatter_upload_embedded_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=[self.pdf3_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_invoice': True, 'is_decoded': True},
                    'invoice3.pdf': {'on_invoice': True},
                },
            },
        )

    def test_61_chatter_message_embedded_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=[self.pdf3_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True, 'is_decoded': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_62_chatter_email_embedded_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=[self.pdf3_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_63_journal_upload_embedded_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=[self.pdf3_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'embedded.xml': {'is_decoded': True, 'is_new': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
                2: {
                    'invoice1.xml': {'on_invoice': True, 'on_message': True, 'is_decoded': True, 'is_new': True},
                },
            },
        )

    def test_64_mail_alias_embedded_pdf_and_xml(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=[self.pdf3_vals, self.xml1_vals],
            expected_invoices={
                1: {
                    'invoice1.xml': {'on_message': True, 'is_decoded': True, 'is_new': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
            },
        )

    def test_70_chatter_upload_all(self):
        self.assert_attachment_import(
            origin='chatter_upload',
            attachments_vals=self.all_attachment_vals,
            expected_invoices={
                1: {
                    'invoice2.docx': {'on_invoice': True},
                    'gif1.gif': {'on_invoice': True},
                    'gif2.gif': {'on_invoice': True},
                    'invoice1.pdf': {'on_invoice': True},
                    'invoice2.pdf': {'on_invoice': True},
                    'invoice3.pdf': {'on_invoice': True},
                    'invoice2.xlsx': {'on_invoice': True},
                    # The code doesn't put a hard constraint on which of the XMLs gets decoded.
                    'invoice1.xml': {'is_decoded': True, 'on_invoice': True},
                    'invoice2.xml': {'on_invoice': True}
                },
            },
        )

    def test_71_chatter_message_all(self):
        self.assert_attachment_import(
            origin='chatter_message',
            attachments_vals=self.all_attachment_vals,
            expected_invoices={
                1: {
                    'invoice2.docx': {'on_invoice': True, 'on_message': True},
                    'gif1.gif': {'on_message': True},
                    'gif2.gif': {'on_message': True},
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.xlsx': {'on_invoice': True, 'on_message': True},
                    # The code doesn't put a hard constraint on which of the XMLs gets decoded.
                    'invoice1.xml': {'is_decoded': True, 'on_message': True},
                    'invoice2.xml': {'on_message': True},
                },
            },
        )

    def test_72_chatter_email_all(self):
        self.assert_attachment_import(
            origin='chatter_email',
            attachments_vals=self.all_attachment_vals,
            expected_invoices={
                1: {
                    'invoice2.docx': {'on_invoice': True, 'on_message': True},
                    'gif1.gif': {'on_message': True},
                    'gif2.gif': {'on_message': True},
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.xlsx': {'on_invoice': True, 'on_message': True},
                    'invoice1.xml': {'on_message': True},
                    'invoice2.xml': {'on_message': True},
                },
            },
        )

    def test_73_journal_upload_all(self):
        self.assert_attachment_import(
            origin='journal',
            attachments_vals=self.all_attachment_vals,
            expected_invoices={
                1: {'invoice1.pdf': {'is_decoded': True, 'is_new': True, 'on_invoice': True, 'on_message': True}},
                2: {'invoice2.pdf': {'is_decoded': True, 'is_new': True, 'on_invoice': True, 'on_message': True}},
                3: {
                    'embedded.xml': {'is_decoded': True, 'is_new': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                },
                4: {'gif1.gif': {'on_invoice': True, 'on_message': True}},
                5: {'gif2.gif': {'on_invoice': True, 'on_message': True}},
                6: {'invoice1.xml': {'is_decoded': True, 'is_new': True, 'on_invoice': True, 'on_message': True}},
                7: {'invoice2.xml': {'is_decoded': True, 'is_new': True, 'on_invoice': True, 'on_message': True}},
                8: {'invoice2.docx': {'on_invoice': True, 'on_message': True}},
                9: {'invoice2.xlsx': {'on_invoice': True, 'on_message': True}},
            },
        )

    def test_74_mail_alias_all(self):
        self.assert_attachment_import(
            origin='mail_alias',
            attachments_vals=self.all_attachment_vals,
            expected_invoices={
                1: {
                    'gif1.gif': {'on_message': True},
                    'gif2.gif': {'on_message': True},
                    'invoice1.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice1.xml': {'is_decoded': True, 'is_new': True, 'on_message': True}
                },
                2: {
                    'invoice2.pdf': {'on_invoice': True, 'on_message': True},
                    'invoice2.xml': {'is_decoded': True, 'is_new': True, 'on_message': True},
                    # The XLSX and DOCX are attached to this invoice due to filename similarity
                    'invoice2.xlsx': {'on_invoice': True, 'on_message': True},
                    'invoice2.docx': {'on_invoice': True, 'on_message': True},
                },
                3: {
                    'embedded.xml': {'is_decoded': True, 'is_new': True},
                    'invoice3.pdf': {'on_invoice': True, 'on_message': True},
                }
            },
        )
