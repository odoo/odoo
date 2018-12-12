# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

from itertools import groupby


class MrpBom(models.Model):
    """ Defines bills of material for a product or a product template """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = ['mail.thread']
    _rec_name = 'product_tmpl_id'
    _order = "sequence"

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    code = fields.Char('Reference')
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the bills of material without removing it.")
    type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'Kit')], 'BoM Type',
        default='normal', required=True)
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        domain="[('type', 'in', ['product', 'consu'])]", required=True)
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ['product', 'consu'])]",
        help="If a product variant is defined the BOM is available only for this product.")
    bom_line_ids = fields.One2many('mrp.bom.line', 'bom_id', 'BoM Lines', copy=True)
    byproduct_ids = fields.One2many('mrp.bom.byproduct', 'bom_id', 'By-products', copy=True)
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id, oldname='product_uom', required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control", domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of bills of material.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        help="The operations for producing this BoM.  When a routing is specified, the production orders will "
             " be executed through work orders, otherwise everything is processed in the production order itself. ")
    ready_to_produce = fields.Selection([
        ('all_available', ' When all components are available'),
        ('asap', 'When components for 1st operation are available')], string='Manufacturing Readiness',
        default='asap', help="Defines when a Manufacturing Order is considered as ready to be started", required=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', domain=[('code', '=', 'mrp_operation')],
        help=u"When a procurement has a ‘produce’ route with a operation type set, it will try to create "
             "a Manufacturing Order for that product using a BoM of the same operation type. That allows "
             "to define stock rules which trigger different manufacturing orders with different BoMs.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        required=True)
    consumption = fields.Selection([
        ('strict', 'Strict'),
        ('flexible', 'Flexible')],
        help="Defines if you can consume more or less components than the quantity defined on the BoM.",
        default='strict',
        string='Consumption'
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            for line in self.bom_line_ids:
                line.attribute_value_ids = False

    @api.constrains('product_id', 'product_tmpl_id', 'bom_line_ids')
    def _check_product_recursion(self):
        for bom in self:
            if bom.product_id:
                if bom.bom_line_ids.filtered(lambda x: x.product_id == bom.product_id):
                    raise ValidationError(_('BoM line product %s should not be same as BoM product.') % bom.display_name)
            else:
                if bom.bom_line_ids.filtered(lambda x: x.product_id.product_tmpl_id == bom.product_tmpl_id):
                    raise ValidationError(_('BoM line product %s should not be same as BoM product.') % bom.display_name)

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        res = {}
        if not self.product_uom_id or not self.product_tmpl_id:
            return
        if self.product_uom_id.category_id.id != self.product_tmpl_id.uom_id.category_id.id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
        return res

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            if self.product_id.product_tmpl_id != self.product_tmpl_id:
                self.product_id = False
            for line in self.bom_line_ids:
                line.attribute_value_ids = False

    @api.onchange('routing_id')
    def onchange_routing_id(self):
        for line in self.bom_line_ids:
            line.operation_id = False

    @api.multi
    def name_get(self):
        return [(bom.id, '%s%s' % (bom.code and '%s: ' % bom.code or '', bom.product_tmpl_id.display_name)) for bom in self]

    @api.multi
    def unlink(self):
        if self.env['mrp.production'].search([('bom_id', 'in', self.ids), ('state', 'not in', ['done', 'cancel'])], limit=1):
            raise UserError(_('You can not delete a Bill of Material with running manufacturing orders.\nPlease close or cancel it first.'))
        return super(MrpBom, self).unlink()

    @api.model
    def _bom_find_domain(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
        if product:
            if not product_tmpl:
                product_tmpl = product.product_tmpl_id
            domain = ['|', ('product_id', '=', product.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl.id)]
        elif product_tmpl:
            domain = [('product_tmpl_id', '=', product_tmpl.id)]
        else:
            # neither product nor template, makes no sense to search
            raise UserError(_('You should provide either a product or a product template to search a BoM'))
        if picking_type:
            domain += ['|', ('picking_type_id', '=', picking_type.id), ('picking_type_id', '=', False)]
        if company_id or self.env.context.get('company_id'):
            domain = domain + [('company_id', '=', company_id or self.env.context.get('company_id'))]
        if bom_type:
            domain += [('type', '=', bom_type)]
        # order to prioritize bom with product_id over the one without
        return domain

    @api.model
    def _bom_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
        """ Finds BoM for particular product, picking and company """
        domain = self._bom_find_domain(product_tmpl=product_tmpl, product=product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
        if domain is False:
            return domain
        return self.search(domain, order='sequence, product_id', limit=1)

    def explode(self, product, quantity, picking_type=False):
        """
            Explodes the BoM and creates two lists with all the information you need: bom_done and line_done
            Quantity describes the number of times you need the BoM: so the quantity divided by the number created by the BoM
            and converted into its UoM
        """
        from collections import defaultdict

        graph = defaultdict(list)
        V = set()

        def check_cycle(v, visited, recStack, graph):
            visited[v] = True
            recStack[v] = True
            for neighbour in graph[v]:
                if visited[neighbour] == False:
                    if check_cycle(neighbour, visited, recStack, graph) == True:
                        return True
                elif recStack[neighbour] == True:
                    return True
            recStack[v] = False
            return False

        boms_done = [(self, {'qty': quantity, 'product': product, 'original_qty': quantity, 'parent_line': False})]
        lines_done = []
        V |= set([product.product_tmpl_id.id])

        bom_lines = [(bom_line, product, quantity, False) for bom_line in self.bom_line_ids]
        for bom_line in self.bom_line_ids:
            V |= set([bom_line.product_id.product_tmpl_id.id])
            graph[product.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)
        while bom_lines:
            current_line, current_product, current_qty, parent_line = bom_lines[0]
            bom_lines = bom_lines[1:]

            if current_line._skip_bom_line(current_product):
                continue

            line_quantity = current_qty * current_line.product_qty
            bom = self._bom_find(product=current_line.product_id, picking_type=picking_type or self.picking_type_id, company_id=self.company_id.id, bom_type='phantom')
            if bom:
                converted_line_quantity = current_line.product_uom_id._compute_quantity(line_quantity / bom.product_qty, bom.product_uom_id)
                bom_lines = [(line, current_line.product_id, converted_line_quantity, current_line) for line in bom.bom_line_ids] + bom_lines
                for bom_line in bom.bom_line_ids:
                    graph[current_line.product_id.product_tmpl_id.id].append(bom_line.product_id.product_tmpl_id.id)
                    if bom_line.product_id.product_tmpl_id.id in V and check_cycle(bom_line.product_id.product_tmpl_id.id, {key: False for  key in V}, {key: False for  key in V}, graph):
                        raise UserError(_('Recursion error!  A product with a Bill of Material should not have itself in its BoM or child BoMs!'))
                    V |= set([bom_line.product_id.product_tmpl_id.id])
                boms_done.append((bom, {'qty': converted_line_quantity, 'product': current_product, 'original_qty': quantity, 'parent_line': current_line}))
            else:
                # We round up here because the user expects that if he has to consume a little more, the whole UOM unit
                # should be consumed.
                rounding = current_line.product_uom_id.rounding
                line_quantity = float_round(line_quantity, precision_rounding=rounding, rounding_method='UP')
                lines_done.append((current_line, {'qty': line_quantity, 'product': current_product, 'original_qty': quantity, 'parent_line': parent_line}))

        return boms_done, lines_done

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Bills of Materials'),
            'template': '/mrp/static/xls/mrp_bom.xls'
        }]


class MrpBomLine(models.Model):
    _name = 'mrp.bom.line'
    _order = "sequence, id"
    _rec_name = "product_id"
    _description = 'Bill of Material Line'

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    product_id = fields.Many2one(
        'product.product', 'Component', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id', readonly=False)
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id,
        oldname='product_uom', required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control", domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    sequence = fields.Integer(
        'Sequence', default=1,
        help="Gives the sequence order when displaying.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        related='bom_id.routing_id', store=True, readonly=False,
        help="The list of operations to produce the finished product. The routing is mainly used to "
             "compute work center costs during operations and to plan future loads on work centers "
             "based on production planning.")
    bom_id = fields.Many2one(
        'mrp.bom', 'Parent BoM',
        index=True, ondelete='cascade', required=True)
    parent_product_tmpl_id = fields.Many2one('product.template', 'Parent Product Template', related='bom_id.product_tmpl_id')
    valid_product_attribute_value_ids = fields.Many2many('product.attribute.value', related='bom_id.product_tmpl_id.valid_product_attribute_value_ids')
    attribute_value_ids = fields.Many2many(
        'product.attribute.value', string='Apply on Variants',
        help="BOM Product Variants needed form apply this line.")
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Consumed in Operation',
        help="The operation where the components are consumed, or the finished products created.")
    child_bom_id = fields.Many2one(
        'mrp.bom', 'Sub BoM', compute='_compute_child_bom_id')
    child_line_ids = fields.One2many(
        'mrp.bom.line', string="BOM lines of the referred bom",
        compute='_compute_child_line_ids')
    attachments_count = fields.Integer('Attachments Count', compute='_compute_attachments_count')

    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>=0)', 'All product quantities must be greater or equal to 0.\n'
            'Lines with 0 quantities can be used as optional lines. \n'
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs !'),
    ]

    @api.depends('product_id', 'bom_id')
    def _compute_child_bom_id(self):
        for line in self:
            if not line.product_id:
                line.child_bom_id = False
            else:
                line.child_bom_id = self.env['mrp.bom']._bom_find(
                    product_tmpl=line.product_id.product_tmpl_id,
                    product=line.product_id,
                    picking_type=line.bom_id.picking_type_id)

    @api.depends('product_id')
    def _compute_attachments_count(self):
        for line in self:
            nbr_attach = self.env['mrp.document'].search_count([
                '|',
                '&', ('res_model', '=', 'product.product'), ('res_id', '=', line.product_id.id),
                '&', ('res_model', '=', 'product.template'), ('res_id', '=', line.product_id.product_tmpl_id.id)])
            line.attachments_count = nbr_attach

    @api.depends('child_bom_id')
    def _compute_child_line_ids(self):
        """ If the BOM line refers to a BOM, return the ids of the child BOM lines """
        for line in self:
            line.child_line_ids = line.child_bom_id.bom_line_ids.ids

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        res = {}
        if not self.product_uom_id or not self.product_id:
            return res
        if self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            self.product_uom_id = self.product_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('parent_product_tmpl_id')
    def onchange_parent_product(self):
        if not self.parent_product_tmpl_id:
            return {}
        return {'domain': {'attribute_value_ids': [
            ('id', 'in', self.parent_product_tmpl_id.valid_product_attribute_value_ids.ids),
            ('attribute_id.create_variant', '!=', 'no_variant')
        ]}}

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        return super(MrpBomLine, self).create(vals_list)

    def _skip_bom_line(self, product):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control. It currently checks that all variant values are in the
        product. """
        if self.attribute_value_ids:
            for att, att_values in groupby(self.attribute_value_ids, lambda l: l.attribute_id):
                values = self.env['product.attribute.value'].concat(*list(att_values))
                if not (product.attribute_value_ids & values):
                    return True
        return False

    @api.multi
    def action_see_attachments(self):
        domain = [
            '|',
            '&', ('res_model', '=', 'product.product'), ('res_id', '=', self.product_id.id),
            '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.product_tmpl_id.id)]
        attachment_view = self.env.ref('mrp.view_document_file_kanban_mrp')
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'mrp.document',
            'type': 'ir.actions.act_window',
            'view_id': attachment_view.id,
            'views': [(attachment_view.id, 'kanban'), (False, 'form')],
            'view_mode': 'kanban,tree,form',
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Upload files to your product
                    </p><p>
                        Use this feature to store any files, like drawings or specifications.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % ('product.product', self.product_id.id)
        }


class MrpByProduct(models.Model):
    _name = 'mrp.bom.byproduct'
    _description = 'Byproduct'

    product_id = fields.Many2one('product.product', 'By-product', required=True)
    product_qty = fields.Float(
        'Quantity',
        default=1.0, digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    bom_id = fields.Many2one('mrp.bom', 'BoM', ondelete='cascade')
    operation_id = fields.Many2one('mrp.routing.workcenter', 'Produced in Operation')

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Changes UoM if product_id changes. """
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('product_uom_id')
    def onchange_uom(self):
        res = {}
        if self.product_uom_id and self.product_id and self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {
                'title': _('Warning'),
                'message': _('The unit of measure you choose is in a different category than the product unit of measure.')
            }
            self.product_uom_id = self.product_id.uom_id.id
        return res
