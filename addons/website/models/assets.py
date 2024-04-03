# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
import requests

from werkzeug.urls import url_parse

from odoo import api, models


class Assets(models.AbstractModel):
    _inherit = 'web_editor.assets'

    @api.model
    def make_scss_customization(self, url, values):
        """
        Makes a scss customization of the given file. That file must
        contain a scss map including a line comment containing the word 'hook',
        to indicate the location where to write the new key,value pairs.

        Params:
            url (str):
                the URL of the scss file to customize (supposed to be a variable
                file which will appear in the assets_frontend bundle)

            values (dict):
                key,value mapping to integrate in the file's map (containing the
                word hook). If a key is already in the file's map, its value is
                overridden.
        """
        IrAttachment = self.env['ir.attachment']
        if 'color-palettes-name' in values:
            self.reset_asset('/website/static/src/scss/options/colors/user_color_palette.scss', 'web.assets_frontend')
            self.reset_asset('/website/static/src/scss/options/colors/user_gray_color_palette.scss', 'web.assets_frontend')
            # Do not reset all theme colors for compatibility (not removing alpha -> epsilon colors)
            self.make_scss_customization('/website/static/src/scss/options/colors/user_theme_color_palette.scss', {
                'success': 'null',
                'info': 'null',
                'warning': 'null',
                'danger': 'null',
            })
            # Also reset gradients which are in the "website" values palette
            self.make_scss_customization('/website/static/src/scss/options/user_values.scss', {
                'menu-gradient': 'null',
                'header-boxed-gradient': 'null',
                'footer-gradient': 'null',
                'copyright-gradient': 'null',
            })

        delete_attachment_id = values.pop('delete-font-attachment-id', None)
        if delete_attachment_id:
            delete_attachment_id = int(delete_attachment_id)
            IrAttachment.search([
                '|', ('id', '=', delete_attachment_id),
                ('original_id', '=', delete_attachment_id),
                ('name', 'like', '%google-font%')
            ]).unlink()

        google_local_fonts = values.get('google-local-fonts')
        if google_local_fonts and google_local_fonts != 'null':
            # "('font_x': 45, 'font_y': '')" -> {'font_x': '45', 'font_y': ''}
            google_local_fonts = dict(re.findall(r"'([^']+)': '?(\d*)", google_local_fonts))
            # Google is serving different font format (woff, woff2, ttf, eot..)
            # based on the user agent. We need to get the woff2 as this is
            # supported by all the browers we support.
            headers_woff2 = {
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
            }
            for font_name in google_local_fonts:
                if google_local_fonts[font_name]:
                    google_local_fonts[font_name] = int(google_local_fonts[font_name])
                else:
                    font_family_attachments = IrAttachment
                    font_content = requests.get(
                        f'https://fonts.googleapis.com/css?family={font_name}:300,300i,400,400i,700,700i&display=swap',
                        timeout=5, headers=headers_woff2,
                    ).content.decode()

                    def fetch_google_font(src):
                        statement = src.group()
                        url, font_format = re.match(r'src: url\(([^\)]+)\) (.+)', statement).groups()
                        req = requests.get(url, timeout=5, headers=headers_woff2)
                        # https://fonts.gstatic.com/s/modak/v18/EJRYQgs1XtIEskMB-hRp7w.woff2
                        # -> s-modak-v18-EJRYQgs1XtIEskMB-hRp7w.woff2
                        name = url_parse(url).path.lstrip('/').replace('/', '-')
                        attachment = IrAttachment.create({
                            'name': f'google-font-{name}',
                            'type': 'binary',
                            'datas': base64.b64encode(req.content),
                            'public': True,
                        })
                        nonlocal font_family_attachments
                        font_family_attachments += attachment
                        return 'src: url(/web/content/%s/%s) %s' % (
                            attachment.id,
                            name,
                            font_format,
                        )

                    font_content = re.sub(r'src: url\(.+\)', fetch_google_font, font_content)

                    attach_font = IrAttachment.create({
                        'name': f'{font_name} (google-font)',
                        'type': 'binary',
                        'datas': base64.encodebytes(font_content.encode()),
                        'mimetype': 'text/css',
                        'public': True,
                    })
                    google_local_fonts[font_name] = attach_font.id
                    # That field is meant to keep track of the original
                    # image attachment when an image is being modified (by the
                    # website builder for instance). It makes sense to use it
                    # here to link font family attachment to the main font
                    # attachment. It will ease the unlink later.
                    font_family_attachments.original_id = attach_font.id

            # {'font_x': 45, 'font_y': 55} -> "('font_x': 45, 'font_y': 55)"
            values['google-local-fonts'] = str(google_local_fonts).replace('{', '(').replace('}', ')')

        custom_url = self._make_custom_asset_url(url, 'web.assets_frontend')
        updatedFileContent = self._get_content_from_url(custom_url) or self._get_content_from_url(url)
        updatedFileContent = updatedFileContent.decode('utf-8')
        for name, value in values.items():
            # Protect variable names so they cannot be computed as numbers
            # on SCSS compilation (e.g. var(--700) => var(700)).
            if isinstance(value, str):
                value = re.sub(
                    r"var\(--([0-9]+)\)",
                    lambda matchobj: "var(--#{" + matchobj.group(1) + "})",
                    value)
            pattern = "'%s': %%s,\n" % name
            regex = re.compile(pattern % ".+")
            replacement = pattern % value
            if regex.search(updatedFileContent):
                updatedFileContent = re.sub(regex, replacement, updatedFileContent)
            else:
                updatedFileContent = re.sub(r'( *)(.*hook.*)', r'\1%s\1\2' % replacement, updatedFileContent)

        self.save_asset(url, 'web.assets_frontend', updatedFileContent, 'scss')

    @api.model
    def _get_custom_attachment(self, custom_url, op='='):
        """
        See web_editor.Assets._get_custom_attachment
        Extend to only return the attachments related to the current website.
        """
        if self.env.user.has_group('website.group_website_designer'):
            self = self.sudo()
        website = self.env['website'].get_current_website()
        res = super()._get_custom_attachment(custom_url, op=op)
        # FIXME (?) In website, those attachments should always have been
        # created with a website_id. The "not website_id" part in the following
        # condition might therefore be useless (especially since the attachments
        # do not seem ordered). It was developed in the spirit of served
        # attachments which follow this rule of "serve what belongs to the
        # current website or all the websites" but it probably does not make
        # sense here. It however allowed to discover a bug where attachments
        # were left without website_id. This will be kept untouched in stable
        # but will be reviewed and made more robust in master.
        return res.with_context(website_id=website.id).filtered(lambda x: not x.website_id or x.website_id == website)

    @api.model
    def _get_custom_asset(self, custom_url):
        """
        See web_editor.Assets._get_custom_asset
        Extend to only return the views related to the current website.
        """
        if self.env.user.has_group('website.group_website_designer'):
            # TODO: Remove me in master, see commit message, ACL added right to
            #       unlink to designer but not working without -u in stable
            self = self.sudo()
        website = self.env['website'].get_current_website()
        res = super()._get_custom_asset(custom_url)
        return res.with_context(website_id=website.id).filter_duplicate()

    @api.model
    def _save_asset_hook(self):
        """
        See web_editor.Assets._save_asset_hook
        Extend to add website ID at attachment creation.
        """
        res = super()._save_asset_hook()

        website = self.env['website'].get_current_website()
        if website:
            res['website_id'] = website.id
        return res
