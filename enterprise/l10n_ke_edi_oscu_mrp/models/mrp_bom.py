# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    """ Defines bills of material for a product or a product template """
    _inherit = 'mrp.bom'

    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')
    l10n_ke_validation_message = fields.Json(compute='_compute_l10n_ke_validation_message')

    @api.depends('company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            allowed_companies = record.company_id or self.env.companies
            record.fiscal_country_codes = ",".join(allowed_companies.mapped('account_fiscal_country_id.code'))

    @api.depends_context('allowed_company_ids')
    @api.depends(
        'product_id',
        'product_tmpl_id',
        'bom_line_ids.product_id',
    )
    def _compute_l10n_ke_validation_message(self):
        for bom in self:
            if not self.env.company.l10n_ke_oscu_is_active:
                bom.l10n_ke_validation_message = False
                continue
            products = bom.product_id or bom.product_tmpl_id.product_variant_ids
            products |= bom.bom_line_ids.product_id
            bom.l10n_ke_validation_message = products._l10n_ke_get_validation_messages(for_invoice=False)

    def action_l10n_ke_send_bom(self):
        """ Send the BoM to eTIMS. """
        self.ensure_one()
        # Search for all variants for which this BoM is valid
        variants = self.product_id or self.product_tmpl_id.product_variant_ids
        contents = []
        if (blocking := [msg for msg in (self.l10n_ke_validation_message or {}).values() if msg.get('blocking')]):
            raise UserError(_(
                "This bill of materials cannot be registered on eTIMS until following points are resolved: %s",
                ''.join([f"\n- {msg['message']}" for msg in blocking]),
            ))

        for product in (variants | self.bom_line_ids.product_id).filtered(lambda p: not p.l10n_ke_item_code):
            product.action_l10n_ke_oscu_save_item()

        for product in variants:
            for bom_line in self.bom_line_ids:
                content = {
                    "itemCd": product.l10n_ke_item_code,
                    "cpstItemCd": bom_line.product_id.l10n_ke_item_code,
                    "cpstQty": bom_line.product_qty,
                    **self.env.company._l10n_ke_get_user_dict(bom_line.create_uid, bom_line.write_uid),
                }
                sending_company = bom_line.company_id or self.env.company
                error, _data, _date = sending_company._l10n_ke_call_etims('saveItemComposition', content)
                if error:
                    raise UserError(error['message'])
                contents.append(content)
        # If no error: message_post
        if contents:
            self.env['ir.attachment'].create({
                'name': 'KRA ' + self.display_name + '.json',
                'res_model': 'mrp.bom',
                'res_id': self.id,
                'raw': "\n".join(json.dumps(p, indent=4) for p in contents),
                })
        self.message_post(body=_("BoM successfully sent to KRA"))
