from odoo import http
from base64 import b64encode
import json

class OwlValid(http.Controller):
    @http.route('/filepond/process', type='http', auth='user', methods=["POST"], csrf=False)
    def filepond_process(self):
        print("request", http.request.params)
        filepond = http.request.params.get("filepond")
        print("filepond", filepond.filename, filepond.content_type)

        file = b64encode(filepond.read())
        ir_attachment = http.request.env["ir.attachment"]
        attachment = ir_attachment.create({
            'name': filepond.filename,
            'datas': file,
        })
        print("attachment", attachment)
        if not attachment:
            return False
        return str(attachment.id)

    @http.route('/filepond/revert', type='http', auth='user', methods=["DELETE"], csrf=False)
    def filepond_revert(self):
        print("request", json.loads(http.request.httprequest.data))
        id = json.loads(http.request.httprequest.data)

        ir_attachment = http.request.env["ir.attachment"]
        attachment = ir_attachment.search([('id', '=', id)])
        print("attachment", attachment)

        if attachment:
            attachment.unlink()
        return ""