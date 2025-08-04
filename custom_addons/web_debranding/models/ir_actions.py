# Copyright 2015-2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2017 Ilmir Karamov <https://it-projects.info/team/ilmir-k>
# License MIT (https://opensource.org/licenses/MIT).

from odoo import models


class IrActionsActWindowDebranding(models.Model):
    _inherit = "ir.actions.act_window"

    def read(self, fields=None, load="_classic_read"):
        results = super(IrActionsActWindowDebranding, self).read(
            fields=fields, load=load
        )
        if not fields or "help" in fields:
            params = self.env["ir.config_parameter"].get_debranding_parameters()
            new_name = params.get("web_debranding.new_name")
            for res in results:
                if isinstance(res, dict) and res.get("help"):
                    res["help"] = res["help"].replace("Odoo", new_name)
        return results
