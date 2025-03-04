import json
import unicodedata
from odoo import _, http
from odoo.addons.web.controllers.binary import clean, _logger
from odoo.exceptions import AccessError
from odoo.http import request

class ProjectSharingCoverImg(http.Controller):

    @http.route('/project/controllers/upload_attachment', type='http', auth="user")
    def upload_attachment(self, model, id, ufile, callback=None):
        files = request.httprequest.files.getlist('ufile')
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        args = []
        for ufile in files:

            filename = ufile.filename
            if request.httprequest.user_agent.browser == 'safari':
                # Safari sends NFD UTF-8 (where é is composed by 'e' and [accent])
                # we need to send it the same stuff, otherwise it'll fail
                filename = unicodedata.normalize('NFD', ufile.filename)

            try:
                attachment =  self.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'raw': ufile.read(),
                    'res_model': model,
                    'res_id': int(id),
                    'public':True,
                })
            except AccessError:
                args.append({'error': _("You are not allowed to upload an attachment here.")})
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s", ufile.filename)
            else:  
                args.append({
                    'filename': clean(filename),
                    'mimetype': attachment.mimetype,
                    'id': attachment.id,
                    'size': attachment.file_size
                })
        return out % (json.dumps(clean(callback)), json.dumps(args)) if callback else json.dumps(args)

    @http.route('/project/controllers/set_attachment', type='jsonrpc', auth="user")
    def set_attachment(self, model, field, task_id, attachment_id, callback=None):
        try:
            task =  self.env[model].sudo().browse(int(task_id))
            task.write({
                field : attachment_id 
            })
            return { 'status': 'success' }
        except Exception:
            return { 'status': 'error' }

    @http.route('/project/controllers/get_attachment', type='jsonrpc', auth="user")
    def get_attachment(self, model, id, callback=None):
        attachments =  self.env['ir.attachment'].sudo().search_read(
                [
                    ("res_model", "=", model),
                    ("res_id", "=", int(id)),
                    ("mimetype", "ilike", "image"),
                ],
                ["id"]
        )
        return {
            'attachments': attachments,
        }
