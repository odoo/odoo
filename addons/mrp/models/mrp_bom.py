# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    """
    Defines bills of material for a product.
    """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = ['mail.thread']
    # TDE FIXME: _rec_name
    _name_rec = 'product_tmpl_id'
    _order = "sequence"

    def _get_default_product_uom_id(self):
        return self.env['product.uom'].search([], limit=1, order='id').id

    code = fields.Char('Reference')
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the bills of material without removing it.")
    type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'Ship this product as a set of components (kit)')],
        string='BoM Type', default='normal', required=True,
        help="Set: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product.")
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        domain="[('type', 'in', ['product', 'consu'])]",
        required=True)
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ['product', 'consu'])]",
        help="If a product variant is defined the BOM is available only for this product.")
    bom_line_ids = fields.One2many('mrp.bom.line', 'bom_id', 'BoM Lines', copy=True)
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits_compute=dp.get_precision('Unit of Measure'), required=True)
    product_uom_id = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id, oldname='product_uom', required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of bills of material.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        help="The list of operations (list of work centers) to produce the finished product. "
             "The routing is mainly used to compute work center costs during operations and to "
             "plan future loads on work centers based on production planning.")
    ready_to_produce = fields.Selection([
        ('all_available', 'All components available'),
        ('asap', 'The components of 1st operation')],
        string='Ready when are available',  # TDE FIXME: I am not able to renglish
        default='asap', required=True)
    operation_id = fields.Many2one('mrp.routing.workcenter', 'Produced at Operation')
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Picking Type',
        domain=[('code', '=', 'mrp_operation')],
        help="When a procurement has a ‘produce’ route with a picking type set, it will try to create "
             "a Manufacturing Order for that product using a BOM of the same picking type. That allows "
             "to define pull rules for products with different routing (different BOMs)")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('mrp.bom'),
        required=True)

    @api.model
    def _bom_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False):
        """ Finds BoM for particular product and product uom.
        :param product_tmpl_id: Selected product.
        :param product_uom_id: Unit of measure of a product.
        :return: False or BoM id.
        """
        today_date = fields.date.today()
        if product:
            if not product_tmpl:
                product_tmpl = product.product_tmpl_id
            domain = ['|', ('product_id', '=', product.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl.id)]
        elif product_tmpl:
            domain = [('product_tmpl_id', '=', product_tmpl.id)]
        else:
            # neither product nor template, makes no sense to search
            return False
        if picking_type:
            domain += ['|', ('picking_type_id', '=', picking_type.id), ('picking_type_id', '=', False)]
        if self.env.context.get('company_id', company_id):
            domain = domain + [('company_id', '=', self.env.context.get('company_id', company_id))]
        # order to prioritize bom with product_id over the one without
        return self.search(domain, order='sequence, product_id', limit=1)

    def _prepare_consume_line(self, bom_line, quantity, result=None):
        if result:
            result['result'].append({
                'name': bom_line.product_id.name,
                'product_id': bom_line.product_id.id,
                'product_uom_qty': quantity,  # TDE FIXME: this field does not exist
                # 'product_qty': quantity,  # TDE NOTSURE: Yes or no ? removed in QDP
                'product_uom_id': bom_line.product_uom_id.id,
                'operation_id': bom_line.operation_id.id,
            })

    # Quantity must be in same UoM than the BoM: convert uom before explode()
    def explode(self, product, quantity, original_quantity=0, method=None, method_wo=None, done=None, **kw):
        self.ensure_one()
        ProductUom = self.env['product.uom']
        if not original_quantity:
            original_quantity = quantity
        if method_wo and self.routing_id: method_wo(self, quantity)
        done = done or []
        for bom_line in self.bom_line_ids:
            if bom_line._skip_bom_line(product):
                continue
            if bom_line.product_id.product_tmpl_id.id in done:
                raise UserError(_('BoM "%s" contains a BoM line with a product recursion: "%s".') % (self.display_name, bom_line.product_id.display_name))
            # This is very slow, can we improve that?
            bom = self._bom_find(product=bom_line.product_id, picking_type=self.picking_type_id)
            if not bom or bom.type != "phantom":
                qty = quantity * bom_line.product_qty / self.product_qty
                if method: method(bom_line, qty, original_quantity=original_quantity)
            else:
                done.append(self.product_tmpl_id.id)
                # We need to convert to units/UoM of chosen BoM 
                qty2 = self.env['product.uom']._compute_qty(bom_line.product_uom_id.id, quantity * bom_line.product_qty / self.product_qty, bom.product_uom_id.id)
                bom.explode(bom_line.product_id, qty2, original_quantity=original_quantity, method=method, method_wo=method_wo, done=done, result=kw)
        return True

    @api.multi
    def copy_data(self, default=None):
        # TDE CLEANME: unnecessary
        if default is None:
            default = {}
        return super(MrpBom, self).copy_data(default)[0]

    @api.onchange('product_uom_id')
    def onchange_uom(self):
        res = {}
        if not self.product_uom_id or not self.product_tmpl_id:
            return
        if self.product_uom_id.category_id.id != self.product_tmpl_id.uom_id.category_id.id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
        return res

    @api.multi
    def unlink(self):
        if self.env['mrp.production'].search([('bom_id', 'in', self.ids), ('state', 'not in', ['done', 'cancel'])], limit=1):
            raise UserError(_('You can not delete a Bill of Material with running manufacturing orders.\nPlease close or cancel it first.'))
        return super(MrpBom, self).unlink()

    @api.onchange('product_tmpl_id', 'product_qty')
    def onchange_product_tmpl_id(self):
        # TDE CLEANME: product_qty is not a dependency
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id

    @api.multi
    def name_get(self):
        return [(bom.id, '%s%s' % (bom.code and '%s: ' % bom.code or '', bom.product_tmpl_id.display_name)) for bom in self]


class MrpBomLine(models.Model):
    _name = 'mrp.bom.line'
    _order = "sequence"
    _rec_name = "product_id"

    def _get_uom_id(self):
        return self.env['product.uom'].search([], limit=1, order='id')

    @api.one
    @api.depends('product_id', 'bom_id')
    def _compute_child_line_ids(self):
        """ If the BOM line refers to a BOM, return the ids of the child BOM lines """
        # JCO TODO: remove this and reimplement the report in a better way
        if not self.product_id:
            self.child_line_ids = False
            return
        bom = self.env['mrp.bom']._bom_find(
            product_tmpl=self.product_id.product_tmpl_id,
            product=self.product_id,
            picking_type=self.bom_id.picking_type_id)
        if bom:
            self.child_line_ids = bom.bom_line_ids.ids
        else:
            self.child_line_ids = False

    @api.multi
    def _get_child_bom_lines(self):
        pass

    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True)
    product_qty = fields.Float(
        'Product Quantity', default=1.0,
        digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        default=lambda self: self.env['mrp.bom']._get_default_product_uom_id(),
        oldname='product_uom', required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    sequence = fields.Integer(
        'Sequence', default=1,
        help="Gives the sequence order when displaying.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        related='bom_id.routing_id', store=True,
        help="The list of operations (list of work centers) to produce the finished product. The routing "
             "is mainly used to compute work center costs during operations and to plan future loads on "
             "work centers based on production planning.")
    bom_id = fields.Many2one(
        'mrp.bom', 'Parent BoM',
        index=True, ondelete='cascade', required=True)
    attribute_value_ids = fields.Many2many(
        'product.attribute.value', string='Variants',
        help="BOM Product Variants needed form apply this line.")
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Consumed in Operation',
        help="The operation where the components are consumed, or the finished products created.")
    child_line_ids = fields.One2many(
        'mrp.bom.line', string="BOM lines of the referred bom",
        compute='_compute_child_line_ids')
    has_attachments = fields.Boolean('Has Attachments', compute='_compute_has_attachments')

    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)', 'All product quantities must be greater than 0.\n'
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs !'),
    ]

    @api.one
    @api.depends('product_id')
    def _compute_has_attachments(self):
        nbr_attach = self.env['ir.attachment'].search_count([
            '|',
            '&', ('res_model', '=', 'product.product'), ('res_id', '=', self.product_id.id),
            '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.product_tmpl_id.id)])
        self.has_attachments = bool(nbr_attach) 

    def _skip_bom_line(self, product):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control. """
        # all bom_line_id variant values must be in the product
        if self.attribute_value_ids:
            if not product or self.attribute_value_ids - product.attribute_value_ids:
                return True
        return False

    @api.model
    def create(self, values):
        if 'product_id' in values and 'product_uom_id' not in values:
            values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        return super(MrpBomLine, self).create(values)

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

    @api.multi
    def show_documents(self):
        # TDE FIXME: rename me + CLEANME
        self.ensure_one()
        domain = [
             '|',
             '&', ('res_model', '=', 'product.product'), ('res_id', '=', self.product_id.id),
             '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.product_tmpl_id.id)]
        ir_model_data = self.env['ir.model.data']
        attachment_view = ir_model_data.get_object_reference('mrp', 'view_document_file_kanban_mrp')[1]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': attachment_view,
            'views': [(attachment_view, 'kanban'), (False, 'form')],
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                        Documents are attached to the tasks and issues of your project.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your project.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % ('product.product', self.product_id.id)
        }
