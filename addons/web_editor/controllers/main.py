# -*- coding: utf-8 -*-
from openerp.http import request, STATIC_CACHE
from openerp.addons.web import http
import json
import io
from PIL import Image, ImageFont, ImageDraw
from openerp import tools
import cStringIO
import werkzeug.wrappers
import time
import logging
logger = logging.getLogger(__name__)


class Web_Editor(http.Controller):
    #------------------------------------------------------
    # Backend snippet
    #------------------------------------------------------
    @http.route('/web_editor/snippets', type='json', auth="user")
    def snippets(self, **kwargs):
        return request.registry["ir.ui.view"].render(request.cr, request.uid, 'web_editor.snippets', None, context=request.context)

    #------------------------------------------------------
    # Backend html field
    #------------------------------------------------------
    @http.route('/web_editor/field/html', type='http', auth="user")
    def FieldTextHtml(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context

        kwargs.update(
            model=model,
            res_id=res_id,
            field=field,
            datarecord=json.loads(kwargs['datarecord']),
            debug='debug' in kwargs)

        for k in kwargs:
            if isinstance(kwargs[k], basestring) and kwargs[k].isdigit():
                kwargs[k] = int(kwargs[k])

        trans = dict(
            lang=kwargs.get('lang', context.get('lang')),
            translatable=kwargs.get('translatable'),
            edit_translations=kwargs.get('edit_translations'),
            editable=kwargs.get('enable_editor'))

        context.update(trans)
        kwargs.update(trans)

        record = None
        if model and kwargs.get('res_id'):
            record = request.registry[model].browse(cr, uid, kwargs.get('res_id'), context)

        kwargs.update(content=record and getattr(record, field) or "")

        return request.render(kwargs.get("template") or "web_editor.FieldTextHtml", kwargs, uid=request.uid)

    #------------------------------------------------------
    # Backend html field in inline mode
    #------------------------------------------------------
    @http.route('/web_editor/field/html/inline', type='http', auth="user")
    def FieldTextHtmlInline(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['inline_mode'] = True
        kwargs['dont_load_assets'] = not kwargs.get('enable_editor') and not kwargs.get('edit_translations')
        return self.FieldTextHtml(model, res_id, field, callback, **kwargs)

    #------------------------------------------------------
    # convert font into picture
    #------------------------------------------------------
    @http.route([
        '/web_editor/font_to_img/<icon>',
        '/web_editor/font_to_img/<icon>/<color>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        ], type='http', auth="none")
    def export_icon_to_png(self, icon, color='#000', size=100, alpha=255, font='/web/static/lib/fontawesome/fonts/fontawesome-webfont.ttf'):
        """ This method converts FontAwesom pictograms to Images and is Used only
            for mass mailing becuase custom fonts are not supported in mail.
            :param icon : character from FontAwesom cheatsheet
            :param color : RGB code of the color
            :param size : Pixels in integer
            :param alpha : transparency of the image from 0 to 255
            :param font : font path

            :returns PNG image converted from given font
        """
        # Initialize font
        addons_path = http.addons_manifest['web']['addons_path']
        font_obj = ImageFont.truetype(addons_path + font, size)

        # Determine the dimensions of the icon
        image = Image.new("RGBA", (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        boxw, boxh = draw.textsize(icon, font=font_obj)
        draw.text((0, 0), icon, font=font_obj)
        left, top, right, bottom = image.getbbox()

        # Create an alpha mask
        imagemask = Image.new("L", (boxw, boxh), 0)
        drawmask = ImageDraw.Draw(imagemask)
        drawmask.text((-left, -top), icon, font=font_obj, fill=alpha)

        # Create a solid color image and apply the mask
        if color.startswith('rgba'):
            color = color.replace('rgba', 'rgb')
            color = ','.join(color.split(',')[:-1])+')'
        iconimage = Image.new("RGBA", (boxw, boxh), color)
        iconimage.putalpha(imagemask)

        # Create output image
        outimage = Image.new("RGBA", (boxw, size), (0, 0, 0, 0))
        outimage.paste(iconimage, (left, top))

        # output image
        output = io.BytesIO()
        outimage.save(output, format="PNG")
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/png'
        response.data = output.getvalue()
        response.headers['Cache-Control'] = 'public, max-age=604800'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        response.headers['Connection'] = 'close'
        response.headers['Date'] = time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime())
        response.headers['Expires'] = time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(time.time()+604800*60))

        return response

    #------------------------------------------------------
    # add attachment (images or link)
    #------------------------------------------------------
    @http.route('/web_editor/attachment/add', type='http', auth='user', methods=['POST'])
    def attach(self, func, upload=None, url=None, disable_optimization=None, **kwargs):
        # the upload argument doesn't allow us to access the files if more than
        # one file is uploaded, as upload references the first file
        # therefore we have to recover the files from the request object
        Attachments = request.registry['ir.attachment']  # registry for the attachment table

        uploads = []
        message = None
        if not upload: # no image provided, storing the link and the image name
            name = url.split("/").pop()                       # recover filename
            attachment_id = Attachments.create(request.cr, request.uid, {
                'name': name,
                'type': 'url',
                'url': url,
                'public': True,
                'res_model': 'ir.ui.view',
            }, request.context)
            uploads += Attachments.read(request.cr, request.uid, [attachment_id], ['name', 'mimetype', 'checksum', 'url'], request.context)
        else:                                                  # images provided
            try:
                attachment_ids = []
                for c_file in request.httprequest.files.getlist('upload'):
                    data = c_file.read()
                    try:
                        image = Image.open(cStringIO.StringIO(data))
                        w, h = image.size
                        if w*h > 42e6: # Nokia Lumia 1020 photo resolution
                            raise ValueError(
                                u"Image size excessive, uploaded images must be smaller "
                                u"than 42 million pixel")
                        if not disable_optimization and image.format in ('PNG', 'JPEG'):
                            data = tools.image_save_for_web(image)
                    except IOError, e:
                        pass

                    attachment_id = Attachments.create(request.cr, request.uid, {
                        'name': c_file.filename,
                        'datas': data.encode('base64'),
                        'datas_fname': c_file.filename,
                        'public': True,
                        'res_model': 'ir.ui.view',
                    }, request.context)
                    attachment_ids.append(attachment_id)
                uploads += Attachments.read(request.cr, request.uid, attachment_ids, ['name', 'mimetype', 'checksum', 'url'], request.context)
            except Exception, e:
                logger.exception("Failed to upload image to attachment")
                message = unicode(e)

        return """<script type='text/javascript'>
            window.parent['%s'](%s, %s);
        </script>""" % (func, json.dumps(uploads), json.dumps(message))

    #------------------------------------------------------
    # remove attachment (images or link)
    #------------------------------------------------------
    @http.route('/web_editor/attachment/remove', type='json', auth='user')
    def remove(self, ids, **kwargs):
        """ Removes a web-based image attachment if it is used by no view (template)

        Returns a dict mapping attachments which would not be removed (if any)
        mapped to the views preventing their removal
        """
        cr, uid, context = request.cr, request.uid, request.context
        Attachment = request.registry['ir.attachment']
        Views = request.registry['ir.ui.view']

        attachments_to_remove = []
        # views blocking removal of the attachment
        removal_blocked_by = {}

        for attachment in Attachment.browse(cr, uid, ids, context=context):
            # in-document URLs are html-escaped, a straight search will not
            # find them
            url = tools.html_escape(attachment.local_url)
            ids = Views.search(cr, uid, ["|", ('arch_db', 'like', '"%s"' % url), ('arch_db', 'like', "'%s'" % url)], context=context)

            if ids:
                removal_blocked_by[attachment.id] = Views.read(
                    cr, uid, ids, ['name'], context=context)
            else:
                attachments_to_remove.append(attachment.id)
        if attachments_to_remove:
            Attachment.unlink(cr, uid, attachments_to_remove, context=context)
        return removal_blocked_by
