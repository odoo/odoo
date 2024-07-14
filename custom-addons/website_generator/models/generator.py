# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import html
import io
import json
import logging
import re
import requests
import tarfile

from odoo import api, fields, models, _lt
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError
from urllib.parse import urljoin, urlparse

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
    version = fields.Char(string="Version", default='1.0.0')
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
            record.status_message = STATUS_MESSAGES.get(record.status, STATUS_MESSAGES['error_internal'])

    def _get_call_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'url': self.target_url,
            'additional_urls': self.additional_urls,
            'page_count': self.page_count,
            'token': ICP.get_param('website_generator.token', None),
            'dbuuid': ICP.get_param('database.uuid'),
        }

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
            self.website_id = website.id
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
        website = self._get_website(odoo_blocks, tar)
        # Generate the images attachments (Modifies odoo_blocks in place)
        self._save_images_as_attachments(odoo_blocks, tar)
        self._generate_pages(website, odoo_blocks)
        return website, odoo_blocks

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
        website_info = odoo_blocks.get('website')
        if not website_info:
            raise ValueError("Website info not found in the input")
        homepage_url = odoo_blocks.get('homepage', {}).get('url')
        if not homepage_url:
            raise ValueError("Homepage url not found in the input")
        website_name = urlparse(homepage_url).netloc.split(".")[-2]
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
        all_images = odoo_blocks['website'].get('all_images', {})
        # Create attachments for all images (uncropped)
        attachments_url_src = {}
        for img_url, img_name in all_images.items():
            attachments_url_src = self.try_create_image_attachment(img_name, img_url, attachments_url_src, tar)

        # Create attachments for all images (cropped)
        cropped_attachments_url_src = {}
        # Home page
        for image in odoo_blocks['homepage'].get('images_to_crop', []):
            img_name = self._get_cropped_image_name(all_images, image)
            cropped_attachments_url_src = self.try_create_image_attachment(img_name, image['url'], cropped_attachments_url_src, tar)

        # Other pages
        for page_dict in odoo_blocks.get('pages', {}).values():
            for image in page_dict.get('images_to_crop', []):
                img_name = self._get_cropped_image_name(all_images, image)
                cropped_attachments_url_src = self.try_create_image_attachment(img_name, image['url'], cropped_attachments_url_src, tar)

        # Update the html urls
        if attachments_url_src:
            # Modifies odoo_blocks in place
            self._update_html_urls(odoo_blocks, attachments_url_src, cropped_attachments_url_src)

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
        except (TypeError, ValueError) as e:
            # Defensive programming: skip the image if it's invalid
            # (image extension not supported, corrupted metadata, etc.)
            logger.warning("Error attaching image %r : %s", img_url, e)

        return attachments_url_src

    def _get_cropped_image_name(self, all_images, image):
        cropped_image_id = image.get('ws_id')
        uncropped_img_name = all_images.get(image.get('url'), "")
        if uncropped_img_name:
            img_name = 'cropped_' + uncropped_img_name.split('.')[0] + '_' + cropped_image_id + '.png'
            return img_name
        return ""

    def _update_html_urls(self, odoo_blocks, attachments_url_src, cropped_attachments_url_src):
        def update_page_html(page_dict):
            images_on_page = page_dict.get('images', [])
            cropped_images = page_dict.get('images_to_crop', [])
            page_attachments_url_src = {html.escape(k): v.image_src for k, v in attachments_url_src.items() if k in images_on_page}
            sorted_list_attachments_url_src = sorted(page_attachments_url_src, key=len, reverse=True)

            new_block_list = []
            for block_html in page_dict.get('body_html', []):
                page_html = self._replace_in_string(block_html, sorted_list_attachments_url_src, page_attachments_url_src)
                # Then replace all cropped src with the new cropped image html
                for img in cropped_images:
                    if 'cropping_coords' in img and img['url'] in cropped_attachments_url_src:
                        page_html = apply_image_cropping(page_html, img)
                new_block_list.append(page_html)
            return new_block_list

        def apply_image_cropping(new_block_html, img):
            # Replace the image with the cropped one
            url = img.get('url')
            cropping_dimensions = img.get('cropping_coords')
            ws_id = img.get('ws_id')
            if url and cropping_dimensions and ws_id:
                pattern = r'<img[^>]*data-ws_id\s*=\s*["\']?{}["\']?[^>]*>'.format(ws_id)
                cropped_img_string = f"""<img src="{cropped_attachments_url_src[url].image_src}" class="img img-fluid mx-auto o_we_image_cropped" loading="lazy" style="" data-bs-original-title="" title="" data-original-id="{attachments_url_src[url].id}" data-original-src="{attachments_url_src[url].image_src}" data-mimetype="image/jpeg" data-y="{cropping_dimensions['y']}" data-width="{cropping_dimensions['width']}" data-height="{cropping_dimensions['height']}" data-scale-x="1" data-scale-y="1" data-aspect-ratio="0/0">"""
                return re.sub(pattern=pattern, repl=cropped_img_string, string=new_block_html)
            return new_block_html

        homepage = odoo_blocks['homepage']
        homepage['body_html'] = update_page_html(homepage)

        footer = homepage.get('footer', [])
        if footer:
            homepage['footer'] = update_page_html({'body_html': footer, 'images': homepage.get('images', []), 'images_to_crop': homepage.get('images_to_crop', [])})

        header_buttons = homepage.get('header', {}).get('buttons', [])
        for button in header_buttons:
            menu_content = button.get('menu_content', {})
            if menu_content.get('type', '') == 'mega_menu':
                menu_content['content'] = update_page_html({'body_html': [menu_content.get('content', '')], 'images': homepage.get('images', []), 'images_to_crop': homepage.get('images_to_crop', [])})[0]

        # Update the html urls for all pages
        for page_name, page_dict in odoo_blocks.get('pages', {}).items():
            odoo_blocks['pages'][page_name]['body_html'] = update_page_html(page_dict)

    def _get_image_data(self, tar, image_name):
        if not image_name:
            return None
        try:
            image_data = tar.extractfile('images/' + image_name).read()
            return image_data
        except (KeyError, AttributeError) as e:
            logger.warning("Image %s not found : %s", image_name, e)
            return None

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
                'url': '/web',
                'target': 'self',
            }

        self.env['website_generator.request'].create({
            'uuid': ws_uuid,
            'target_url': ws_target_url,
        })
        ICP.set_param('website_generator.iap_ws_uuid', None)
        ICP.set_param('website_generator.iap_ws_target_url', None)

        action_id = self.env.ref('website_generator.website_generator_screen').id
        action_id = 'website_generator.website_generator_screen'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web?reload=true#action={action_id}',
            'target': 'self',
        }
