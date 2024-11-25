# Part of Odoo. See LICENSE file for full copyright and licensing details.
<<<<<<< 18.0
from odoo import models, api
||||||| a96cf28115fece7697b3622e5f21cf88187f99e7
from odoo import models
=======
from odoo import models
from odoo import api
>>>>>>> ca2d49d61fdbd725fe4225baa4918d530bd9b468


class ProductTag(models.Model):
    _name = 'product.tag'
    _inherit = ['product.tag', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
<<<<<<< 18.0
        return ['name']
||||||| a96cf28115fece7697b3622e5f21cf88187f99e7
=======
        return ['id', 'name']
>>>>>>> ca2d49d61fdbd725fe4225baa4918d530bd9b468
