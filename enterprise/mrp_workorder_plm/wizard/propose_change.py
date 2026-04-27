# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup

from odoo import SUPERUSER_ID, models, _
from odoo.tools import is_html_empty


class ProposeChange(models.TransientModel):
    _inherit = 'propose.change'

    def default_get(self, fields_list):
        res = super().default_get(fields_list=fields_list)
        if 'step_id' in fields_list:
            wo = self.env['quality.check'].browse(res.get('step_id')).workorder_id
            eco = self.env['mrp.eco'].sudo().search([
                ('bom_id', '=', wo.production_id.bom_id.id),
                ('state', 'in', ('confirmed', 'progress')),
            ])
            if eco:
                res['eco_type_id'] = eco.type_id.id
        return res

    def _get_eco(self):
        self.ensure_one()
        eco = self.env['mrp.eco'].sudo().search([
            ('bom_id', '=', self.workorder_id.production_id.bom_id.id),
            ('state', 'in', ('confirmed', 'progress')),
        ], limit=1)
        type_id = self.env.ref('mrp_plm.ecotype_bom_update')
        if not eco:
            wo_name = f'{self.workorder_id.name}/{self.workorder_id.production_id.name}'
            name = _("Instruction Suggestions (%(wo_name)s)", wo_name=wo_name)
            eco = self.env['mrp.eco'].sudo().create({
                'name': name,
                'product_tmpl_id': self.workorder_id.product_id.product_tmpl_id.id,
                'bom_id': self.workorder_id.production_id.bom_id.id,
                'type_id': type_id.id,
                'stage_id': self.env['mrp.eco.stage'].sudo().search([
                    ('type_ids', 'in', type_id.ids),
                ], limit=1).id
            })
            eco.action_new_revision()
        return eco

    def _do_update_step(self):
        eco = self._get_eco()
        original_title = self.step_id.title
        super()._do_update_step(notify_bom=False)
        # get the step on the new bom related to the one we want to update
        new_step = eco.new_bom_id.operation_ids.quality_point_ids.filtered(lambda p: p._get_sync_values() == self.step_id.point_id._get_sync_values())
        body = self._get_update_step_note(original_title)
        if new_step:
            new_step.note = self.step_id.note
            # Write reason in chatter for record keeping in case of multiple suggestions before approval
            new_step.message_post(body=body)
        else:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp_plm.model_mrp_eco').id,
                'res_id': eco.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback for not found step: %(step)s (%(production)s - %(operation)s)', step=self.step_id.point_id.title, production=self.workorder_id.production_id.name, operation=self.workorder_id.operation_id.name),
                'note': body,
            })

    def _do_remove_step(self):
        eco = self._get_eco()
        super()._do_remove_step(notify_bom=False)
        # get the step on the new bom related to the one we want to delete
        new_step = eco.new_bom_id.operation_ids.quality_point_ids.filtered(lambda p: p._get_sync_values() == self.step_id.point_id._get_sync_values())
        new_step.unlink()
        # Leave a note in the old step's chatter telling why it should be removed.
        old_step = self.step_id.point_id
        if old_step:
            old_step.message_post(body=self._get_remove_step_note())

    def _do_set_picture(self):
        eco = self._get_eco()
        super()._do_set_picture(notify_bom=False)
        # get the step on the new bom related to the one we want to update
        new_step = eco.new_bom_id.operation_ids.quality_point_ids.filtered(lambda p: p._get_sync_values() == self.step_id.point_id._get_sync_values())
        if new_step:
            # remove existing images, but keep existing text + append image after text
            existing_text = False
            image = Markup('<img style="max-width: 75%%" class="img-fluid" src="%s"/>') % self.image_url(self, 'picture')
            if not is_html_empty(new_step.note):
                existing_text = Markup(re.sub(self.IMG_REGEX, '', new_step.note))
            if existing_text and not is_html_empty(existing_text):
                new_step.note = existing_text + image
            else:
                new_step.note = image
            new_step.source_document = 'step'
            new_step.worksheet_document = False
            new_step.worksheet_url = False
            # Write reason in chatter for record keeping in case of multiple suggestions before approval
            new_step.message_post(body=self._get_set_picture_note())
        else:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp_plm.model_mrp_eco').id,
                'res_id': eco.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback for not found step: %(step)s (%(production)s - %(operation)s)', step=self.step_id.point_id.title, production=self.workorder_id.production_id.name, operation=self.workorder_id.operation_id.name),
                'note': self._get_set_picture_note(),
            })
