import logging

# from odoo import fields, models
from odoo import models

_logger = logging.getLogger(__name__)


class IrModel(models.Model):
    _inherit = 'ir.model'

    # is_abstract = fields.Boolean(
    #     compute='_compute_is_abstract', store=True, )
    #
    # def _compute_is_abstract(self):
    #     for obj in self:
    #         obj.is_abstract = self.env[obj.model].sudo()._abstract
