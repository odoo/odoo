# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools
from lxml import etree, objectify


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _l10n_hu_navservice_load_xsd_files(self, force_reload=False):
        base_url = "https://raw.githubusercontent.com/OdooTech-hu/navservice-xsd/main/v3.0/"

        for filename in ("invoiceAnnulment.xsd", "invoiceApi.xsd", "invoiceData.xsd", "serviceMetrics.xsd"):
            tools.load_xsd_files_from_url(
                self.env,
                f"{base_url}{filename}",
                f"l10n_hu_navservice.{filename}",
                force_reload=force_reload,
                # xsd_name_prefix="l10n_hu_navservice",
                modify_xsd_content=lambda content: etree.tostring(
                    objectify.fromstring(content), encoding="utf-8", pretty_print=True
                ),
            )
        return
