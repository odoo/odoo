# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    eco_ids = fields.One2many('mrp.eco', 'production_id', string="ECOs", readonly=True)
    eco_count = fields.Integer(compute="_compute_eco_count")
    latest_bom_id = fields.Many2one('mrp.bom', compute="_compute_latest_bom_id")

    @api.depends('eco_ids')
    def _compute_eco_count(self):
        for mo in self:
            mo.eco_count = len(mo.eco_ids)

    @api.depends('bom_id', 'bom_id.active', 'bom_id.bom_line_ids')
    def _compute_latest_bom_id(self):
        self.latest_bom_id = False
        mo_ids_without_latest_bom = []
        # check if the bom has a new version
        for mo in self:
            if not mo.bom_id or not mo.id:  # Avoid MO who wasn't saved yet.
                continue
            if not mo.bom_id.active:
                mo.latest_bom_id = mo.bom_id._get_active_version()
            if not mo.latest_bom_id:
                mo_ids_without_latest_bom.append(mo.id)
        # Checks if the MO has some component move from an outdated BoM (can happen with exploded kit).
        mos_with_component_from_outdated_kit = self.search([
            ('id', 'in', mo_ids_without_latest_bom),
            ('move_raw_ids.bom_line_id.bom_id.active', '=', False)
        ])
        # For these MOs, we assign their current BoM as the latest one in the purpose to enable the
        # "Update BoM" action on these MOs, that way, the raw moves from a kit will be recreated
        # from the active version of their BoM.
        for mo in mos_with_component_from_outdated_kit:
            mo.latest_bom_id = mo.bom_id

    def action_create_eco(self):
        self.ensure_one()
        if not self.bom_id:  # Can't do anything if no BoM.
            raise UserError(_("Cannot create an ECO if the Manufacturing Order doesn't use a Bill of Materials"))
        # Tries to retrieves "Bill of Materials" ECO type.
        eco_type = self.env.ref('mrp_plm.ecotype_bom_update', raise_if_not_found=False)
        if not eco_type:
            eco_type = self.env['mrp.eco.type'].sudo().search([], limit=1)
        eco_stage = eco_type.stage_ids[:1]
        action = self.env['ir.actions.act_window']._for_xml_id('mrp_plm.mrp_eco_action_main')
        action["views"] = [(False, 'form')]
        action['context'] = {
            'default_bom_id': self.bom_id.id,
            'default_name': _("BoM Suggestions from %(mo_name)s", mo_name=self.display_name),
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_production_id': self.id,
            'default_type_id': eco_type.id,
            'default_stage_id': eco_stage.id,
        }
        return action

    def action_open_eco(self):
        action = self.env['ir.actions.act_window']._for_xml_id('mrp_plm.mrp_eco_action_main')
        if len(self.eco_ids) == 1:
            action['res_id'] = self.eco_ids.id
            action['views'] = [(False, 'form')]
        else:
            action['domain'] = [('id', 'in', self.eco_ids.ids)]
            action['views'].insert(0, action['views'].pop(1))  # Place list view in first position.
        return action

    def action_update_bom(self):
        productions_without_latest_bom = self.env['mrp.production']
        for production in self:
            if not production.latest_bom_id:
                productions_without_latest_bom |= production
            elif production.state in ['draft', 'confirmed']:
                production._link_bom(production.latest_bom_id)
        super(MrpProduction, productions_without_latest_bom).action_update_bom()

    def _create_revision_bom(self, will_update_version=True):
        """ Compares the MO's components, by-products and workorders with its BoM's lines,
        by-products and operations to create and return a new BoM that copies the MO's BoM but
        includes the changes, deletions and additions made in the MO.
        """
        self.ensure_one()
        if not self.bom_id:  # Can't do anything if no BoM.
            return False
        ratio = self._get_ratio_between_mo_and_bom_quantities(self.bom_id)
        revision_bom_lines_vals, revision_byproduct_vals, revision_operations_vals = self._get_bom_values(ratio)
        revision_bom = self.env['mrp.bom'].create({
            'active': False,
            'bom_line_ids': revision_bom_lines_vals,
            'byproduct_ids': revision_byproduct_vals,
            'code': _("New BoM from %(mo_name)s", mo_name=self.display_name),
            'company_id': self.company_id.id,
            'operation_ids': revision_operations_vals,
            'previous_bom_id': self.bom_id.id,
            'product_id': self.bom_id.product_id.id,
            'product_qty': self.bom_id.product_qty,
            'product_tmpl_id': self.bom_id.product_tmpl_id.id,
            'product_uom_id': self.bom_id.product_uom_id.id,
            'version': will_update_version and self.bom_id.version + 1 or self.bom_id.version,
        })
        return revision_bom
