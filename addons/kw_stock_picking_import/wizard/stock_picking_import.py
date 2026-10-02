import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    import xlrd
except (ImportError, IOError) as err:
    _logger.debug(err)


class ImportWizardLine(models.TransientModel):
    _name = 'kw.stock.picking.import.wizard.line'
    _description = 'Import wizard line'

    wizard_id = fields.Many2one(
        comodel_name='kw.stock.picking.import.wizard', )
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product', )
    quantity = fields.Float(
        digits='Product Unit of Measure', )


class ImportWizard(models.TransientModel):
    _name = 'kw.stock.picking.import.wizard'
    _description = 'Import wizard'

    stock_picking_id = fields.Many2one(
        comodel_name='stock.picking', )
    line_ids = fields.One2many(
        comodel_name='kw.stock.picking.import.wizard.line',
        inverse_name='wizard_id', )
    is_product_creation_needed = fields.Boolean(
        string='Create product', )
    upload_file = fields.Binary(attachment=True, )

    @api.model
    def default_get(self, fields_list):
        res = super(ImportWizard, self).default_get(fields_list)
        res['stock_picking_id'] = self.env.context.get('active_id')
        return res

    # pylint: disable=too-many-branches
    def parse_file(self):
        self.ensure_one()
        if not self.upload_file:
            raise ValidationError(_('You need upload file to parse'))
        book = xlrd.open_workbook(
            file_contents=base64.b64decode(self.upload_file))
        lines = [(5,)]
        company_id = self.env.user.company_id.id
        _logger.info(book.sheet_by_index(0).nrows)
        for i in range(1, book.sheet_by_index(0).nrows):
            record = []
            for x in book.sheet_by_index(0).row(i):
                if isinstance(x.value, str):
                    record.append(x.value.strip())
                elif isinstance(x.value, float):
                    try:
                        if x.value == float(int(x.value)):
                            x.value = int(x.value)
                    except Exception as e:
                        _logger.debug(e)
                    record.append(x.value)
                else:
                    record.append(x.value)
            if len(record) < 4:
                raise ValidationError(_(
                    'Line %s has no enough columns') % str(i + 1))
            if not all([record[2], record[3]]):
                raise ValidationError(_(
                    'Line %s has no name or qty') % str(i + 1))
            p = False
            if any([record[0], record[1]]):
                domain = [('company_id', '=', company_id), ]
                if all([record[0], record[1]]):
                    domain += ['|', ('default_code', '=', record[1]),
                               ('barcode', '=', record[0])]
                elif record[0]:
                    domain.append(('barcode', '=', record[0]))
                elif record[1]:
                    domain.append(('default_code', '=', record[1]))
                p = self.env['product.product'].search(domain, limit=1)
            if not p:
                p = self.env['product.product'].search([
                    ('company_id', '=', company_id),
                    ('name', '=', record[2])], limit=1)
            if not p:
                if not self.is_product_creation_needed:
                    raise ValidationError(_(
                        'Product "%s" was not found in DB'
                    ) % record[1])
                vals = {
                    'company_id': company_id, 'default_code': record[1],
                    'type': 'product', 'name': record[2], }
                if record[0]:
                    vals['barcode'] = record[0]
                p = self.env['product.product'].create(vals)
            lines.append([0, 0, {'product_id': p.id,
                                 'quantity': float(record[3])}])
        _logger.info(lines)
        self.line_ids = lines
        # return {'type': 'ir.actions.do_nothing', }

        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kw.stock.picking.import.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def load_lines(self):
        self.ensure_one()
        move_lines = []
        for x in self.line_ids:
            move = self.env['stock.move'].create({
                'name': x.product_id.name,
                'product_id': x.product_id.id,
                'product_uom_qty': x.quantity,
                'product_uom': x.product_id.uom_id.id,
                'location_id': self.stock_picking_id.location_id.id,
                'location_dest_id': self.stock_picking_id.location_dest_id.id,
            })
            move_lines.append(move.id)
        self.stock_picking_id.move_ids = [(6, 0, move_lines)]
