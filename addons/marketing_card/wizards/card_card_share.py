from odoo import api, fields, models

from ..utils.image_utils import scale_image_b64


class CardCardShare(models.TransientModel):
    _name = 'card.card.share'
    _description = 'Marketing Card Wizard'

    campaign_id = fields.Many2one('card.campaign', required=True)
    res_model = fields.Selection(related='campaign_id.res_model')
    record_ref = fields.Reference(string="Record", selection="_selection_record_ref", compute="_compute_record_ref", store=True, readonly=False)
    image = fields.Image(compute='_compute_image', readonly=True)
    url = fields.Char(compute='_compute_url', string="Link")

    @api.depends('res_model')
    def _compute_record_ref(self):
        """Used to set a value for the reference field, and thus its model."""
        for model, card_wizards in self.grouped('res_model').items():
            card_wizards.record_ref = self.env[model].search([], limit=1)

    @api.depends('campaign_id', 'record_ref')
    def _compute_image(self):
        self.image = False
        for share_wizard in self:
            if record := share_wizard.record_ref:
                image = share_wizard.campaign_id._get_images_b64(records=record)[record.id]
                share_wizard.image = scale_image_b64(image, 0.5)

    @api.depends('campaign_id', 'record_ref')
    def _compute_url_id(self):
        self.url_id = False
        for share_wizard in self.filtered('record_ref'):
            share_wizard.url_id = share_wizard.campaign_id._get_or_create_card_from_res_id(share_wizard.record_ref.id)

    @api.depends('campaign_id', 'record_ref')
    def _compute_url(self):
        for share_wizard in self:
            share_wizard.url = share_wizard.campaign_id._get_preview_url(share_wizard.record_ref.id)

    @api.model
    def _selection_record_ref(self):
        return self.env['card.card']._selection_record_ref()
