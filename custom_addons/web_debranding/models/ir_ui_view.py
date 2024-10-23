# Copyright 2016-2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2017 ArtyomLosev <https://github.com/ArtyomLosev>
# Copyright 2017 Ilmir Karamov <https://it-projects.info/team/ilmir-k>
# Copyright 2022 IT-Projects <https://it-projects.info/>
# License MIT (https://opensource.org/licenses/MIT).

import logging

from odoo import api, models
from odoo.tools import mute_logger

from .ir_translation import debrand

_logger = logging.getLogger(__name__)

MODULE = "_web_debranding"


class View(models.Model):
    _inherit = "ir.ui.view"

    def get_combined_arch(self):
        res = super(View, self).get_combined_arch()
        res = debrand(self.env, res, is_code=True)
        return res

    @api.model
    def _create_debranding_views(self):
        """Create UI views that may work only in one Odoo edition"""
        return True

    @api.model
    def _create_view(self, name, inherit_id, arch, noupdate=False, view_type="qweb"):
        view = self.env.ref("{}.{}".format(MODULE, name), raise_if_not_found=False)
        if view:
            try:
                view.write({"arch": arch})
                view._check_xml()
            except Exception:
                _logger.warning(
                    "Cannot update view %s. Delete it.", name, exc_info=True
                )
                view.unlink()
                return

            return view.id

        try:
            with self.env.cr.savepoint(), mute_logger("odoo.models"):
                view = self.env["ir.ui.view"].create(
                    {
                        "name": name,
                        "type": view_type,
                        "arch": arch,
                        "inherit_id": self.env.ref(
                            inherit_id, raise_if_not_found=True
                        ).id,
                    }
                )
                view._check_xml()
        except Exception:
            _logger.debug("Cannot create view %s. Cancel.", name, exc_info=True)
            return
        self.env["ir.model.data"].create(
            {
                "name": name,
                "model": "ir.ui.view",
                "module": MODULE,
                "res_id": view.id,
                "noupdate": noupdate,
            }
        )
        return view.id
