# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import html
import io
import json
import logging
import re
import requests
import tarfile

from odoo import api, fields, models
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError
from odoo.tools import LazyTranslate
from urllib.parse import urljoin, urlparse

_lt = LazyTranslate(__name__)

DEFAULT_WSS_ENDPOINT = 'https://iap-scraper.odoo.com/'
GET_RESULT_TIMEOUT_SECONDS = 3600  # 1 hour
STATUS_MESSAGES = {
    'success': _lt("Success"),
    'processing': _lt("Processing"),
    'waiting': _lt("Waiting for the server to process the request"),
    'done': _lt("Done, website generated"),
    'error_maintenance': _lt("Server is currently under maintenance. Please retry later"),
    'error_internal': _lt("An error occurred"),
    'error_invalid_url': _lt("Invalid url"),
    'error_banned_url': _lt("Banned url"),
    'error_invalid_dbuuid': _lt("Invalid dbuuid"),
    'error_too_many_pages': _lt("The request asks for too many pages"),
    'error_unsupported_version': _lt("Version is unsupported"),
    'error_invalid_token': _lt("Invalid token"),
    'error_concurrent_request': _lt("Number of concurrent requests exceeded"),
    'error_allowed_request_exhausted': _lt("Number of allowed requests exhausted"),
    'error_invalid_import_products': _lt("Invalid import products"),
    'error_invalid_request_uuid': _lt("Could not fetch result, invalid output uuid or result expired"),
    'error_request_still_processing': _lt("Request is still processing, result not available yet"),
    'error_attachment_not_found': _lt("Attachment not found"),
    'errror_website_not_supported': _lt("Website not supported"),
    'error_website_blocked': _lt("Website blocked or unreachable"),
}

logger = logging.getLogger(__name__)


