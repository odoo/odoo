# -*- coding: utf-8 -*-
"""Classes extending the populate factory for Companies and related models.

Only adding specificities of basic accounting applications.
"""
from odoo import models

import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """Populate factory part for the accountings applications of res.company."""

    _inherit = "res.company"

    def _populate(self, size):
        _logger.info('Loading Chart Template')
        records = super()._populate(size)

        # Load the a chart of accounts matching the country_id of the company for the 3 first created companies
        # We are loading an existing CoA and not populating it because:
        #   * it reflects best real use cases.
        #   * it allows checking reports by localization
        #   * the config is complete with try_loading(), no need to adapt when the model changes
        #   * it is way easier :-)
        # We are loading only for 3 companies because:
        #   * It takes a few hundreds of a second to create account.move records in batch.
        #     Because we want to have a lot of entries for at least one company (in order to test
        #     reports, functions and widgets performances for instance), we can't afford to do it for
        #     a lot of companies.
        #   * it would be useless to have entries for all the companies, we can already do everything with
        #     entries in only a few (but multiple) companies.
        # Note that we can still populate some new records on top of the CoA if it makes sense,
        # like account.journal for instance.
        for company in records[:3]:
            self.env['account.chart.template'].try_loading(company=company, template_code=None)
        return records
