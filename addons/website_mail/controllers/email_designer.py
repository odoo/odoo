# -*- coding: utf-8 -*-

import io
from PIL import Image, ImageFont, ImageDraw
import werkzeug.wrappers

from openerp import addons
from openerp.addons.web import http
from openerp.addons.web.http import request
import time


class WebsiteEmailDesigner(http.Controller):

    @http.route(['/website_mail/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website_mail.email_designer_snippets')

    @http.route([
        '/website_mail/font_to_img/<icon>',
        '/website_mail/font_to_img/<icon>/<color>',
        '/website_mail/font_to_img/<icon>/<color>/<int:size>',
        '/website_mail/font_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        ], auth="public", website=True)
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


class Website(addons.website.controllers.main.Website):

    #------------------------------------------------------
    # Backend email template field
    #------------------------------------------------------
    @http.route('/website_mail/field/email', type='http', auth="user", website=True)
    def FieldTextHtmlEmail(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['template'] = "website_mail.FieldTextHtmlEmail"
        return self.FieldTextHtml(model, res_id, field, callback, **kwargs)

    @http.route('/website_mail/field/email_template', type='http', auth="user", website=True)
    def FieldTextHtmlEmailTemplate(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        kwargs['theme'] = True
        kwargs['snippets'] = 'snippets' not in kwargs and '/website_mail/snippets' or kwargs['snippets']
        kwargs['dont_load_assets'] = not kwargs.get('enable_editor')
        return self.FieldTextHtmlEmail(model, res_id, field, callback, **kwargs)
