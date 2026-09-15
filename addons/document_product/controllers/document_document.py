import json
import logging

from odoo import _
from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ProductDocumentsController(Controller):
    @route("/product/document/upload", type="http", methods=["POST"], auth="user")
    def upload_document(self, ufile, res_model, res_id, **kwargs):
        if not self.is_model_valid(res_model):
            _debug.logic("upload_refused", reason="bad_model", res_model=res_model)
            return self._error_response(
                _("Documents cannot be attached to this model.")
            )

        try:
            res_id = int(res_id)
        except ValueError, TypeError:
            _debug.logic("upload_refused", reason="bad_res_id")
            return self._error_response(_("Invalid record id."))

        record = request.env[res_model].browse(res_id).exists()

        if not record or not record.has_access("write"):
            _debug.logic("upload_refused", reason="no_write_access", record=record)
            return self._error_response(
                _("You are not allowed to attach documents to this record.")
            )

        files = request.httprequest.files.getlist("ufile")
        _debug.pipeline("product_upload", record=record, files=len(files))
        failed = []
        for file in files:
            try:
                with request.env.cr.savepoint():
                    request.env["document.document"].create(
                        {
                            "name": file.filename,
                            "res_model": record._name,
                            "res_id": record.id,
                            "company_id": record.company_id.id,
                            "mimetype": file.content_type,
                            "raw": file.read(),
                            **self._prepare_additional_document_vals(**kwargs),
                        }
                    )
            except Exception:
                _debug.logic("product_upload_failed", record=record)
                logger.exception("Failed to upload document %s", file.filename)
                failed.append(file.filename or _("unnamed file"))

        if failed:
            _debug.logic("product_upload_partial", failed=len(failed), files=len(files))
            if len(failed) == len(files):
                message = _("No file could be uploaded.")
            else:
                message = _("Some files could not be uploaded: %s", ", ".join(failed))
            return request.prepare_json_response(self._error_result(message))
        return request.prepare_json_response({"success": _("All files uploaded")})

    @staticmethod
    def _error_result(message):
        return {"error": {"message": message}}

    def _error_response(self, message):
        return json.dumps(self._error_result(message))

    def _prepare_additional_document_vals(self, **kwargs):
        return {}

    def is_model_valid(self, res_model):
        return res_model in ("product.product", "product.template")
