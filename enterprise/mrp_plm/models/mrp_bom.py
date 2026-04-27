# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.osv import expression


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    version = fields.Integer('Version', default=1)
    previous_bom_id = fields.Many2one('mrp.bom', 'Previous BoM')
    active = fields.Boolean('Production Ready')
    image_128 = fields.Image(related='product_tmpl_id.image_128', readonly=False)
    eco_ids = fields.One2many(
        'mrp.eco', 'new_bom_id', 'ECO to be applied')
    eco_count = fields.Integer('# ECOs', compute='_compute_eco_data')

    def _compute_eco_data(self):
        previous_boms_mapping = self._get_previous_boms()
        previous_boms_list = list(previous_boms_mapping.keys())
        eco_data = self.env['mrp.eco']._read_group([
            ('bom_id', 'in', previous_boms_list)],
            ['bom_id'], ['__count'])
        eco_count = defaultdict(lambda: 0)
        for previous_bom, count in eco_data:
            for bom_id in previous_boms_mapping[previous_bom.id]:
                eco_count[bom_id] += count
        for bom in self:
            bom.eco_count = eco_count[bom.id]

    def apply_new_version(self):
        """ Put old BoM as deprecated - TODO: Set to stage that is production_ready """
        MrpEco = self.env['mrp.eco']
        for new_bom in self:
            new_bom.write({'active': True})
            # Move eco's into rebase state which is in progress state.
            ecos = MrpEco.search(['|',
                    ('bom_id', '=', new_bom.previous_bom_id.id),
                    ('current_bom_id', '=', new_bom.previous_bom_id.id),
                    ('new_bom_id', '!=', False),
                    ('new_bom_id', '!=', new_bom.id),
                    ('state', 'not in', ('done', 'new'))])
            ecos.write({'state': 'rebase', 'current_bom_id': new_bom.id})
            # Change old bom of eco which is in draft state.
            draft_ecos = MrpEco.search(['|',
                ('bom_id', '=', new_bom.previous_bom_id.id),
                ('current_bom_id', '=', new_bom.previous_bom_id.id),
                ('new_bom_id', '=', False)])
            draft_ecos.write({'bom_id': new_bom.id})
            # Deactivate previous revision of BoM
            new_bom.previous_bom_id.write({'active': False})
        return True

    def button_mrp_eco(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_plm.mrp_eco_action_main")
        previous_boms = self._get_previous_boms()
        action['domain'] = ['&', ('bom_id', 'in', list(previous_boms.keys())), ('type', '=', 'bom')]
        action['context'] = {
            'default_bom_id': self.id,
            'default_product_tmpl_id': self.product_tmpl_id.id,
        }
        return action

    def _get_previous_boms(self):
        """ Return a dictionary with the keys to be all the previous boms' id and
        the value to be a set of ids in self of which the key is their previous boms.
        """
        boms_data = self.with_context(active_test=False).search_read(
            [('product_tmpl_id', 'in', self.product_tmpl_id.ids)],
            fields=['id', 'previous_bom_id'], load=False,
            order='id desc, version desc')
        previous_boms = defaultdict(set, {bom.id: {bom.id} for bom in self})
        for bom_data in boms_data:
            if not bom_data['previous_bom_id']:
                continue
            bom_id = bom_data['id']
            previous_bom_id = bom_data['previous_bom_id']
            previous_boms[previous_bom_id] |= previous_boms[bom_id]
        return dict(previous_boms)

    def _get_active_version(self):
        self.ensure_one()
        domain = [('version', '>=', self.version)]
        if self.product_id:
            domain = expression.AND([domain, [('product_id', '=', self.product_id.id)]])
        else:
            domain = expression.AND([domain, [('product_tmpl_id', '=', self.product_tmpl_id.id)]])
        boms = self.with_context(active_test=False).search(domain, order='version, id')
        previous_boms = self
        for bom in boms:
            if bom.previous_bom_id not in previous_boms:
                continue
            previous_boms += bom
            if bom.active:
                return bom
        return False


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    def _prepare_rebase_line(self, eco, change_type, product_id, uom_id, operation_id=None, new_qty=0):
        self.ensure_one()
        return {
            'change_type': change_type,
            'product_id': product_id,
            'rebase_id': eco.id,
            'old_uom_id': self.product_uom_id.id,
            'new_uom_id': uom_id,
            'old_operation_id': self.operation_id.id,
            'new_operation_id': operation_id,
            'old_product_qty': 0.0 if change_type == 'add' else self.product_qty,
            'new_product_qty': new_qty,
            }

    def _create_or_update_rebase_line(self, ecos, operation, product_id, uom_id, operation_id=None, new_qty=0):
        self.ensure_one()
        BomChange = self.env['mrp.eco.bom.change'].sudo()
        for eco in ecos:
            # When product exist in new bill of material update line otherwise add line in rebase changes.
            rebase_line = BomChange.search([
                ('product_id', '=', product_id),
                ('rebase_id', '=', eco.id)], limit=1)
            if rebase_line:
                # Update existing rebase line or unlink it.
                if (rebase_line.old_product_qty, rebase_line.old_uom_id.id, rebase_line.old_operation_id.id) != (new_qty, uom_id, operation_id):
                    if rebase_line.change_type == 'update':
                        rebase_line.write({'new_product_qty': new_qty, 'new_operation_id': operation_id, 'new_uom_id': uom_id})
                    else:
                        rebase_line_vals = self._prepare_rebase_line(eco, 'add', product_id, uom_id, operation_id, new_qty)
                        rebase_line.write(rebase_line_vals)
                else:
                    rebase_line.unlink()
            else:
                rebase_line_vals = self._prepare_rebase_line(eco, operation, product_id, uom_id, operation_id, new_qty)
                BomChange.create(rebase_line_vals)
            eco.state = 'rebase' if eco.bom_rebase_ids or eco.previous_change_ids else 'progress'
        return True

    def _bom_line_change(self, vals, operation='update'):
        MrpEco = self.env['mrp.eco']
        for line in self:
            ecos = MrpEco.sudo().search([
                ('bom_id', '=', line.bom_id.id), ('state', 'in', ('progress', 'rebase')),
                ('type', 'in', ('bom', 'both'))
            ])
            if ecos:
                # Latest bom line (product, uom, operation_id, product_qty)
                product_id = vals.get('product_id', line.product_id.id)
                uom_id = vals.get('product_uom_id', line.product_uom_id.id)
                operation_id = vals.get('operation_id', line.operation_id.id)
                product_qty = vals.get('product_qty', line.product_qty)
                line._create_or_update_rebase_line(ecos, operation, product_id, uom_id, operation_id, product_qty)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            line._bom_line_change(vals, operation='add')
        return lines

    def write(self, vals):
        operation = 'update'
        if vals.get('product_id'):
            # It will create update rebase line with negative quantity.
            self._bom_line_change({'product_qty': 0.0}, operation)
            operation = 'add'
        self._bom_line_change(vals, operation)
        return super(MrpBomLine, self).write(vals)

    def unlink(self):
        # It will create update rebase line.
        self._bom_line_change({'product_qty': 0.0})
        return super(MrpBomLine, self).unlink()

    def _get_sync_values(self):
        if not self:
            return tuple()
        self.ensure_one()
        return tuple([self.product_id] + self.bom_product_template_attribute_value_ids.ids) + self.operation_id._get_sync_values()


class MrpByProduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    def _get_sync_values(self):
        if not self:
            return tuple()
        self.ensure_one()
        return tuple([self.product_id] + self.bom_product_template_attribute_value_ids.ids) + self.operation_id._get_sync_values()
