# Copyright 2015-2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2016 Stanislav Krotov <https://it-projects.info/team/ufaks>
# Copyright 2017 Ilmir Karamov <https://it-projects.info/team/ilmir-k>
# License MIT (https://opensource.org/licenses/MIT).

import logging

from odoo import models
from odoo.release import version_info

_logger = logging.getLogger(__name__)


class PublisherWarrantyContract(models.AbstractModel):
    _inherit = "publisher_warranty.contract"

    def update_notification(self, cron_mode=True):
        is_enterprise = version_info[5] == "e"
        _logger.debug("is_enterprise=%s", is_enterprise)
        # Running Odoo EE without calling super is illegal. So, make it impossible to disable in enterprise. See README.rst for details
        if (
            is_enterprise
            or self.env["ir.config_parameter"]
            .get_debranding_parameters()
            .get("web_debranding.send_publisher_warranty_url")
            == "1"
        ):
            return super(PublisherWarrantyContract, self).update_notification(cron_mode)
        else:
            return True
