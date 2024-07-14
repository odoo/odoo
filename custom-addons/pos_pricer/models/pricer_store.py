import requests
import re
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)
PRICER_REQUESTS_TIMEOUT = 10

def setup_requests_session(requests_session, pricer_login, pricer_password, auth_url):
    """
    Setup the jwt token for the authentification in requests_session
    """
    try:
        # Get a new JWT token
        response = requests_session.get(auth_url, auth=(pricer_login, pricer_password), timeout=PRICER_REQUESTS_TIMEOUT)
        response.raise_for_status()
        jwt_token = response.json().get('token')
        requests_session.headers.update({'Authorization': f'Bearer {jwt_token}'})
    except requests.exceptions.RequestException as e:
        _logger.warning("Failed to update the jwt token through Pricer API URL: %s: %s", auth_url, e)

class PricerStore(models.Model):
    _name = 'pricer.store'
    _description = 'Pricer Store regrouping pricer tags'

    # The name of the Pricer store in Odoo
    name = fields.Char(
        string='Store Name',
        help='Pricer Store name in Odoo database',
        required=True
    )

    # Fields used for Pricer API requests
    # All the 4 following fields need to be provided to clients by Pricer
    pricer_store_identifier = fields.Char(
        string='Pricer Store ID',
        help='Identifier of the store in the Pricer system',
        required=True
    )
    pricer_tenant_name = fields.Char(
        string='Pricer Tenant Name',
        help='Your company identifier at Pricer',
        required=True
    )
    pricer_login = fields.Char(
        string='Pricer Login',
        help='Login of your Pricer account',
        required=True
    )
    pricer_password = fields.Char(
        string='Pricer Password',
        help='Password of your Pricer account',
        required=True
    )

    # Products and Pricer tags associated to the Pricer Store
    product_ids = fields.One2many(
        comodel_name='product.template',
        inverse_name='pricer_store_id',
        string='Products',
    )
    pricer_tag_ids = fields.One2many(
        comodel_name='pricer.tag',
        inverse_name='pricer_store_id',
        string='Pricer Tags',
    )

    # Update status fields
    last_update_datetime = fields.Datetime(
        string="Last Update",
        help='Date and time of the last synchronization with Pricer',
        readonly=True,
    )
    last_update_status_message = fields.Char(
        string='Last Update Status',
        help='Status message of the last synchronization with Pricer',
        readonly=True,
    )

    # ------------------------- PRICER API URLs -------------------------
    # For authentification: "https://central-manager.[PRICER_TENANT_NAME].pcm.pricer-plaza.com[PRICER_API_SUFFIX]"
    # For other requests: "https://[PRICER_STORE_NAME].[PRICER_TENANT_NAME].pcm.pricer-plaza.com[PRICER_API_SUFFIX]"
    # Example: "https://1234.odoo-be.pcm.pricer-plaza.com/api/public/core/v1/items"
    auth_url = fields.Char(compute='_compute_auth_url')
    create_or_update_products_url = fields.Char(compute='_compute_create_or_update_products_url')
    link_tags_url = fields.Char(compute='_compute_link_tags_url')

    # Their "compute" methods
    @api.depends('pricer_tenant_name')
    def _compute_auth_url(self):
        for record in self:
            record.auth_url = f'https://central-manager.{record.pricer_tenant_name}.pcm.pricer-plaza.com/api/public/auth/v1/login'

    @api.depends('pricer_store_identifier', 'pricer_tenant_name')
    def _compute_create_or_update_products_url(self):
        for record in self:
            record.create_or_update_products_url = f'https://{record.pricer_store_identifier}.{record.pricer_tenant_name}.pcm.pricer-plaza.com/api/public/core/v1/items'

    @api.depends('pricer_store_identifier', 'pricer_tenant_name')
    def _compute_link_tags_url(self):
        for record in self:
            record.link_tags_url = f'https://{record.pricer_store_identifier}.{record.pricer_tenant_name}.pcm.pricer-plaza.com/api/public/core/v1/labels'


    # ------------------------- CONSTRAINS -------------------------
    @api.constrains('pricer_store_identifier')
    def _check_pricer_store_identifier(self):
        """
        Pricer Store ID must:
            1) Consist of: a-z, 0-9 or '-'
            2) Must start with a-z or 0-9
        """
        for record in self:
            if not re.fullmatch(r'^[a-z0-9][a-z0-9-]*$', record.pricer_store_identifier):
                raise ValidationError(_("Pricer Store ID must only contain lowercase a-z, 0-9 or '-' and not start with '-'"))

    # ------------------------- API METHODS -------------------------
    def unlink_label(self, pricer_tag_id):
        """
        Stop displaying product infromation on a pricer tag when deleting it from Odoo database
        """
        unlink_tag_url = f'https://{self.pricer_store_identifier}.{self.pricer_tenant_name}.pcm.pricer-plaza.com/api/public/core/v1/labels/{pricer_tag_id}/links'

        with requests.Session() as requests_session:
            try:
                setup_requests_session(requests_session, self.pricer_login, self.pricer_password, self.auth_url)
                response = requests_session.delete(unlink_tag_url, timeout=PRICER_REQUESTS_TIMEOUT)
                response.raise_for_status()
                _logger.info("Succesfully unlinked products from Pricer tag %s at Pricer API URL: %s", pricer_tag_id, unlink_tag_url)
            except requests.exceptions.RequestException as e:
                _logger.warning("Failed to unlink product from Pricer tag %s at Pricer API URL: %s: %s", pricer_tag_id, unlink_tag_url, e)
                raise UserError(_('Failed to unlink Pricer tag %s at API url %s', pricer_tag_id, unlink_tag_url))

    def action_button_update_pricer_tags(self):
        """
        Action assigned to buttons which allow the user to manually call Pricer API
        self here contains the recordset of selected Pricer Stores in their list view
        """
        # Recover arguments from xml context
        self._update_pricer_tags(self.env.context.get('update_all') or False)

    def _update_pricer_tags(self, update_all):
        """
        This method is regularly called by a cron in pricer module
        The interval is defined in data/pricer_ir_cron.xml
        This is done to avoid doing excessive API requests on every action
        while maintaining user's pricer tags synchronized with Odoo database

        A button on list view of pricer stores allows the user to manually call this method
        If called manually, instead of going through ALL the pricer stores in the database,
        it will only check the pricer stores specified in its "pricer_stores_to_update" argument
        """
        # Go through every Pricer store and build a JSON request body for it
        with requests.Session() as requests_session:
            for pricer_store in self:
                create_or_update_request_body = []
                link_request_body = []

                for product_id in pricer_store.product_ids:
                    # Check if the product needs to be created / update on Pricer db
                    if product_id.pricer_product_to_create_or_update or update_all:
                        create_or_update_request_body.append(product_id._get_create_or_update_body())
                        product_id.pricer_product_to_create_or_update = False
                        for pricer_tag_id in product_id.pricer_tag_ids:
                            # Check if the pricer tag needs to be linked to a product
                            if pricer_tag_id.pricer_product_to_link or update_all:
                                link_request_body.append(pricer_tag_id._get_link_body())
                                pricer_tag_id.pricer_product_to_link = False

                # If needed, call the Pricer api to update/create products and link the price tags
                if create_or_update_request_body or link_request_body:
                    try:
                        setup_requests_session(requests_session, pricer_store.pricer_login, pricer_store.pricer_password, pricer_store.auth_url)
                        # Create / Update products at Pricer database
                        if create_or_update_request_body:
                            response = requests_session.patch(pricer_store.create_or_update_products_url, json=create_or_update_request_body, timeout=PRICER_REQUESTS_TIMEOUT)
                            response.raise_for_status()
                            _logger.info("Succesfully created/updated products information for %s at Pricer API url: %s", pricer_store.name, pricer_store.create_or_update_products_url)
                        # Link the new Pricer tags to the existing products on their database
                        if link_request_body:
                            response = requests_session.patch(pricer_store.link_tags_url, json=link_request_body, timeout=PRICER_REQUESTS_TIMEOUT)
                            response.raise_for_status()
                            _logger.info("Succesfully linked Pricer labels to products for %s at Pricer API URL: %s", pricer_store.name, pricer_store.link_tags_url)
                        pricer_store.last_update_status_message = _("Update successfully sent to Pricer")
                    except requests.exceptions.RequestException as e:
                        _logger.warning(e)
                        if e.response:
                            pricer_store.last_update_status_message = _("Error: %s - %s", e.response.status_code, e.response.reason)
                        else:
                            pricer_store.last_update_status_message = _("Error: check Pricer credentials")
                    finally:
                        pricer_store.last_update_datetime = fields.Datetime.now()
