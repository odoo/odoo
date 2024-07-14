# -*- coding: utf-8 -*-

from odoo import _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.documents.controllers.documents import ShareRoute

class SpreadsheetShareRoute(ShareRoute):

    @classmethod
    def _get_downloadable_documents(cls, documents):
        """
            override of documents to prevent the download
            of spreadsheets binary as they are not usable
        """
        return super()._get_downloadable_documents(documents.filtered(lambda doc: doc.mimetype != "application/o-spreadsheet"))

    def _create_uploaded_documents(self, *args, **kwargs):
        documents = super()._create_uploaded_documents(*args, **kwargs)
        if any(doc.handler == "spreadsheet" for doc in documents):
            raise AccessError(_("You cannot upload spreadsheets in a shared folder"))
        return documents

    @classmethod
    def _get_share_zip_data_stream(cls, share, document):
        if document.handler == "spreadsheet":
            spreadsheet_copy = share.freezed_spreadsheet_ids.filtered(
                lambda s: s.document_id == document
            )
            try:
                return request.env["ir.binary"]._get_stream_from(
                    spreadsheet_copy, "excel_export", filename=document.name
                )
            except MissingError:
                return False
        return super()._get_share_zip_data_stream(share, document)
