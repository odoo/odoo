from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def action_view_install_request(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "target": "new",
            "name": self.env._('Activation Request of "%s"', self.shortdesc),
            "view_mode": "form",
            "res_model": "base.module.install.request",
            "views": [
                (
                    self.env.ref(
                        "base_install_request.base_module_install_request_view_form"
                    ).id,
                    "form",
                )
            ],
            "context": {"default_module_id": self.id},
        }
