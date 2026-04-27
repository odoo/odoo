# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.addons.l10n_ke_edi_oscu.models.account_move import format_etims_datetime, parse_etims_datetime


class L10nKeEdiCustomsImport(models.Model):
    _name = 'l10n_ke_edi.customs.import'
    _description = "Kenya Customs Import"
    _inherit = ['mail.thread']

    _check_company_auto = True

    _rec_name = 'task_code'
    _rec_names_search = ['task_code', 'item_seq']

    task_code = fields.Char("Task Code", readonly=True, required=True)
    item_seq = fields.Integer("Item Sequence", readonly=True, required=True)
    item_name = fields.Char("Item Name", readonly=True)
    declaration_date = fields.Date("Declaration Date", readonly=True)
    declaration_number = fields.Char("Declaration Number", readonly=True)
    origin_country_id = fields.Many2one('res.country', string="Origin Country", readonly=True)
    export_country_id = fields.Many2one('res.country', string="Export Country", readonly=True)
    hs_code = fields.Char('HS Code', readonly=True)

    number_packages = fields.Integer("Number of Packages", readonly=True)
    package_unit_code_id = fields.Many2one('l10n_ke_edi_oscu.code', domain="[('code_type', '=', '17')]", readonly=True)
    quantity = fields.Float("Quantity", readonly=True)
    uom_code_id = fields.Many2one('l10n_ke_edi_oscu.code', domain="[('code_type', '=', '10')]", readonly=True)
    uom_id = fields.Many2one('uom.uom', string="UoM", compute='_compute_uom_id')

    supplier_name = fields.Char("Vendor", readonly=True)

    product_id = fields.Many2one('product.product', tracking=True, check_company=True)
    company_id = fields.Many2one('res.company', readonly=True)
    remark = fields.Text("Remark", readonly=True)

    state = fields.Selection([('2', "Waiting"), ('3', "Approved"), ('4', "Rejected")], tracking=True)
    warning_msg = fields.Json(compute='_compute_warning_msg')

    purchase_id = fields.Many2one('purchase.order', "Purchase Order", tracking=True, check_company=True)
    partner_id = fields.Many2one('res.partner', "Partner", tracking=True, check_company=True)

    # === Computes === #

    @api.depends('uom_code_id')
    def _compute_uom_id(self):
        for customs_imp in self:
            if customs_imp.uom_code_id:
                customs_imp.uom_id = self.env['uom.uom'].search([('l10n_ke_quantity_unit_id.code', '=', customs_imp.uom_code_id.code)], limit=1)
            else:
                customs_imp.uom_id = False

    @api.depends('product_id')
    def _compute_warning_msg(self):
        product_items = self.filtered(lambda i: i.product_id)
        (self - product_items).warning_msg = ""
        for item in product_items:
            item.warning_msg = item.product_id._l10n_ke_get_validation_messages(for_invoice=True)
            if item.warning_msg:
                continue

            warnings = {}
            if item.package_unit_code_id != item.product_id.l10n_ke_packaging_unit_id:
                warnings['packaging_code_mismatch'] = {'message': _("Packaging unit code does not match")}
            if item.origin_country_id != item.product_id.l10n_ke_origin_country_id:
                warnings['origin_country_mismatch'] = {'message': _("Origin Country is not the same as on the product")}
            if item.uom_id and item.uom_id.category_id != item.product_id.uom_id.category_id:
                warnings['uom_mismatch'] = {'message': _("UoMs do not match")}

            if warnings:
                item.warning_msg = warnings
            else:
                item.warning_msg = False

    @api.ondelete(at_uninstall=False)
    def _unlink_only_if_unsent(self):
        if self.filtered(lambda i: i.state):
            raise UserError(_('You cannot delete a customs import after approving or rejecting it with eTIMS!'))

    # === Sending to eTIMS: customs import approval/rejection === #

    def button_approve(self):
        self.ensure_one()
        if not self.purchase_id or not self.purchase_id._l10n_ke_check_import(self):
            raise UserError(_('You can not approve the customs import before receiving the items.'))
        self._revise_item(status='3')
        # Trigger cron
        self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves')._trigger()

    def button_reject(self):
        self._revise_item(status='4')

    def _revise_item(self, status='2'):
        if not self.product_id:
            raise UserError(_("Please match with a product first. "))
        if (blocking := [msg for msg in (self.warning_msg or {}).values() if msg.get('blocking')]):
            raise UserError(
                _("Please resolve these issues first.\n %s", '\n'.join([f"- {msg['message']}" for msg in blocking])))
        if not self.product_id.l10n_ke_item_code:  # Register the product if not already
            self.product_id.action_l10n_ke_oscu_save_item()
        content = {
            'taskCd': (self.task_code or '')[:50],
            'dclDe': self.declaration_date.strftime('%d%m%Y'),
            'itemSeq': self.item_seq,
            'hsCd': self.hs_code.ljust(10, '0'),
            'itemClsCd': self.product_id.unspsc_code_id.code,
            'itemCd': self.product_id.l10n_ke_item_code,
            'imptItemSttsCd': status,
            'remark': (self.remark or '')[:400],
            'modrNm': self.env.user.name,
            'modrId': self.env.user.id,
        }
        error, _data, _date = self.company_id._l10n_ke_call_etims('updateImportItem', content)
        if error:
            raise UserError(f"[{error['code']}] {error['message']}")
        else:
            self.state = status

    # === Fetching from eTIMS === #

    def _cron_l10n_ke_fetch_customs_import(self):
        companies = self.env['res.company'].search([('l10n_ke_oscu_is_active', '=', True)])
        for company in companies:
            self._receive_customs_import(company)

    def _receive_customs_import(self, company):
        """ Fetch customs imports from eTIMS """
        content = {
            'lastReqDt': format_etims_datetime(
                company.l10n_ke_oscu_last_fetch_customs_import_date
                or datetime(2018, 1, 1)
            )
        }
        error, data, date = company._l10n_ke_call_etims('selectImportItemList', content)
        if error:
            return

        self._process_receival_dict(company, data)
        company.l10n_ke_oscu_last_fetch_customs_import_date = parse_etims_datetime(date)

    def _process_receival_dict(self, company, data):
        for item in data['itemList']:
            task_code = item['taskCd']
            item_seq = item['itemSeq']
            custom_item = self.search([('task_code', '=', task_code),
                                       ('item_seq', '=', item_seq),
                                       ('company_id', '=', company.id)], limit=1)
            if not custom_item:
                item_rec = self.create({
                    'task_code': task_code,
                    'item_seq': item_seq,
                    'company_id': company.id,
                    'declaration_date': datetime.strptime(item['dclDe'], '%d%m%Y'),
                    'declaration_number': item['dclNo'],
                    'hs_code': item['hsCd'],
                    'item_name': item['itemNm'].split('; ')[1] if ';' in item['itemNm'] else item['itemNm'],
                    'origin_country_id': self.env['res.country'].search([('code', '=', item['orgnNatCd'])], limit=1).id,
                    'export_country_id': self.env['res.country'].search([('code', '=', item['exptNatCd'])], limit=1).id,
                    'number_packages': item['pkg'],
                    'package_unit_code_id': self.env['l10n_ke_edi_oscu.code'].search([('code_type', '=', '17'),
                                                                                      ('code', '=', item['pkgUnitCd'])], limit=1).id,
                    'quantity': item['qty'],
                    'uom_code_id': self.env['l10n_ke_edi_oscu.code'].search([('code_type', '=', '10'),
                                                                             ('code', '=', item['qtyUnitCd'])], limit=1).id,
                    'supplier_name': item['spplrNm'],
                    'state': item.get('imptItemsttsCd'),
                    'remark': item.get('remark'),
                })
                self.env['ir.attachment'].create({
                    'name': item_rec.declaration_number + '-' + item_rec.task_code + '-' + str(item_rec.item_seq) + '.json',
                    'res_model': 'l10n_ke_edi.customs.import',
                    'res_id': item_rec.id,
                    'raw': json.dumps(item, indent=4),
                })
                # Try to match with product
                matched_item = self.search([
                    ('product_id', '!=', False),
                    ('hs_code', '=', item['hsCd']),
                    ('item_name', '=', item['itemNm']),
                    ('origin_country_id.code', '=', item['orgnNatCd']),
                    ('package_unit_code_id.code', '=', item['pkgUnitCd']),
                    ('uom_code_id.code', '=', item['qtyUnitCd'])
                ], limit=1)
                if matched_item:
                    item_rec.product_id = matched_item.product_id.id
                else:
                    # Search for a product with the same name, ...
                    matched_product = self.env['product.product'].search([
                        ('name', '=', item['itemNm']),
                        ('l10n_ke_origin_country_id.code', '=', item['orgnNatCd']),
                        ('l10n_ke_packaging_unit_id.code', '=', item['pkgUnitCd']),
                        ('uom_id.l10n_ke_quantity_unit_id.code', '=', item['qtyUnitCd'])
                    ])
                    if matched_product:
                        item_rec.product_id = matched_product.id

    # === Actions === #

    def action_create_purchase_order(self):
        vals = []
        custimps = self.filtered(lambda c: not c.purchase_id)
        partners = custimps.mapped('partner_id')
        if len(partners) != 1:
            raise UserError(_("You can only create a Purchase Order for multiple Customs Imports if they share the same partner."))
        for custimp in custimps:
            if not custimp.partner_id:
                raise UserError(_('Please make sure to put a partner.'))
            if not custimp.product_id:
                raise UserError(_("Please make sure to put a matching product."))
            vals.append(Command.create({
                'name': custimp.item_name,
                'product_id': custimp.product_id.id,
                'product_qty': custimp.quantity,
                'product_uom': custimp.uom_id.id or self.env.ref('uom.product_uom_unit').id,
            }))
        po1 = self.env['purchase.order'].create({
            'partner_id': partners[0].id,
            'order_line': vals,
            'company_id': custimp.company_id.id,
        })
        custimps.write({'purchase_id': po1.id})
        action = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': po1.id,
        }
        return action

    def action_view_purchase_order(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')
        result.update({
            'views': [(self.env.ref('purchase.purchase_order_form', False).id, 'form')],
            'res_id': self.purchase_id.id,
        })
        return result
