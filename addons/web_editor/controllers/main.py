# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json
import logging
import re
import time
import requests
from PIL import Image, ImageFont, ImageDraw
from lxml import etree
from base64 import b64decode
from math import floor
from os.path import join as opj
from hashlib import sha256

from odoo.http import request, Response
from odoo import http, tools, _
from odoo.tools.misc import file_open


logger = logging.getLogger(__name__)
DEFAULT_LIBRARY_ENDPOINT = 'https://media-api.odoo.com'
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'


def get_existing_attachment(IrAttachment, vals):
    """
    Check if an attachment already exists for the same vals. Return it if
    so, None otherwise.
    """
    fields = dict(vals)
    # Falsy res_id defaults to 0 on attachment creation.
    fields['res_id'] = fields.get('res_id') or 0
    raw, datas = fields.pop('raw', None), fields.pop('datas', None)
    domain = [(field, '=', value) for field, value in fields.items()]
    if fields.get('type') == 'url':
        if 'url' not in fields:
            return None
        domain.append(('checksum', '=', False))
    else:
        if not (raw or datas):
            return None
        domain.append(('checksum', '=', IrAttachment._compute_checksum(raw or b64decode(datas))))
    return IrAttachment.search(domain, limit=1) or None

class Web_Editor(http.Controller):
    #------------------------------------------------------
    # convert font into picture
    #------------------------------------------------------
    @http.route([
        '/web_editor/font_to_img/<icon>',
        '/web_editor/font_to_img/<icon>/<color>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>',
        '/web_editor/font_to_img/<icon>/<color>/<int:width>x<int:height>',
        '/web_editor/font_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        '/web_editor/font_to_img/<icon>/<color>/<int:width>x<int:height>/<int:alpha>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>/<int:size>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>',
        '/web_editor/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>/<int:alpha>',
        ], type='http', auth="none")
    def export_icon_to_png(self, icon, color='#000', bg=None, size=100, alpha=255, font='/web/static/src/libs/fontawesome/fonts/fontawesome-webfont.ttf', width=None, height=None):
        """ This method converts an unicode character to an image (using Font
            Awesome font by default) and is used only for mass mailing because
            custom fonts are not supported in mail.
            :param icon : decimal encoding of unicode character
            :param color : RGB code of the color
            :param bg : RGB code of the background color
            :param size : Pixels in integer
            :param alpha : transparency of the image from 0 to 255
            :param font : font path
            :param width : Pixels in integer
            :param height : Pixels in integer

            :returns PNG image converted from given font
        """
        # For custom icons, use the corresponding custom font
        if icon.isdigit():
            oi_font_char_codes = [
                # Replacement of existing Twitter icons by X icons (the route
                # here receives the old icon code always, but the replacement
                # one is also considered for consistency anyway).
                ("61569", "59464"),  # F081 -> E848: fa-twitter-square
                ("61593", "59418"),  # F099 -> E81A: fa-twitter

                # Addition of new icons
                "59407",  # E80F: fa-strava
                "59409",  # E811: fa-discord
                "59416",  # E818: fa-threads
                "59417",  # E819: fa-kickstarter
                "59419",  # E81B: fa-tiktok
                "59420",  # E81C: fa-bluesky
                "59421",  # E81D: fa-google-play
            ]
            for data in oi_font_char_codes:
                old_and_new_char_codes = data if isinstance(data, tuple) else (data, data)
                if icon in old_and_new_char_codes:
                    icon = old_and_new_char_codes[-1]
                    font = "/web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff"
                    break

        size = max(width, height, 1) if width else size
        width = width or size
        height = height or size
        # Make sure we have at least size=1
        width = max(1, min(width, 512))
        height = max(1, min(height, 512))
        # Initialize font
        if font.startswith('/'):
            font = font[1:]
        font_obj = ImageFont.truetype(file_open(font, 'rb'), height)

        # if received character is not a number, keep old behaviour (icon is character)
        icon = chr(int(icon)) if icon.isdigit() else icon

        # Background standardization
        if bg is not None and bg.startswith('rgba'):
            bg = bg.replace('rgba', 'rgb')
            bg = ','.join(bg.split(',')[:-1])+')'

        # Convert the opacity value compatible with PIL Image color (0 to 255)
        # when color specifier is 'rgba'
        if color is not None and color.startswith('rgba'):
            *rgb, a = color.strip(')').split(',')
            opacity = str(floor(float(a) * 255))
            color = ','.join([*rgb, opacity]) + ')'

        # Determine the dimensions of the icon
        image = Image.new("RGBA", (width, height), color)
        draw = ImageDraw.Draw(image)

        if hasattr(draw, 'textbbox'):
            box = draw.textbbox((0, 0), icon, font=font_obj)
            left = box[0]
            top = box[1]
            boxw = box[2] - box[0]
            boxh = box[3] - box[1]
        else:  # pillow < 8.00 (Focal)
            left, top, _right, _bottom = image.getbbox()
            boxw, boxh = draw.textsize(icon, font=font_obj)

        draw.text((0, 0), icon, font=font_obj)

        # Create an alpha mask
        imagemask = Image.new("L", (boxw, boxh), 0)
        drawmask = ImageDraw.Draw(imagemask)
        drawmask.text((-left, -top), icon, font=font_obj, fill=255)

        # Create a solid color image and apply the mask
        if color.startswith('rgba'):
            color = color.replace('rgba', 'rgb')
            color = ','.join(color.split(',')[:-1])+')'
        iconimage = Image.new("RGBA", (boxw, boxh), color)
        iconimage.putalpha(imagemask)

        # Create output image
        outimage = Image.new("RGBA", (boxw, height), bg or (0, 0, 0, 0))
        outimage.paste(iconimage, (left, top), iconimage)

        # output image
        output = io.BytesIO()
        outimage.save(output, format="PNG")
        response = Response()
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
    # Update a checklist in the editor on check/uncheck
    #------------------------------------------------------
    @http.route('/web_editor/checklist', type='jsonrpc', auth='user')
    def update_checklist(self, res_model, res_id, filename, checklistId, checked, **kwargs):
        record = request.env[res_model].browse(res_id)
        value = filename in record._fields and record.read([filename])[0][filename]
        htmlelem = etree.fromstring("<div>%s</div>" % value, etree.HTMLParser())
        checked = bool(checked)

        li = htmlelem.find(".//li[@id='checkId-%s']" % checklistId)

        if li is None:
            return value

        classname = li.get('class', '')
        if ('o_checked' in classname) != checked:
            if checked:
                classname = '%s o_checked' % classname
            else:
                classname = re.sub(r"\s?o_checked\s?", '', classname)
            li.set('class', classname)
        else:
            return value

        value = etree.tostring(htmlelem[0][0], encoding='utf-8', method='html')[5:-6].decode("utf-8")
        record.write({filename: value})

        return value

    #------------------------------------------------------
    # Update a stars rating in the editor on check/uncheck
    #------------------------------------------------------
    @http.route('/web_editor/stars', type='jsonrpc', auth='user')
    def update_stars(self, res_model, res_id, filename, starsId, rating):
        record = request.env[res_model].browse(res_id)
        value = filename in record._fields and record.read([filename])[0][filename]
        htmlelem = etree.fromstring("<div>%s</div>" % value, etree.HTMLParser())

        stars_widget = htmlelem.find(".//span[@id='checkId-%s']" % starsId)

        if stars_widget is None:
            return value

        # Check the `rating` first stars and uncheck the others if any.
        stars = []
        for star in stars_widget.getchildren():
            if 'fa-star' in star.get('class', ''):
                stars.append(star)
        star_index = 0
        for star in stars:
            classname = star.get('class', '')
            if star_index < rating and (not 'fa-star' in classname or 'fa-star-o' in classname):
                classname = re.sub(r"\s?fa-star-o\s?", '', classname)
                classname = '%s fa-star' % classname
                star.set('class', classname)
            elif star_index >= rating and not 'fa-star-o' in classname:
                classname = re.sub(r"\s?fa-star\s?", '', classname)
                classname = '%s fa-star-o' % classname
                star.set('class', classname)
            star_index += 1

        value = etree.tostring(htmlelem[0][0], encoding='utf-8', method='html')[5:-6]
        record.write({filename: value})

        return value

    @http.route('/web_editor/tests', type='http', auth="user")
    def test_suite(self, mod=None, **kwargs):
        return request.render('web_editor.tests')

    @http.route("/web_editor/field/translation/update", type="jsonrpc", auth="user", website=True)
    def update_field_translation(self, model, record_id, field_name, translations):
        record = request.env[model].browse(record_id)
        field = record._fields[field_name]
        source_lang = None
        if callable(field.translate):
            for translation in translations.values():
                for key, value in translation.items():
                    translation[key] = field.translate.term_converter(value)
            source_lang = record._get_base_lang()
        return record._update_field_translations(field_name, translations, lambda old_term: sha256(old_term.encode()).hexdigest(), source_lang=source_lang)
