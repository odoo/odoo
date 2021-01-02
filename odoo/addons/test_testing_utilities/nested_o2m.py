from lxml.builder import E

from odoo import fields, models, api, Command

class Product(models.Model):
    _name = _description = 'ttu.product'

class Root(models.Model):
    _name = _description = 'ttu.root'

    product_id = fields.Many2one('ttu.product')
    product_qty = fields.Integer()
    qty_producing = fields.Integer()
    qty_produced = fields.Integer(compute='_get_produced_qty')

    move_raw_ids = fields.One2many('ttu.child', 'root_raw_id')
    move_finished_ids = fields.One2many('ttu.child', 'root_id')

    @api.depends('move_finished_ids.move_line_ids.qty_done')
    def _get_produced_qty(self):
        for r in self:
            r.qty_produced = sum(r.mapped('move_finished_ids.move_line_ids.qty_done'))
    @api.onchange('qty_producing')
    def _onchange_producing(self):
        production_move = self.move_finished_ids.filtered(
            lambda move: move.product_id == self.product_id
        )
        if not production_move:
            # Happens when opening the mo?
            return
        for line in production_move.move_line_ids:
            line.qty_done = 0
        qty_producing = self.qty_producing - self.qty_produced
        vals = production_move._set_quantity_done_prepare_vals(qty_producing)
        if vals['to_create']:
            for res in vals['to_create']:
                production_move.move_line_ids.new(res)
        if vals['to_write']:
            for move_line, res in vals['to_write']:
                move_line.update(res)

        for move in (self.move_raw_ids | self.move_finished_ids.filtered(lambda m: m.product_id != self.product_id)):
            new_qty = qty_producing * move.unit_factor
            for line in move.move_line_ids:
                line.qty_done = 0
            vals = move._set_quantity_done_prepare_vals(new_qty)
            if vals['to_create']:
                for res in vals['to_create']:
                    move.move_line_ids.new(res)
            if vals['to_write']:
                for move_line, res in vals['to_write']:
                    move_line.update(res)

    def _get_default_form_view(self):
        move_subview = E.tree(
            {'editable': 'bottom'},
            E.field(name='product_id'),
            E.field(name='unit_factor'),
            E.field(name='quantity_done'),
            E.field(
                {'name': 'move_line_ids', 'invisible': '1'},
                E.tree(
                    E.field(name='qty_done', invisible='1'),
                    E.field(name='product_id', invisible='1'),
                    E.field(name='move_id', invisible='1'),
                    E.field(name='id', invisible='1'),
                )
            )
        )

        t = E.form(
            E.field(name='product_id'),
            E.field(name='product_qty'),
            E.field(name='qty_producing'),
            E.field({'name': 'move_raw_ids', 'on_change': '1'}, move_subview),
            E.field({'name': 'move_finished_ids', 'on_change': '1'}, move_subview),
        )
        # deoptimise to ensure we call onchange most of the time, as im the real
        # case this is done as a result of the metric fuckton of computes, but
        # here the near complete lack of computes causes most of the onchange
        # triggers to get disabled
        for f in t.iter('field'):
            f.set('on_change', '1')
        return t


class Child(models.Model):
    _name = _description = 'ttu.child'

    product_id = fields.Many2one('ttu.product')
    unit_factor = fields.Integer(default=1, required=True) # should be computed but we can ignore that
    quantity_done = fields.Integer(
        compute='_quantity_done_compute',
        inverse='_quantity_done_set'
    )

    root_raw_id = fields.Many2one('ttu.root')
    root_id = fields.Many2one('ttu.root')
    move_line_ids = fields.One2many('ttu.grandchild', 'move_id')

    def _set_quantity_done_prepare_vals(self, qty):
        res = {'to_write': [], 'to_create': []}
        for ml in self.move_line_ids:
            ml_qty = ml.product_uom_qty - ml.qty_done
            if ml_qty <= 0:
                continue

            taken_qty = min(qty, ml_qty)

            res['to_write'].append((ml, {'qty_done': ml.qty_done + taken_qty}))
            qty -= taken_qty

            if qty <= 0:
                break

        if qty > 0:
            res['to_create'].append({
                'move_id': self.id,
                'product_id': self.product_id.id,
                'product_uom_qty': 0,
                'qty_done': qty,
            })
        return res

    @api.depends('move_line_ids.qty_done')
    def _quantity_done_compute(self):
        for move in self:
            move.quantity_done = sum(move.mapped('move_line_ids.qty_done'))

    def _quantity_done_set(self):
        quantity_done = self[0].quantity_done  # any call to create will invalidate `move.quantity_done`
        for move in self:
            move_lines = move.move_line_ids
            if not move_lines:
                if quantity_done:
                    # do not impact reservation here
                    move_line = self.env['ttu.grandchild'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_qty': 0,
                        'qty_done': quantity_done,
                    })
                    move.write({'move_line_ids': [Command.link(move_line.id)]})
            elif len(move_lines) == 1:
                move_lines[0].qty_done = quantity_done
            else:
                # Bypass the error if we're trying to write the same value.
                ml_quantity_done = sum(l.qty_done for l in move_lines)
                assert quantity_done == ml_quantity_done, "Cannot set the done quantity from this stock move, work directly with the move lines."


class Grandchild(models.Model):
    _name = _description = 'ttu.grandchild'

    product_id = fields.Many2one('ttu.product')
    product_uom_qty = fields.Integer()
    qty_done = fields.Integer()

    move_id = fields.Many2one('ttu.child')
