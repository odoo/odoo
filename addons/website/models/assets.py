# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import requests

from werkzeug.urls import url_parse

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes, file_open
from odoo.addons.base.models.assetsbundle import EXTENSIONS, AssetsBundle

_match_asset_file_url_regex = re.compile(r"^(/_custom/([^/]+))?/(\w+)/([/\w]+\.\w+)$")


class WebsiteAssets(models.AbstractModel):
    _name = 'website.assets'
    _description = 'Assets Utils'

    @api.model
    def reset_asset(self, url, bundle):
        """
        Delete the potential customizations made to a given (original) asset.

        Params:
            url (str): the URL of the original asset (scss / js) file

            bundle (str):
                the name of the bundle in which the customizations to delete
                were made
        """
        custom_url = self._make_custom_asset_url(url, bundle)

        # Simply delete the attachement which contains the modified scss/js file
        # and the xpath view which links it
        self._get_custom_attachment(custom_url).unlink()
        self._get_custom_asset(custom_url).unlink()

    @api.model
    def save_asset(self, url, bundle, content, file_type):
        """
        Customize the content of a given asset (scss / js).

        Params:
            url (src):
                the URL of the original asset to customize (whether or not the
                asset was already customized)

            bundle (src):
                the name of the bundle in which the customizations will take
                effect

            content (src): the new content of the asset (scss / js)

            file_type (src):
                either 'scss' or 'js' according to the file being customized
        """
        custom_url = self._make_custom_asset_url(url, bundle)
        raw = (content or "\n").encode("utf-8")

        # Check if the file to save had already been modified
        custom_attachment = self._get_custom_attachment(custom_url)
        if custom_attachment:
            # If it was already modified, simply override the corresponding
            # attachment content
            custom_attachment.write({"raw": raw})
            self.env.transaction.invalidate_ormcache('assets')
        else:
            # If not, create a new attachment to copy the original scss/js file
            # content, with its modifications
            new_attach = {
                'name': url.split("/")[-1],
                'type': "binary",
                'mimetype': (file_type == 'js' and 'text/javascript' or 'text/scss'),
                'raw': raw,
                'url': custom_url,
                **self._add_website_id({}),
            }
            self.env["ir.attachment"].create(new_attach)

            # Create an asset with the new attachment
            IrAsset = self.env['ir.asset']
            new_asset = {
                'path': custom_url,
                'target': url,
                'directive': 'replace',
                **self._add_website_id({}),
            }
            target_asset = self._get_custom_asset(url)
            if target_asset:
                new_asset['name'] = target_asset.name + ' override'
                new_asset['bundle'] = target_asset.bundle
                new_asset['sequence'] = target_asset.sequence
            else:
                new_asset['name'] = '%s: replace %s' % (bundle, custom_url.split('/')[-1])
                new_asset['bundle'] = IrAsset._get_related_bundle(url, bundle)
            IrAsset.create(new_asset)

    @api.model
    def _get_content_from_url(self, url, url_info=None, custom_attachments=None):
        """
        Fetch the content of an asset (scss / js) file. That content is either
        the one of the related file on the disk or the one of the corresponding
        custom ir.attachment record.

        Params:
            url (str): the URL of the asset (scss / js) file/ir.attachment

            url_info (dict, optional):
                the related url info (see _get_data_from_url) (allows to optimize
                some code which already have the info and do not want this
                function to re-get it)

            custom_attachments (ir.attachment(), optional):
                the related custom ir.attachment records the function might need
                to search into (allows to optimize some code which already have
                that info and do not want this function to re-get it)

        Returns:
            utf-8 encoded content of the asset (scss / js)
        """
        if url_info is None:
            url_info = self._get_data_from_url(url)

        if url_info["customized"]:
            # If the file is already customized, the content is found in the
            # corresponding attachment
            attachment = None
            if custom_attachments is None:
                attachment = self._get_custom_attachment(url)
            else:
                attachment = custom_attachments.filtered(lambda r: r.url == url)
            return attachment.raw

        # If the file is not yet customized, the content is found by reading
        # the local file
        with file_open(url.strip('/'), 'rb', filter_ext=EXTENSIONS) as f:
            return BinaryBytes(f.read(), filename=f.name or '')

    @api.model
    def _get_data_from_url(self, url):
        """
        Return information about an asset (scss / js) file/ir.attachment just by
        looking at its URL.

        Params:
            url (str): the url of the asset (scss / js) file/ir.attachment

        Returns:
            dict:
                module (str): the original asset's related app

                resource_path (str):
                    the relative path to the original asset from the related app

                customized (bool): whether the asset is a customized one or not

                bundle (str):
                    the name of the bundle the asset customizes (False if this
                    is not a customized asset)
        """
        m = _match_asset_file_url_regex.match(url)
        if not m:
            return False
        return {
            'module': m.group(3),
            'resource_path': m.group(4),
            'customized': bool(m.group(1)),
            'bundle': m.group(2) or False
        }

    @api.model
    def _make_custom_asset_url(self, url, bundle_xmlid):
        """
        Return the customized version of an asset URL, that is the URL the asset
        would have if it was customized.

        Params:
            url (str): the original asset's url
            bundle_xmlid (str): the name of the bundle the asset would customize

        Returns:
            str: the URL the given asset would have if it was customized in the
                 given bundle
        """
        return f"/_custom/{bundle_xmlid}{url}"

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
        if not self.env.website and (host_id := self.env.context.get('host_id')):
            self = self.with_context(website_id=host_id)  # noqa: PLW0642

        IrAttachment = self.env['ir.attachment']
        if 'color-palettes-name' in values:
            for reset_url, reset_values in self._get_color_palette_resets().items():
                if reset_values is None:
                    self.reset_asset(reset_url, 'web.assets_frontend')
                else:
                    self.make_scss_customization(reset_url, reset_values)

        delete_attachment_id = values.pop('delete-font-attachment-id', None)
        if delete_attachment_id:
            delete_attachment_id = int(delete_attachment_id)
            IrAttachment.search([
                '|', ('id', '=', delete_attachment_id),
                ('original_id', '=', delete_attachment_id),
                ('name', 'like', 'google-font'),
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
                        f'https://fonts.googleapis.com/css?family={font_name}:100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i&display=swap',
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
                            'raw': BinaryBytes(req.content),
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
                        'raw': BinaryBytes(font_content.encode()),
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

        updatedFileContent = self._customize_scss_content(self._get_scss_content(url), values)
        self.save_asset(url, 'web.assets_frontend', updatedFileContent, 'scss')

    @api.model
    def _get_color_palette_resets(self):
        """
        Return the customizations a color palette switch resets: by URL, the
        values to write in the file, or None to reset the file to its original
        content.
        """
        preset_gradients = {f'o-cc{cc}-bg-gradient': 'null' for cc in range(1, 6)}
        return {
            '/website/static/src/scss/options/colors/user_color_palette.scss': None,
            '/website/static/src/scss/options/colors/user_gray_color_palette.scss': None,
            # Do not reset all theme colors for compatibility (not removing alpha -> epsilon colors)
            '/website/static/src/scss/options/colors/user_theme_color_palette.scss': {
                'success': 'null',
                'info': 'null',
                'warning': 'null',
                'danger': 'null',
            },
            # Also reset gradients which are in the "website" values palette
            '/website/static/src/scss/options/user_values.scss': {
                'menu-gradient': 'null',
                'menu-secondary-gradient': 'null',
                'footer-gradient': 'null',
                'copyright-gradient': 'null',
                'breadcrumb-gradient': 'null',
                **preset_gradients,
            },
        }

    @api.model
    def _get_scss_content(self, url):
        """ Return the current content of a (possibly customized) SCSS file. """
        custom_url = self._make_custom_asset_url(url, 'web.assets_frontend')
        content = self._get_content_from_url(custom_url) or self._get_content_from_url(url)
        return content.decode('utf-8')

    @api.model
    def _customize_scss_content(self, content, values):
        """
        Return the content of a SCSS file with the given key,value pairs
        written in its map (see `make_scss_customization`), without saving it.
        """
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
            if regex.search(content):
                content = re.sub(regex, replacement, content)
            else:
                content = re.sub(r'^( *)(.*hook.*)', r'\1%s\1\2' % replacement, content, count=1, flags=re.MULTILINE)
        return content

    @api.model
    def _get_theme_preview_css(self, values_by_url):
        """
        Compile the website's frontend CSS as if the given customizations had
        been saved with `make_scss_customization`, without writing anything:
        the customized files' content is replaced in memory, for this compile
        only.

        Params:
            values_by_url (dict):
                by SCSS file URL, in the order they would be saved, the
                key,value mapping to write in its map

        Returns:
            str: the CSS of the website's web.assets_frontend bundle
        """
        contents = {}
        for url, values in values_by_url.items():
            if 'color-palettes-name' in values:
                for reset_url, reset_values in self._get_color_palette_resets().items():
                    if reset_values is None:
                        contents[reset_url] = self._get_content_from_url(reset_url).decode('utf-8')
                    else:
                        contents[reset_url] = self._customize_scss_content(
                            contents.get(reset_url) or self._get_scss_content(reset_url), reset_values)
            contents[url] = self._customize_scss_content(contents.get(url) or self._get_scss_content(url), values)

        IrQweb = self.env['ir.qweb']
        assets_params = self.env['ir.asset']._get_asset_params()
        files, external_assets = IrQweb._get_asset_content('web.assets_frontend', assets_params)
        original_urls = {self._make_custom_asset_url(url, 'web.assets_frontend'): url for url in contents}
        for file in files:
            url = original_urls.get(file['url'], file['url'])
            if url in contents:
                # A file's content makes it an inline asset: it isn't read.
                file['content'] = contents[url]
        # As `ir.qweb._get_asset_links` decides it for the page.
        rtl = self.env['res.lang'].sudo()._lang_get(code=(self.env.lang or self.env.user.lang)).direction == 'rtl'
        bundle = AssetsBundle('web.assets_frontend', files, external_assets, env=self.env,
                              js=False, rtl=rtl, assets_params=assets_params)
        css = bundle.preprocess_css()
        if bundle.css_errors:
            raise UserError('\n'.join(bundle.css_errors))
        # Move the @import rules up to the top, as `AssetsBundle.css` does.
        imports = []
        css = bundle.rx_css_import.sub(lambda matchobj: imports.append(matchobj.group(0)) and '', css)
        return '\n'.join([*imports, css])

    @api.model
    def _get_custom_attachment(self, custom_url, op='='):
        """
        Fetch the ir.attachment record related to the given customized asset.

        Params:
            custom_url (str): the URL of the customized asset
            op (str, default: '='): the operator to use to search the records

        Returns:
            ir.attachment()
        Only return the attachments related to the current website.
        """
        assert op in ('in', '='), 'Invalid operator'
        if self.env.user.has_group('website.group_website_designer'):
            self = self.sudo()
        res = self.env['ir.attachment'].search([('url', op, custom_url), ('website_id', '=', self.env.website.id)])
        # It is guaranteed that the attachment we are looking for has a website_id.
        # When we serve an attachment we normally serve the ones which have the right website_id
        # or no website_id at all (which means "available to all websites", of
        # course if they are marked "public"). But this does not apply in this
        # case of customized asset files.
        return res

    @api.model
    def _get_custom_asset(self, custom_url):
        """
        Fetch the ir.asset record related to the given customized asset (the
        inheriting view which replace the original asset by the customized one).

        Params:
            custom_url (str): the URL of the customized asset

        Returns:
            ir.asset()
        Return the views related to the current website.
        """
        url = custom_url[1:] if custom_url.startswith(('/', '\\')) else custom_url
        res = self.env['ir.asset'].search([('path', 'like', url)])
        return res.filter_duplicate()

    @api.model
    def _add_website_id(self, values):
        values['website_id'] = self.env.website.id
        return values
