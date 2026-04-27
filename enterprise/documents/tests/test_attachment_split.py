import base64
import io

from odoo.tests.common import TransactionCase
from odoo.tools.pdf import OdooPdfFileWriter, OdooPdfFileReader

class TestAttachmentSplit(TransactionCase):

    def _create_attachment(self, pages, attachments=None):
        """
        Create a PDF with the specified number of pages and attachments.

        :param pages: Number of blank pages to add to the PDF.
        :param attachments: List of tuples (name, content) for the attachments.
        :return: BytesIO stream of the generated PDF.
        """
        writer = OdooPdfFileWriter()
        for _ in range(pages):
            writer.addBlankPage(width=200, height=200)

        if attachments:
            for name, content in attachments:
                writer.addAttachment(name, content)

        stream = io.BytesIO()
        writer.write(stream)
        return self.env['ir.attachment'].create({
            'name': 'Test PDF with Attachment',
            'datas': base64.b64encode(stream.getvalue()),
            'mimetype': 'application/pdf',
        })

    def test_attachment_retention_no_split(self):
        """Test that attachments are retained when the PDF is split to produce the same original file."""
        attachment = self._create_attachment(2, [("test_attachment.txt", b"Sample content for attachment")])

        open_file = io.BytesIO(base64.b64decode(attachment.datas))

        # Define the new_files structure to reproduce the original PDF
        new_files = [{
            'name': 'Original File',
            'new_pages': [
                {'old_file_index': 0, 'old_page_number': 1},
                {'old_file_index': 0, 'old_page_number': 2},
            ],
        }]

        # Call the _pdf_split method
        new_attachments = attachment._pdf_split(
            new_files=new_files,
            open_files=[open_file],
        )

        # Ensure the new PDF has the same attachment
        self.assertEqual(len(new_attachments), 1, "Should produce one new PDF attachment.")
        new_attachment = new_attachments[0]
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachment.datas)))
        attachments = list(pdf_reader.getAttachments())

        # Check that the attachment is retained
        self.assertEqual(len(attachments), 1, "New PDF should have 1 attachment.")
        self.assertEqual(attachments[0][0], "test_attachment.txt", "Attachment name should match.")

    def test_attachment_removal_on_split(self):
        """Test that attachments are removed when the PDF is split."""

        attachment = self._create_attachment(2, [("test_attachment.txt", b"Sample content for attachment")])
        open_file = io.BytesIO(base64.b64decode(attachment.datas))

        # Define the new_files structure to split the PDF
        new_files = [{
            'name': 'Page 1',
            'new_pages': [{'old_file_index': 0, 'old_page_number': 1}],
        }, {
            'name': 'Page 2',
            'new_pages': [{'old_file_index': 0, 'old_page_number': 2}],
        }]

        # Call the _pdf_split method
        new_attachments = attachment._pdf_split(
            new_files=new_files,
            open_files=[open_file],
        )
        self.assertEqual(len(new_attachments), 2, f"The pdf should be splitted.")
        # Ensure the new PDFs do not have attachments
        for i, new_attachment in enumerate(new_attachments):
            pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachment.datas)))
            attachments = list(pdf_reader.getAttachments())
            self.assertEqual(len(attachments), 0, f"Attachment {i + 1} should have no attachments.")

    def test_attachment_count(self):
        attachment_1 = self._create_attachment(2, [
            ("test_attachment1.txt", b"Sample content for attachment"),
            ("test_attachment2.txt", b"Sample content for attachment")
        ])

        attachment_2 = self._create_attachment(3, [
            ("test_attachment3.txt", b"Sample content for attachment")
        ])

        new_files = [{
            'name': 'Original File',
            'new_pages': [
                {'old_file_index': 0, 'old_page_number': 1},
                {'old_file_index': 0, 'old_page_number': 2},
                {'old_file_index': 1, 'old_page_number': 1},
                {'old_file_index': 1, 'old_page_number': 2},
                {'old_file_index': 1, 'old_page_number': 3},
            ],
        }]
        new_attachments = (attachment_1 | attachment_2)._pdf_split(
            new_files=new_files,
            open_files=[io.BytesIO(base64.b64decode(attachment_1.datas)), io.BytesIO(base64.b64decode(attachment_2.datas))],
        )

        self.assertEqual(len(new_attachments), 1)
        new_attachment = new_attachments[0]
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachment.datas)))
        attachments = list(pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 3)

        new_files = [{
            'name': 'Original File',
            'new_pages': [
                {'old_file_index': 0, 'old_page_number': 2},
                {'old_file_index': 1, 'old_page_number': 1},
                {'old_file_index': 1, 'old_page_number': 2},
                {'old_file_index': 1, 'old_page_number': 3},
            ],
        }]
        new_attachments = (attachment_1 | attachment_2)._pdf_split(
            new_files=new_files,
            open_files=[io.BytesIO(base64.b64decode(attachment_1.datas)), io.BytesIO(base64.b64decode(attachment_2.datas))],
        )
        self.assertEqual(len(new_attachments), 1)
        new_attachment = new_attachments[0]
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachment.datas)))
        attachments = list(pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 1)

    def test_merge_pdfs_with_mixed_attachments(self):
        """Test merging multiple PDFs with different numbers of attachments."""
        # First PDF with 2 pages and 2 attachments
        attachment_1 = self._create_attachment(2, [
            ("test_attachment1.txt", b"Sample content for attachment"),
            ("test_attachment2.txt", b"Sample content for attachment")
        ])

        # Second PDF with 1 page and 1 attachment
        attachment_2 = self._create_attachment(1, [
            ("test_attachment3.txt", b"Sample content for attachment")
        ])

        # Third PDF with 1 page and no attachments
        attachment_3 = self._create_attachment(1, [])

        # Test merging all PDFs
        new_files = [{
            'name': 'Merged Complete',
            'new_pages': [
                {'old_file_index': 0, 'old_page_number': 1},
                {'old_file_index': 0, 'old_page_number': 2},
                {'old_file_index': 1, 'old_page_number': 1},
                {'old_file_index': 2, 'old_page_number': 1},
            ],
        }]
        new_attachments = (attachment_1 | attachment_2 | attachment_3)._pdf_split(
            new_files=new_files,
            open_files=[
                io.BytesIO(base64.b64decode(attachment_1.datas)),
                io.BytesIO(base64.b64decode(attachment_2.datas)),
                io.BytesIO(base64.b64decode(attachment_3.datas)),
            ],
        )
        self.assertEqual(len(new_attachments), 1)
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachments[0].datas)))
        attachments = list(pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 3, "Should keep all attachments when merging with all pages")

    def test_split_pdf_with_multiple_attachments(self):
        """Test splitting a PDF that has multiple attachments."""
        # Create PDF with 3 pages and 2 attachments
        attachment = self._create_attachment(3, [
            ("test_attachment1.txt", b"Sample content for attachment"),
            ("test_attachment2.txt", b"Sample content for attachment")
        ])

        # Test splitting into three parts
        new_files = [
            {
                'name': 'Part 1',
                'new_pages': [{'old_file_index': 0, 'old_page_number': 1}],
            },
            {
                'name': 'Part 2',
                'new_pages': [{'old_file_index': 0, 'old_page_number': 2}],
            },
            {
                'name': 'Part 3',
                'new_pages': [{'old_file_index': 0, 'old_page_number': 3}],
            }
        ]
        new_attachments = attachment._pdf_split(
            new_files=new_files,
            open_files=[io.BytesIO(base64.b64decode(attachment.datas))],
        )
        self.assertEqual(len(new_attachments), 3)
        for new_attachment in new_attachments:
            pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachment.datas)))
            attachments = list(pdf_reader.getAttachments())
            self.assertEqual(len(attachments), 0, "Split PDFs should have no attachments")

    def test_partial_merge_attachment_handling(self):
        """Test merging PDFs but only using some pages from each."""
        # First PDF with 2 pages and 1 attachment
        attachment_1 = self._create_attachment(2, [
            ("test_attachment1.txt", b"Sample content for attachment"),
        ])

        # Second PDF with 3 pages and 1 attachment
        attachment_2 = self._create_attachment(3, [
            ("test_attachment1.txt", b"Sample content for attachment"),
        ])

        # Test partial merge - using only some pages from each PDF
        new_files = [{
            'name': 'Partial Merge',
            'new_pages': [
                {'old_file_index': 0, 'old_page_number': 1},  # Missing page 2 from first PDF
                {'old_file_index': 1, 'old_page_number': 1},
                {'old_file_index': 1, 'old_page_number': 2},
                {'old_file_index': 1, 'old_page_number': 3},
            ],
        }]
        new_attachments = (attachment_1 | attachment_2)._pdf_split(
            new_files=new_files,
            open_files=[
                io.BytesIO(base64.b64decode(attachment_1.datas)),
                io.BytesIO(base64.b64decode(attachment_2.datas)),
            ],
        )
        self.assertEqual(len(new_attachments), 1)
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(new_attachments[0].datas)))
        attachments = list(pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 1, "Should only keep attachment from PDF with all pages included")

    def test_split_pdf_retains_attachments_for_complete_files(self):
        """Test that splitting a PDF retains attachments when all pages of the PDF are in one output file."""
        # Create a PDF with 3 pages and 2 attachments
        attachment = self._create_attachment(3, [
            ("test_attachment1.txt", b"Sample content for attachment"),
            ("test_attachment2.txt", b"Sample content for attachment")
        ])

        # Define the split where one output file contains all pages of the original PDF
        new_files = [
            {
                'name': 'Complete File',
                'new_pages': [
                    {'old_file_index': 0, 'old_page_number': 1},
                    {'old_file_index': 0, 'old_page_number': 2},
                    {'old_file_index': 0, 'old_page_number': 3},
                ],
            },
            {
                'name': 'Empty File',
                'new_pages': [],
            }
        ]

        # Perform the split
        new_attachments = attachment._pdf_split(
            new_files=new_files,
            open_files=[io.BytesIO(base64.b64decode(attachment.datas))],
        )

        # Assert that there are two new attachments
        self.assertEqual(len(new_attachments), 2)

        # Check the first output file (complete file)
        complete_file_attachment = new_attachments[0]
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(complete_file_attachment.datas)))
        attachments = list(pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 2, "Complete file should retain all attachments from the original PDF")

        # Check the second output file (empty file)
        empty_file_attachment = new_attachments[1]
        pdf_reader = OdooPdfFileReader(io.BytesIO(base64.b64decode(empty_file_attachment.datas)))
        attachments = list(pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 0, "Empty file should not contain any attachments")
