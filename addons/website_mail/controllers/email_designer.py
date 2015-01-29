# -*- coding: utf-8 -*-

import io
from PIL import Image, ImageFont, ImageDraw
from urllib import urlencode
import werkzeug.wrappers

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.mail import html_sanitize


class WebsiteEmailDesigner(http.Controller):

    @http.route('/website_mail/email_designer', type='http', auth="user", website=True)
    def index(self, model, res_id, action=None, template_model=None, **kw):
        if not model or not model in request.registry or not res_id:
            return request.redirect('/')
        model_fields = request.registry[model]._fields
        if 'body' not in model_fields and 'body_html' not in model_fields or \
           'email' not in model_fields and 'email_from' not in model_fields or \
           'name' not in model_fields and 'subject' not in model_fields:
            return request.redirect('/')
        res_id = int(res_id)
        obj_ids = request.registry[model].exists(request.cr, request.uid, [res_id], context=request.context)
        if not obj_ids:
            return request.redirect('/')
        # try to find fields to display / edit -> as t-field is static, we have to limit
        # the available fields to a given subset
        email_from_field = 'email'
        if 'email_from' in model_fields:
            email_from_field = 'email_from'
        subject_field = 'name'
        if 'subject' in model_fields:
            subject_field = 'subject'
        body_field = 'body'
        if 'body_html' in model_fields:
            body_field = 'body_html'

        cr, uid, context = request.cr, request.uid, request.context
        record = request.registry[model].browse(cr, uid, res_id, context=context)
        values = {
            'record': record,
            'templates': None,
            'model': model,
            'res_id': res_id,
            'email_from_field': email_from_field,
            'subject_field': subject_field,
            'body_field': body_field,
            'action': action,
        }

        if getattr(record, body_field) or kw.get('theme_id'):
            values['mode'] = 'email_designer'
        else:
            if kw.get('enable_editor'):
                kw.pop('enable_editor')
                fragments = dict(model=model, res_id=res_id, action=action, **kw)
                if template_model:
                    fragments['template_model'] = template_model
                return request.redirect('/website_mail/email_designer?%s' % urlencode(fragments))
            values['mode'] = 'email_template'

        tmpl_obj = request.registry['mail.template']
        if template_model:
            tids = tmpl_obj.search(cr, uid, [('model', '=', template_model)], context=context)
        else:
            tids = tmpl_obj.search(cr, uid, [], context=context)
        templates = tmpl_obj.browse(cr, uid, tids, context=context)
        values['templates'] = templates
        values['html_sanitize'] = html_sanitize

        return request.website.render("website_mail.email_designer", values)

    @http.route(['/website_mail/snippets', '/website_mail/snippets/<theme_xml_id>'], type='json', auth="user", website=True)
    def snippets(self, theme_xml_id='website_mail.email_designer_default_snippets'):
        base_url = request.registry['ir.config_parameter'].get_param(request.cr, request.uid, 'web.base.url')
        return request.website._render(theme_xml_id, {'base_url': base_url})

    @http.route(['/website_mail/set_template_theme'], type='json', auth="user", website=True)
    def set_template_theme(self, res_id=None, model=None, theme_id=None, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        if model and res_id:
            request.registry[model].write(cr, uid, int(res_id), {'theme_xml_id': theme_id})
        return True

    @http.route(['/website_mail/load_qweb_templates'], type='json', auth="user", website=True)
    def load_qweb_template(self, templates):
        cr, uid, context, view_pool, data = request.cr, request.uid, request.context, request.registry['ir.ui.view'], []
        for template in templates:
            data.append(view_pool.read_template(cr, uid, template, context=context))
        return data

    @http.route([
        '/fa_to_img/<icon>',
        '/fa_to_img/<icon>/<color>',
        '/fa_to_img/<icon>/<color>/<int:size>',
        '/fa_to_img/<icon>/<color>/<int:size>/<int:alpha>',
        ], auth="public", website=True)
    def export_icon_to_png(self, icon, color='#000', size=100, alpha=255):
        """ This method converts FontAwesom pictograms to Images and is Used only
            for mass mailing becuase custom fonts are not supported in mail.
            :param icon : character from FontAwesom cheatsheet
            :param color : RGB code of the color
            :param size : Pixels in integer
            :param alpha : transparency of the image from 0 to 255

            :returns PNG image converted from given font
        """
        if color.startswith('rgba'):
            color = color.replace('rgba','rgb')
            color = ','.join(color.split(',')[:-1])+')'
        image = Image.new("RGBA", (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        addons_path = http.addons_manifest['web']['addons_path']
        font = ImageFont.truetype(addons_path + '/web/static/lib/fontawesome/fonts/fontawesome-webfont.ttf', (size * 77) / 100) # Initialize font

        width,height = draw.textsize(icon, font=font)# Determine the dimensions of the icon
        draw.text(((size - width) / 2, (size - height) / 2), icon, font=font, fill=color)
        bbox = image.getbbox() # Get bounding box

        imagemask = Image.new("L", (size, size), 0) # Create an alpha mask
        drawmask = ImageDraw.Draw(imagemask)

        drawmask.text(((size - width) / 2, (size - height) / 2), icon, font=font, fill=alpha) # Draw the icon on the mask

        iconimage = Image.new("RGBA", (size,size), color) # Create a solid color image and apply the mask
        iconimage.putalpha(imagemask)
        if bbox:
            iconimage = iconimage.crop(bbox)
        borderw = int((size - (bbox[2] - bbox[0])) / 2)
        borderh = int((size - (bbox[3] - bbox[1])) / 2)

        outimage = Image.new("RGBA", (size, size), (0, 0, 0, 0)) # Create output image
        outimage.paste(iconimage, (borderw,borderh))
        output = io.BytesIO()
        outimage.save(output, format="PNG")
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/png'
        response.data = output.getvalue()
        return response
