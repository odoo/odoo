from odoo import models, fields
from werkzeug.urls import url_join
import logging

_logger = logging.getLogger(__name__)


class WebsiteTechnicalPage(models.Model):
    """
    Model to manage technical website pages in Odoo,
    capturing CMS and route URLs with relevant view and website associations.
    """
    _name = 'website.technical.page'
    _description = "Website Technical Page"

    website_url_technical_page = fields.Char(
        'Website URL',
        help='The full relative URL to access the document through the website.'
    )
    name_technical_page = fields.Char(
        'Name',
        help='The name of the page. This is used to identify the page in the website.'
    )
    website_technical_page_id = fields.Many2one(
        "website",
        string="Website",
        ondelete="restrict",
        help="Restrict to a specific website.",
        index=True
    )
    view_id = fields.Many2one(
        'ir.ui.view',
        string='View',
        required=True,
        index=True,
        ondelete="cascade"
    )

    def open_website_url(self):
        """
        Opens the technical page in the frontend website, based on the URL and website.
        """
        website_id = self.website_technical_page_id.id if self.website_technical_page_id else False

        if self.website_technical_page_id and self.website_technical_page_id.domain:
            client_action_url = self.env['website'].get_client_action_url(self.website_url_technical_page)
            client_action_url = f'{client_action_url}&website_id={website_id}'
            return {
                'type': 'ir.actions.act_url',
                'url': url_join(self.website_technical_page_id.domain, client_action_url),
                'target': 'self',
            }

        return self.env['website'].get_client_action(self.website_url_technical_page, False, website_id)
