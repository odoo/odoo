# -*- coding: utf-8 -*-
"""
Company Model Customizations
=============================

Customizes res.company for ViaSuite branding defaults.
"""

from odoo import models, api
from odoo.addons.via_suite_base.utils.logger import get_logger

logger = get_logger(__name__)


class ResCompany(models.Model):
    """
    Extended Company model for ViaSuite defaults.

    Sets default branding for new companies:
    - Default logo
    - Color scheme
    - Email settings
    """

    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        """
        Override create to apply ViaSuite defaults.

        Args:
            vals (dict): Company values

        Returns:
            res.company: Created company record
        """
        # Apply ViaSuite defaults if not specified
        if 'email' not in vals:
            vals['email'] = 'no-reply@viafronteira.com'

        # Create company
        company = super(ResCompany, self).create(vals)

        logger.info(
            "company_created",
            company_id=company.id,
            company_name=company.name,
            tenant=self.env.cr.dbname
        )

        return company

    def _apply_viasuite_defaults(self):
        """
        Apply ViaSuite branding defaults to company.

        This is called during post_init_hook to configure the default company.
        """
        self.ensure_one()

        try:
            # Set company logo (will be set by logo_updater in hooks)
            # Set color scheme
            vals = {}

            # Update primary color (used in various UI elements)
            vals['primary_color'] = '#FF730E'  # ViaSuite orange

            # Update email if not set
            if not self.email:
                vals['email'] = 'no-reply@viafronteira.com'

            # Update website if not set
            if not self.website:
                vals['website'] = 'https://www.viafronteira.com'

            if vals:
                self.write(vals)

                logger.info(
                    "company_viasuite_defaults_applied",
                    company_id=self.id,
                    company_name=self.name
                )

        except Exception as e:
            logger.error(
                "company_defaults_error",
                company_id=self.id,
                error=str(e)
            )