class WebsiteGeneratorRequest(models.Model):
    _name = 'website_generator.request'
    _description = "Website Generator Request"

    target_url = fields.Char(string="URL to scrape", required=True)
    additional_urls = fields.Char(string="Additional URLs")
    page_count = fields.Integer(string="Number of pages")
    uuid = fields.Char(string="Output UUID generated from Website Scraper Server")
    status = fields.Char(string="Status", default='waiting')
    status_message = fields.Char(string="Status Message", compute='_compute_status_message')
    version = fields.Char(string="Version", default='2.0.0')
    website_id = fields.Many2one('website', string="Website", ondelete='cascade')
    notified = fields.Boolean(string="Notified", default=False)

    @api.model_create_multi
    def create(self, vals_list):
        wg_requests = super().create(vals_list)
        for req in wg_requests:
            # If there is already a uuid, it means the request was already
            # created via the odoo.com start trial.
            if not req.uuid:
                ws_endpoint = self.env['ir.config_parameter'].sudo().get_param('website_scraper_endpoint', DEFAULT_WSS_ENDPOINT)
                url = urljoin(ws_endpoint, f'/website_scraper/{req.version}/scrape')
                response = iap_jsonrpc(url, params=req._get_call_params())
                if response.get('status') == 'accepted':
                    req.uuid = response['uuid']
                    req.status = 'waiting'
                else:
                    req.status = response.get('status', 'error_internal')
                    logger.warning("Error calling WS server: %s", req.status)

        self.env.ref("website_generator.cron_get_result").toggle(model=self._name, domain=[])
        return wg_requests

    def write(self, values):
        res = super().write(values)
        pending_requests = self.search([
            ('status', 'in', ['waiting', 'error_request_still_processing', 'error_maintenance']),
        ])
        if not pending_requests:
            self.env.ref("website_generator.cron_get_result").active = False
            logger.info("Webite Generator: No more pending request, disabling 'cron_get_result' cron")
        return res

    @api.depends('status')
    def _compute_status_message(self):
        for record in self:
            record.status_message = self.env._(STATUS_MESSAGES.get(record.status, STATUS_MESSAGES['error_internal']))  # pylint: disable=gettext-variable

    def _get_call_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        params = {
            'url': self.target_url,
            'additional_urls': self.additional_urls,
            'token': ICP.get_param('website_generator.token', None),
            'dbuuid': ICP.get_param('database.uuid'),
        }
        if self.page_count:
            params['page_count'] = self.page_count
        return params

    @api.model
    def get_result_waiting_requests(self):
        """ This method is called by the CRON job which is started by the
        webhook (``/result_ready``). """
        ready_requests = self.search([
            ('status', 'in', ['waiting', 'error_request_still_processing', 'error_maintenance']),
        ])
        for request in ready_requests:
            request._call_server_get_result()

    def _call_server_get_result(self):
        # Don't inline this method in `get_result_waiting_requests()`, it's
        # needed for ease of development (overridden in custom dev module)
        logger.info("Webite Generator: Getting result for request uuid: %s", self.uuid)
        ICP = self.env['ir.config_parameter'].sudo()
        data = {
            'uuid': self.uuid,
            'dbuuid': ICP.get_param('database.uuid'),
            # This is called by a CRON, we are not in a website context,
            # this will always shortcut to ICP, so we can at least have a domain to go back to.
            'db_url': self.get_base_url(),
        }
        ws_endpoint = ICP.get_param('website_scraper_endpoint', DEFAULT_WSS_ENDPOINT)
        url = urljoin(ws_endpoint, f'/website_scraper/{self.version}/get_result')
        response = requests.get(url, params=data, timeout=GET_RESULT_TIMEOUT_SECONDS)

        # /get_result is not protected by token
        data['token'] = ICP.get_param('website_generator.token', None)

        # Check the response
        try:
            if response.status_code != 200:
                self.status = 'error_internal'
                logger.warning("Error calling WS server: Status code %s", response.status_code)
                return
            # TODO: Find a better way to check if the response failed or not
            elif response.headers.get('Content-Type', '') != 'application/x-tar':
                # An error occurred, getting the status from the response
                # On top of real errors, some "normal" status could be returned
                # here as `error_request_still_processing` if the scraping is
                # not yet finished.
                self.status = response.json().get('status', 'error_internal')
                return
        except Exception:
            # If the response is not JSON, it means the request was successful
            pass

        try:
            tar_gz_file = io.BytesIO(response.content)
            with tarfile.open(fileobj=tar_gz_file, mode='r:gz') as tar:
                website, _ = self._generate_site(tar)
            self.status = 'done'
            # Send email to the client.
            website = self.env['website'].get_current_website()
            mail_template = self.env.ref('website_generator.email_template_website_scrapped')
            email_values = {'email_to': self.env.company.email_formatted, 'website_url': website.get_base_url()}
            mail_template.with_context(email_values).send_mail(
                website.id,
                force_send=True,
                email_values=None,
            )

            # Report OK to IAP (success)
            logger.info("Webite Generator: Reporting OK for request uuid: %s", self.uuid)
            url = urljoin(ws_endpoint, f'/website_scraper/{self.version}/report_ok')
            self._report_to_iap(url, data)

        except Exception as e:
            # Defensive programming: if necessary info is missing, stop and warn IAP
            # (should not happen, but just in case of a future changes in the WS server)
            # Rollback the transaction to avoid the creation of the website
            self.env.cr.rollback()
            self.status = 'error_internal'
            logger.exception("Error building the website: %s", e)

            # Report KO to IAP (useful for spotting critical errors)
            logger.info("Webite Generator: Reporting KO for request uuid: %s", self.uuid)
            url = urljoin(ws_endpoint, f'/website_scraper/{self.version}/report_ko')
            self._report_to_iap(url, data)

    def _report_to_iap(self, url, data):
        try:
            resp = iap_jsonrpc(url, params=data)
            if resp.get('status') != 'ok':
                logger.warning("Error reporting to WS server: %s", resp.get('status'))
        except AccessError as e:
            logger.warning("Error reporting to WS server: %s", e)

    def _generate_site(self, tar):
        odoo_blocks = self._load_input(tar)
        odoo_blocks['direct_html_replacements_mapping'] = {}
        odoo_blocks['regex_html_replacements_mapping'] = {}
        website = self._get_website(odoo_blocks, tar)
        # Generate the images attachments (Modifies odoo_blocks in place)
        self._save_images_as_attachments(odoo_blocks, tar)
        self._create_model_records(tar, odoo_blocks)
        # Create redirects, modifies odoo_blocks in place
        self._apply_all_html_replacements(odoo_blocks)
        self._generate_pages(website, odoo_blocks)
        return website, odoo_blocks

    def _apply_all_html_replacements(self, odoo_blocks):
        direct_html_replacements_mapping = odoo_blocks.get('direct_html_replacements_mapping', {})
        regex_html_replacements_mapping = odoo_blocks.get('regex_html_replacements_mapping', {})
        sorted_original_html = sorted(direct_html_replacements_mapping.keys(), key=len, reverse=True)

        homepage = odoo_blocks['homepage']
        homepage['body_html'] = self._apply_html_replacements(homepage.get('body_html', []), sorted_original_html, direct_html_replacements_mapping, regex_html_replacements_mapping)

        footer = homepage.get('footer', [])
        if footer:
            homepage['footer'] = self._apply_html_replacements(footer, sorted_original_html, direct_html_replacements_mapping, regex_html_replacements_mapping)

        header_buttons = homepage.get('header', {}).get('buttons', [])
        for button in header_buttons:
            if button.get('href') in direct_html_replacements_mapping:
                button['href'] = direct_html_replacements_mapping[button['href']]

        # Update the html urls for all pages
        for page_name, page_dict in odoo_blocks.get('pages', {}).items():
            odoo_blocks['pages'][page_name]['body_html'] = self._apply_html_replacements(page_dict.get('body_html', []), sorted_original_html, direct_html_replacements_mapping, regex_html_replacements_mapping)

    def _create_model_records(self, tar, odoo_blocks):
        # Each override will call super and create it's model records as well as any redirects it needs.
        pass

    def _load_input(self, tar):
        # Don't inline this method in `_generate_site()`, it's needed for ease
        # of development (overridden in custom dev module)
        return json.load(tar.extractfile('out.json'))

    def _generate_pages(self, website, odoo_blocks):
        # Create pages
        for page_url, page_data in odoo_blocks.get('pages', {}).items():
            if 'body_html' in page_data:
                # Create page
                new_page_info = website.with_context(website_id=website.id).new_page(page_data['name'])
                new_page = self.env['website.page'].browse(new_page_info['page_id'])
                # force url to the one provided, don't use the slugified one
                new_page.url = page_url
                new_page.is_published = True
                # Create page content
                new_page._construct_page(page_data)

        # Remove the default homepage
        homepage_url = website.homepage_url or '/'
        self.env['website.page'].search([('website_id', '=', website.id), ('url', '=', homepage_url)]).unlink()
        homepage_info = website.with_context(website_id=website.id).new_page('Home')
        homepage = self.env['website.page'].browse(homepage_info['page_id'])
        homepage.write({
            'url': '/',
            'is_published': True,
        })
        # Create home page content
        homepage._construct_homepage(odoo_blocks['homepage'])

    def _get_website(self, odoo_blocks, tar):
        website = self.env['website'].get_current_website()
        self.write({'website_id': website.id})
        website_info = odoo_blocks.get('website')
        if not website_info:
            raise ValueError("Website info not found in the input")
        homepage_url = odoo_blocks.get('homepage', {}).get('url')
        if not homepage_url:
            raise ValueError("Homepage url not found in the input")
        website_name = urlparse(homepage_url).netloc.removeprefix('www.')
        website_values = {'name': website_name, **website_info.get('social_media_links', {})}

        # Add logo
        logo_filename = website_info.get('logo')
        if logo_filename:
            image = self._get_image_data(tar, logo_filename)
            if image:
                website_values['logo'] = base64.b64encode(image).decode()

        website.update(website_values)
        return website

    def _save_images_as_attachments(self, odoo_blocks, tar):
        def populate_image_customization_mapping(customized_image_mappings, ws_id, customization):
            # Replace the image with the cropped one
            url = customization.get('url')
            data_mimetype = customization['data_mimetype']

            # Check that an attachment was created.
            if not customized_attachments_url_src.get(ws_id) or not attachments_url_src.get(url):
                return customized_image_mappings

            attributes = {
                'src': customized_attachments_url_src[ws_id].image_src,
                'data-original-id': attachments_url_src[url].id,
                'data-original-src': attachments_url_src[url].image_src,
                'data-mimetype': data_mimetype,
                'data-mimetype-before-conversion': data_mimetype,
            }

            # Apply the cropping attributes
            cropping_dimensions = customization.get('cropping_coords', {})
            if cropping_dimensions:
                attributes.update({
                    'data-x': cropping_dimensions['x'],
                    'data-y': cropping_dimensions['y'],
                    'data-width': cropping_dimensions['width'],
                    'data-height': cropping_dimensions['height'],
                    'data-scale-x': 1,
                    'data-scale-y': 1,
                    'data-aspect-ratio': '0/0',
                })

            color_filter = customization.get('filter', {})
            if color_filter:
                rgba = f'rgba({int(color_filter["coords"][0] * 255)}, {int(color_filter["coords"][1] * 255)}, {int(color_filter["coords"][2] * 255)}, {color_filter["alpha"]})'
                attributes.update({
                    'data-gl-filter': 'custom',
                    'data-filter-options': f'{{&quot;filterColor&quot;:&quot;{rgba}&quot;}}'
                })

            if url and (cropping_dimensions or color_filter) and ws_id:
                pattern = rf'<img[^>]*data-ws_id\s*=\s*["\']?{ws_id}["\']?[^>]*>'
                # The 'style="" class=""' is needed and will be replaced by the class and style attributes of the original image.
                customized_img_string = f'<img style="" class="" {" ".join([f"{k}={v!r}" for k, v in attributes.items()])}>'
                customized_image_mappings[pattern] = customized_img_string
            return customized_image_mappings

        all_images = odoo_blocks['website'].get('all_images', {})
        # Create attachments for all images (uncropped)
        attachments_url_src = {}
        for img_url, img_name in all_images.items():
            attachments_url_src = self.try_create_image_attachment(img_name, img_url, attachments_url_src, tar)
        odoo_blocks['direct_html_replacements_mapping'].update({html.escape(k): v.image_src for k, v in attachments_url_src.items()})

        # Create attachments for all images (cropped)
        customized_attachments_url_src = {}
        customized_image_mappings = {}
        for page_dict in [odoo_blocks['homepage']] + list(odoo_blocks.get('pages', {}).values()):
            customized_images = page_dict.get('images_to_customize', [])
            for ws_id, image_customizations in customized_images.items():
                img_name = self._get_custom_image_name(all_images, ws_id, image_customizations)
                # Note, we give the 'ws_id' as the image_url because we may have multiple images
                # with the same url but cropped differently (where the image_url is the
                # downloaded image url from the original website).
                customized_attachments_url_src = self.try_create_image_attachment(img_name, ws_id, customized_attachments_url_src, tar)
                customized_image_mappings = populate_image_customization_mapping(customized_image_mappings, ws_id, image_customizations)
        odoo_blocks['regex_html_replacements_mapping'].update(customized_image_mappings)

    def try_create_image_attachment(self, img_name, img_url, attachments_url_src, tar):
        try:
            # Read from tar
            image_data = self._get_image_data(tar, img_name)
            if not image_data:
                return attachments_url_src
            # Create a new attachment
            att = self.env['ir.attachment'].create({
                'name': img_name,
                'raw': image_data,
                'public': True,
                'res_model': 'ir.ui.view',
                'res_id': 0,  # shared between website's pages
            })
            if att and att.image_src:
                attachments_url_src[img_url] = att
        except (AttributeError, TypeError, ValueError) as e:
            # Defensive programming: skip the image if it's invalid
            # (image extension not supported, corrupted metadata, etc.)
            logger.warning("Error attaching image %r : %s", img_url, e)

        return attachments_url_src

    def _get_custom_image_name(self, all_images, ws_id, image_customizations):
        original_img_url = image_customizations.get('url')
        original_img_name = all_images.get(original_img_url, '')
        # We keep the same mimetype as the original image
        supported_mimetypes = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'webp': 'image/webp',
            'svg': 'image/svg+xml',
            'gif': 'image/gif',
        }
        # Split the image name and the image extension based on the last dot
        original_img_name_base, separator, original_img_name_extension = original_img_name.rpartition('.')
        image_extension = original_img_name_extension.lower() if separator else ''
        if not image_extension or image_extension not in supported_mimetypes:
            image_extension = 'png'
        image_customizations['data_mimetype'] = supported_mimetypes[image_extension]
        if original_img_name:
            img_name = f'customized_{original_img_name_base}_{ws_id}.{image_extension}'
            image_customizations['filename'] = img_name
            return img_name
        return ''

    def _apply_html_replacements(self, body_html, sorted_list_replacement_mapping, direct_replacement_mapping, regex_replacement_mapping):
        new_block_list = []
        for block_html in body_html:
            page_html = self._replace_in_string(block_html, sorted_list_replacement_mapping, direct_replacement_mapping)
            page_html = self._replace_in_string_regex(page_html, regex_replacement_mapping)
            new_block_list.append(page_html)
        return new_block_list

    def _find_or_create(self, model, domain, vals):
        record = self.env[model].search(domain, limit=1)
        if not record:
            record = self.env[model].create(vals)
        return record

    def _get_image_data(self, tar, image_name):
        if not image_name:
            return None
        try:
            image_data = tar.extractfile('images/' + image_name).read()
            return image_data
        except (KeyError, AttributeError) as e:
            logger.warning("Image %s not found : %s", image_name, e)
            return None

    def _get_image_info(self, tar, images, image_file_mappings):
        all_images_info = []
        for image in images:
            image_filename = image_file_mappings.get(image, '')
            image_data = self._get_image_data(tar, image_filename)
            if image_data:
                all_images_info.append({
                    'name': image_filename,
                    'raw': image_data,
                    'base64': base64.b64encode(image_data).decode(),
                })
        return all_images_info

    @staticmethod
    def _replace_in_string_regex(page_html, regex_replacement_mapping):
        # Since we need to have a mapping of the regex to the replacement
        # and not a mapping of the matched string to the replacement,
        # we have to do the sub on each iteration, rather than one group sub.
        re_class_patern = re.compile(r'class="[^"]*"')
        re_style_patern = re.compile(r'style="[^"]*"')
        for pattern, replacement in regex_replacement_mapping.items():
            def replace_but_keep_class_and_style(match):
                # Replaces the matched string but keeps the original class and style attribute (if found).
                result = match.group(0)
                class_match = re_class_patern.search(result)
                if class_match:
                    prev_class = class_match.group(0)
                    result = re_class_patern.sub(prev_class, replacement, count=1)

                style_match = re_style_patern.search(match.group(0))
                if style_match:
                    prev_style = style_match.group(0)
                    result = re_style_patern.sub(prev_style, result, count=1)
                return result

            page_html = re.sub(pattern, replace_but_keep_class_and_style, page_html)
        return page_html

    @staticmethod
    def _replace_in_string(string, sorted_list_replacements, replacements):
        if not replacements or not sorted_list_replacements:
            return string

        # Use a regular expression to match any of the replacements
        pattern = r'(' + '|'.join(map(re.escape, sorted_list_replacements)) + r')'

        def replace_callback(match):
            # Having this callback function is useful for verifying which URLs were replaced.
            matched_url = match.group(0)
            replacement = replacements.get(matched_url)
            if not replacement:
                replacement = matched_url
                logger.warning("Match found but URL %r not found in attachments", matched_url)
            return replacement

        # Replace all matches with their corresponding replacement
        replaced_string = re.sub(pattern, replace_callback, string)
        return replaced_string

    @api.model
    def convert_scraping_request_ICP(self):
        ICP = ws_uuid = self.env['ir.config_parameter'].sudo()
        ws_uuid = ICP.get_param('website_generator.iap_ws_uuid', None)
        ws_target_url = ICP.get_param('website_generator.iap_ws_target_url', None)

        if not (ws_uuid and ws_target_url):
            # TODO: return website configurator?
            return {
                'type': 'ir.actions.act_url',
                'url': '/odoo',
                'target': 'self',
            }

        self.env['website_generator.request'].create({
            'uuid': ws_uuid,
            'target_url': ws_target_url,
        })
        ICP.set_param('website_generator.iap_ws_uuid', None)
        ICP.set_param('website_generator.iap_ws_target_url', None)

        return {
            'type': 'ir.actions.act_url',
            'url': "/odoo/action-website_generator.website_generator_screen?reload=true",
            'target': 'self',
        }
