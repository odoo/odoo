# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import json
import logging
import os
import re
import time
import werkzeug.wrappers
from PIL import Image, ImageFont, ImageDraw
from lxml import etree, html

from odoo.http import request
from odoo import http, tools
from odoo.tools import pycompat
from odoo.modules.module import get_resource_path, get_module_path

logger = logging.getLogger(__name__)

class Web_Editor(http.Controller):
    #------------------------------------------------------
    # Backend snippet
    #------------------------------------------------------
    @http.route('/web_editor/snippets', type='json', auth="user")
    def snippets(self, **kwargs):
        return request.env.ref('web_editor.snippets').render(None)

    #------------------------------------------------------
    # Backend html field
    #------------------------------------------------------
    @http.route('/web_editor/field/html', type='http', auth="user")
    def FieldTextHtml(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs.update(
            model=model,
            res_id=res_id,
            field=field,
            datarecord=json.loads(kwargs['datarecord']),
            debug=request.debug)

        for k in kwargs:
            if isinstance(kwargs[k], pycompat.string_types) and kwargs[k].isdigit():
                kwargs[k] = int(kwargs[k])

        trans = dict(
            lang=kwargs.get('lang', request.env.context.get('lang')),
            translatable=kwargs.get('translatable'),
            edit_translations=kwargs.get('edit_translations'),
            editable=kwargs.get('enable_editor'))

        kwargs.update(trans)

        record = None
        if model and kwargs.get('res_id'):
            record = request.env[model].with_context(trans).browse(kwargs.get('res_id'))

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
        """ This method converts an unicode character to an image (using Font
            Awesome font by default) and is used only for mass mailing because
            custom fonts are not supported in mail.
            :param icon : decimal encoding of unicode character
            :param color : RGB code of the color
            :param size : Pixels in integer
            :param alpha : transparency of the image from 0 to 255
            :param font : font path

            :returns PNG image converted from given font
        """
        # Make sure we have at least size=1
        size = max(1, size)
        # Initialize font
        addons_path = http.addons_manifest['web']['addons_path']
        font_obj = ImageFont.truetype(addons_path + font, size)

        # if received character is not a number, keep old behaviour (icon is character)
        icon = pycompat.unichr(int(icon)) if icon.isdigit() else icon

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
        Attachments = request.env['ir.attachment']  # registry for the attachment table

        res_model = kwargs.get('res_model', 'ir.ui.view')
        if res_model != 'ir.ui.view' and kwargs.get('res_id'):
            res_id = int(kwargs['res_id'])
        else:
            res_id = None

        uploads = []
        message = None
        if not upload: # no image provided, storing the link and the image name
            name = url.split("/").pop()                       # recover filename
            attachment = Attachments.create({
                'name': name,
                'type': 'url',
                'url': url,
                'public': res_model == 'ir.ui.view',
                'res_id': res_id,
                'res_model': res_model,
            })
            attachment.generate_access_token()
            uploads += attachment.read(['name', 'mimetype', 'checksum', 'url', 'res_id', 'res_model', 'access_token'])
        else:                                                  # images provided
            try:
                attachments = request.env['ir.attachment']
                for c_file in request.httprequest.files.getlist('upload'):
                    data = c_file.read()
                    try:
                        image = Image.open(io.BytesIO(data))
                        w, h = image.size
                        if w*h > 42e6: # Nokia Lumia 1020 photo resolution
                            raise ValueError(
                                u"Image size excessive, uploaded images must be smaller "
                                u"than 42 million pixel")
                        if not disable_optimization and image.format in ('PNG', 'JPEG'):
                            data = tools.image_save_for_web(image)
                    except IOError as e:
                        pass

                    attachment = Attachments.create({
                        'name': c_file.filename,
                        'datas': base64.b64encode(data),
                        'datas_fname': c_file.filename,
                        'public': res_model == 'ir.ui.view',
                        'res_id': res_id,
                        'res_model': res_model,
                    })
                    attachment.generate_access_token()
                    attachments += attachment
                uploads += attachments.read(['name', 'mimetype', 'checksum', 'url', 'res_id', 'res_model', 'access_token'])
            except Exception as e:
                logger.exception("Failed to upload image to attachment")
                message = pycompat.text_type(e)

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
        Attachment = attachments_to_remove = request.env['ir.attachment']
        Views = request.env['ir.ui.view']

        # views blocking removal of the attachment
        removal_blocked_by = {}

        for attachment in Attachment.browse(ids):
            # in-document URLs are html-escaped, a straight search will not
            # find them
            url = tools.html_escape(attachment.local_url)
            views = Views.search([
                "|",
                ('arch_db', 'like', '"%s"' % url),
                ('arch_db', 'like', "'%s'" % url)
            ])

            if views:
                removal_blocked_by[attachment.id] = views.read(['name'])
            else:
                attachments_to_remove += attachment
        if attachments_to_remove:
            attachments_to_remove.unlink()
        return removal_blocked_by

    ## The get_assets_editor_resources route is in charge of transmitting the resources the assets
    ## editor needs to work.
    ## @param key - the xml_id or id of the view the resources are related to
    ## @param get_views - True if the views must be fetched (default to True)
    ## @param get_less - True if the style must be fetched (default to True)
    ## @param bundles - True if the bundles views must be fetched (default to False)
    ## @param bundles_restriction - Names of the bundle in which to look for less files (if empty, search in all of them)
    ## @returns a dictionary with views info in the views key and style info in the less key
    @http.route("/web_editor/get_assets_editor_resources", type="json", auth="user", website=True)
    def get_assets_editor_resources(self, key, get_views=True, get_less=True, bundles=False, bundles_restriction=[]):
        # Related views must be fetched if the user wants the views and/or the style
        views = request.env["ir.ui.view"].get_related_views(key, bundles=bundles)
        views = views.read(['name', 'id', 'key', 'xml_id', 'arch', 'active', 'inherit_id'])

        less_files_data_by_bundle = []

        # Load less only if asked by the user
        if get_less:
            # Compile regex outside of the loop
            # This will used to exclude library less files from the result
            excluded_url_matcher = re.compile("^(.+/lib/.+)|(.+import_bootstrap.less)$")

            # Load already customized less files attachments
            custom_attachments = request.env["ir.attachment"].search([("url", "=like", self._make_custom_less_file_url("%%.%%", "%%"))])

            # First check the t-call-assets used in the related views
            url_infos = dict()
            for v in views:
                for asset_call_node in etree.fromstring(v["arch"]).xpath("//t[@t-call-assets]"):
                    if asset_call_node.get("t-css") == "false":
                        continue
                    asset_name = asset_call_node.get("t-call-assets")

                    # Loop through bundle files to search for LESS file info
                    less_files_data = []
                    for file_info in request.env["ir.qweb"]._get_asset_content(asset_name, {})[0]:
                        if file_info["atype"] != "text/less":
                            continue
                        url = file_info["url"]

                        # Exclude library files (see regex above)
                        if excluded_url_matcher.match(url):
                            continue

                        # Check if the file is customized and get bundle/path info
                        less_file_data = self._match_less_file_url(url)
                        if not less_file_data:
                            continue

                        # Save info (arch will be fetched later)
                        url_infos[url] = less_file_data
                        less_files_data.append(url)

                    # Less data is returned sorted by bundle, with the bundles names and xmlids
                    if len(less_files_data):
                        less_files_data_by_bundle.append([dict(xmlid=asset_name, name=request.env.ref(asset_name).name), less_files_data])

            # Filter bundles/files:
            # - A file which appears in multiple bundles only appears in the first one (the first in the DOM)
            # - Only keep bundles with files which appears in the asked bundles and only keep those files
            for i in range(0, len(less_files_data_by_bundle)):
                bundle_1 = less_files_data_by_bundle[i]
                for j in range(0, len(less_files_data_by_bundle)):
                    bundle_2 = less_files_data_by_bundle[j]
                    # In unwanted bundles, keep only the files which are in wanted bundles too (less_helpers)
                    if bundle_1[0]["xmlid"] not in bundles_restriction and bundle_2[0]["xmlid"] in bundles_restriction:
                        bundle_1[1] = [item_1 for item_1 in bundle_1[1] if item_1 in bundle_2[1]]
            for i in range(0, len(less_files_data_by_bundle)):
                bundle_1 = less_files_data_by_bundle[i]
                for j in range(i+1, len(less_files_data_by_bundle)):
                    bundle_2 = less_files_data_by_bundle[j]
                    # In every bundle, keep only the files which were not found in previous bundles
                    bundle_2[1] = [item_2 for item_2 in bundle_2[1] if item_2 not in bundle_1[1]]

            # Only keep bundles which still have files and that were requested
            less_files_data_by_bundle = [
                data for data in less_files_data_by_bundle
                if (len(data[1]) > 0 and (not bundles_restriction or data[0]["xmlid"] in bundles_restriction))
            ]

            # Fetch the arch of each kept file, in each bundle
            for bundle_data in less_files_data_by_bundle:
                for i in range(0, len(bundle_data[1])):
                    url = bundle_data[1][i]
                    url_info = url_infos[url]

                    content = None
                    if url_info["customized"]:
                        # If the file is already customized, the content is found in the corresponding attachment
                        content = base64.b64decode(custom_attachments.filtered(lambda a: a.url == url).datas)
                    else:
                        # If the file is not yet customized, the content is found by reading the local less file
                        module = url_info["module"]
                        module_path = get_module_path(module)
                        module_resource_path = get_resource_path(module, url_info["resource_path"])
                        if module_path and module_resource_path:
                            module_path = os.path.join(os.path.normpath(module_path), '') # join ensures the path ends with '/'
                            module_resource_path = os.path.normpath(module_resource_path)
                            if module_resource_path.startswith(module_path):
                                with open(module_resource_path, "rb") as f:
                                    content = f.read()

                    bundle_data[1][i] = dict(
                        url = "/%s/%s" % (url_info["module"], url_info["resource_path"]),
                        arch = content,
                        customized = url_info["customized"],
                    )

        return dict(
            views = get_views and views or [],
            less = get_less and less_files_data_by_bundle or [],
        )

    ## The save_less route is in charge of saving a given modification of a LESS file.
    ## @param url - the original url of the LESS file which has to be modified
    ## @param bundle_xmlid - the xmlid of the bundle in which the LESS file addition can be found
    ## @param content - the new content of the LESS file
    @http.route("/web_editor/save_less", type="json", auth="user")
    def save_less(self, url, bundle_xmlid, content):
        IrAttachment = request.env["ir.attachment"]

        custom_url = self._make_custom_less_file_url(url, bundle_xmlid)

        # Check if the file to save had already been modified
        custom_attachment = IrAttachment.search([("url", "=", custom_url)])
        datas = base64.b64encode((content or "\n").encode("utf-8"))
        if custom_attachment:
            # If it was already modified, simply override the corresponding attachment content
            custom_attachment.write({"datas": datas})
        else:
            # If not, create a new attachment to copy the original LESS file content, with its modifications
            IrAttachment.create(dict(
                name = custom_url,
                type = "binary",
                mimetype = "text/less",
                datas = datas,
                datas_fname = url.split("/")[-1],
                url = custom_url, # Having an attachment of "binary" type with an non empty "url" field
                                  # is quite of an hack. This allows to fetch the "datas" field by adding
                                  # a <link/> with the "url" content in the bundle template (see qweb)
            ))

            # Create a view to extend the template which adds the original file to link the new modified version instead
            IrUiView = request.env["ir.ui.view"]
            view_to_xpath = IrUiView.get_related_views(bundle_xmlid, bundles=True).filtered(lambda v: v.arch.find(url) >= 0)
            IrUiView.create(dict(
                name = custom_url,
                mode = "extension",
                inherit_id = view_to_xpath.id,
                arch = """
                    <data inherit_id="%(inherit_xml_id)s" name="%(name)s">
                        <xpath expr="//link[@href='%(url_to_replace)s']" position="attributes">
                            <attribute name="href">%(new_url)s</attribute>
                        </xpath>
                    </data>
                """ % dict(
                    inherit_xml_id = view_to_xpath.xml_id,
                    name = custom_url,
                    url_to_replace = url,
                    new_url = custom_url,
                )
            ))

        request.env["ir.qweb"].clear_caches()

    ## The reset_less route is in charge of reverting all the changes that were done to a less file.
    ## @param url - the original URL of the LESS file to reset
    ## @param bundle_xmlid - the xmlid of the bundle in which the LESS file addition can be found
    @http.route("/web_editor/reset_less", type="json", auth="user")
    def reset_less(self, url, bundle_xmlid):
        IrAttachment = request.env["ir.attachment"]
        IrUiView = request.env["ir.ui.view"]

        custom_url = self._make_custom_less_file_url(url, bundle_xmlid)

        # Simply delete the attachement which contains the modified less file and the xpath view which links it
        IrAttachment.search([("url", "=", custom_url)]).unlink()
        IrUiView.search([("name", "=", custom_url)]).unlink()

    def _make_custom_less_file_url(self, url, bundle):
        parts = url.rsplit(".", 1)
        return "%s.custom.%s.%s" % (parts[0], bundle, parts[1])

    _match_less_file_url_regex = re.compile("^/(\w+)/(.+?)(\.custom\.(.+))?\.(\w+)$")
    def _match_less_file_url(self, url):
        m = self._match_less_file_url_regex.match(url)
        if not m:
            return False
        return dict(
            module = m.group(1),
            resource_path = "%s.%s" % (m.group(2), m.group(5)),
            customized = bool(m.group(3)),
            bundle = m.group(4) or False
        )
