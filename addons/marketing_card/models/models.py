from odoo import models

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _marketing_card_allowed_field_paths(self):
        """List of fields allowed to be accessed in template rendering.

        :return list[str]:
        """
        return []
