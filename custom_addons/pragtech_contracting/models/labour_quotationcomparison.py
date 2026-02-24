# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import UserError, UserError


class LabourContractorInfo(models.Model):
    _name = 'labour.contractorinfo'
    _description = 'Labour Contractor Info'

    name = fields.Many2one('res.partner', 'Contractor', required=True, domain=[('contractor', '=', True)], ondelete='cascade', help="contractor of this product")
    product_name = fields.Char('Contractor Product Name')
    date = fields.Datetime('Date', default=datetime.now())
    delay = fields.Integer('Delivery Lead Time')

    min_qty = fields.Float('Minimal Quantity', required=True,
                           help="The minimal quantity to purchase from this Contractor, expressed in the Contractor  Unit of Measure if not any, in the default unit of measure otherwise.")
    price = fields.Float('Price', required=True, )
    is_active = fields.Boolean('Active')
    unit = fields.Many2one('uom.uom', 'UOM')
    labour_id = fields.Many2one('labour.master', 'Labour')
    labour_category = fields.Many2one('labour.category', related='labour_id.category_id', store=True, string='Labour Category')


class LabourQuotationComparison(models.Model):
    _name = 'labour.quotation.comparison'
    _rec_name = 'project_id'
    _description = 'labour Quotation Comparison'

    project_id = fields.Many2one('project.project', 'Project', required=True)
    sub_project = fields.Many2one('sub.project', 'Sub Project', required=True)
    project_wbs_id = fields.Many2one('project.task', 'Project WBS Name', required=True, domain=[('is_wbs', '=', True), ('project_id', '!=', False)])
    sequence_name = fields.Char('Comparison Reference', required=True, index=True, copy=False, default='New')
    from_date = fields.Datetime('From Date', default=str(fields.date.today() - timedelta(days=15)).split(' ')[0])
    to_date = fields.Datetime('To Date', default=str(fields.date.today() + timedelta(days=1)).split(' ')[0])
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Comparison Confirm')],
                             string='Status', copy=False, index=True, track_visibility='onchange', default='draft')
    labour_line = fields.One2many('labour.list', 'quotation_comp_lab_id', string='Labour Lines', copy=True)
    contractor_line = fields.One2many('contractor.list', 'quotation_comp_contractor_id', string='Contractor Lines', copy=True)
    labour_quotation_details = fields.One2many('labour.quotation.details', 'labour_quotation_comp_detail_id', string='Labour Quotation Lines', copy=True)
    labour_quotation_comp_particular = fields.One2many('labour.quotation.compare.particular', 'labour_quotation_comp_pert_id', string='Labour Quotation Details Line', copy=True)
    quotation_comp_contractor1 = fields.One2many('quotation.compare.contractor1', 'quotation_comp_cont1_id', string='Labour Quotation Details Vendor1', copy=True)
    quotation_comp_contractor2 = fields.One2many('quotation.compare.contractor2', 'quotation_comp_cont2_id', string='Labour Quotation Details Vendor2', copy=True)
    quotation_comp_contractor3 = fields.One2many('quotation.compare.contractor3', 'quotation_comp_cont3_id', string='Labour Quotation Details Vendor3', copy=True)
    quotation_comp_contractor4 = fields.One2many('quotation.compare.contractor4', 'quotation_comp_cont4_id', string='Labour Quotation Details Vendor4', copy=True)
    quotation_comp_contractor5 = fields.One2many('quotation.compare.contractor5', 'quotation_comp_cont5_id', string='Labour Quotation Details Vendor5', copy=True)
    quotation_comp_contractor6 = fields.One2many('quotation.compare.contractor6', 'quotation_comp_cont6_id', string='Labour Quotation Details Vendor6', copy=True)
    labour_quotation_comp_tax_particular = fields.One2many('labour.tax.particular', 'labour_quotation_comp_taxper_id', string='Quotation Tax Particular Details', copy=True)
    labour_quotation_comp_tax_details1 = fields.One2many('tax.details.contractor1', 'labour_quotation_comp_tax1_id', string='Quotation Tax1 Details', copy=True)
    labour_quotation_comp_tax_details2 = fields.One2many('tax.details.contractor2', 'labour_quotation_comp_tax2_id', string='Quotation Tax1 Details', copy=True)
    labour_quotation_comp_tax_details3 = fields.One2many('tax.details.contractor3', 'labour_quotation_comp_tax3_id', string='Quotation Tax1 Details', copy=True)
    labour_quotation_comp_tax_details4 = fields.One2many('tax.details.contractor4', 'labour_quotation_comp_tax4_id', string='Quotation Tax1 Details', copy=True)
    labour_quotation_comp_tax_details5 = fields.One2many('tax.details.contractor5', 'labour_quotation_comp_tax5_id', string='Quotation Tax1 Details', copy=True)
    labour_quotation_comp_tax_details6 = fields.One2many('tax.details.contractor6', 'labour_quotation_comp_tax6_id', string='Quotation Tax1 Details', copy=True)
    total_amount = fields.Float(string='Total Amount', store=True, compute='compute_total_amount')

    total_contractor1 = fields.Float("Total", store=True, compute='_amount_particular_all')
    total_contractor2 = fields.Float("Total", store=True, compute='_amount_particular_all')
    total_contractor3 = fields.Float("Total", store=True, compute='_amount_particular_all')
    total_contractor4 = fields.Float("Total", store=True, compute='_amount_particular_all')
    total_contractor5 = fields.Float("Total", store=True, compute='_amount_particular_all')
    total_contractor6 = fields.Float("Total", store=True, compute='_amount_particular_all')

    contractor1 = fields.Many2one('res.partner', 'Conractor1', domain=[('contractor', '=', True)])
    contractor2 = fields.Many2one('res.partner', 'Conractor2', domain=[('contractor', '=', True)])
    contractor3 = fields.Many2one('res.partner', 'Conractor3', domain=[('contractor', '=', True)])
    contractor4 = fields.Many2one('res.partner', 'Conractor4', domain=[('contractor', '=', True)])
    contractor5 = fields.Many2one('res.partner', 'Conractor5', domain=[('contractor', '=', True)])
    contractor6 = fields.Many2one('res.partner', 'Conractor6', domain=[('contractor', '=', True)])
    description = fields.Char('')
    description1 = fields.Char('')
    description2 = fields.Char('')
    description3 = fields.Char('')
    description4 = fields.Char('')

    def unlink(self):
        ids = []
        for line in self:
            ids.append(line.state)
            if 'confirm' in ids:
                raise UserError(_('You cannot delete Confirmed Quotation.'))

    def confirm_action(self):
        obj = self.browse(self.id)
        obj.sequence_name = self.env['ir.sequence'].next_by_code('labour.quotation.comparison')
        no_of_approve = []
        no_of_products = [particular.labour_id for particular in self.labour_quotation_comp_particular if particular.is_approve]
        uom = [particular.labour_uom for particular in self.labour_quotation_comp_particular if particular.is_approve]

        for contractor1 in self.quotation_comp_contractor1:
            if contractor1.is_approve == True:
                no_of_approve.append(contractor1.is_approve)
                vals = {
                    'name': contractor1.contractor_id.id,
                    'price': contractor1.negotiated_rate,
                    'min_qty': 1,
                    'labour_id': contractor1.labour_id.id,
                    'unit': contractor1.labour_id.unit_no.id,
                    'date': datetime.now(),
                    'is_active': True,
                }
                labour = self.env['labour.master'].browse(contractor1.labour_id.id)
                for line in labour.contractor_ids:
                    if line.name.id == contractor1.contractor_id.id and line.is_active == True:
                        line.write({'price': contractor1.negotiated_rate})

                    line.is_active = False

                labour.contractor_ids.create(vals)

        for contractor2 in self.quotation_comp_contractor2:
            if contractor2.is_approve == True:
                no_of_approve.append(contractor2.is_approve)
                contractor_price_info_obj = self.env['labour.contractorinfo'].search([('name', '=', contractor2.labour_id.name)])
                vals = {
                    'name': contractor2.contractor_id.id,
                    'price': contractor2.negotiated_rate,
                    'min_qty': 1,
                    'labour_id': contractor2.labour_id.id,
                    'unit': contractor2.labour_id.unit_no.id,
                    'date': datetime.now(),
                    'is_active': True,
                }
                labour = self.env['labour.master'].browse(contractor2.labour_id.id)

                for line in labour.contractor_ids:
                    if line.name.id == contractor2.contractor_id.id and line.is_active == True:
                        line.write({'price': contractor2.negotiated_rate})

                    line.is_active = False

                labour.contractor_ids.create(vals)

        for contractor3 in self.quotation_comp_contractor3:
            if contractor3.is_approve == True:
                no_of_approve.append(contractor3.is_approve)
                vals = {
                    'name': contractor3.contractor_id.id,
                    'price': contractor3.negotiated_rate,
                    'min_qty': 1,
                    'labour_id': contractor3.labour_id.id,
                    'unit': contractor3.labour_id.unit_no.id,
                    'date': datetime.now(),
                    'is_active': True,
                }

                # Deactivating previously approved vendor
                labour = self.env['labour.master'].browse(contractor3.labour_id.id)

                for line in labour.contractor_ids:
                    if line.name.id == contractor3.contractor_id.id and line.is_active == True:
                        line.write({'price': contractor3.negotiated_rate})

                    line.is_active = False

                labour.contractor_ids.create(vals)

        for contractor4 in self.quotation_comp_contractor4:
            if contractor4.is_approve == True:
                no_of_approve.append(contractor4.is_approve)
                contractor_price_info_obj = self.env['labour.contractorinfo'].search([('name', '=', contractor4.labour_id.name)])
                vals = {
                    'name': contractor4.contractor_id.id,
                    'price': contractor4.negotiated_rate,
                    'min_qty': 1,
                    'labour_id': contractor4.labour_id.id,
                    'unit': contractor4.labour_id.unit_no.id,
                    'date': datetime.now(),
                    'is_active': True,
                }
                labour = self.env['labour.master'].browse(contractor4.labour_id.id)
                for line in labour.contractor_ids:
                    if line.name.id == contractor4.contractor_id.id and line.is_active == True:
                        line.write({'price': contractor4.negotiated_rate})

                    line.is_active = False

                labour.contractor_ids.create(vals)

        for contractor5 in self.quotation_comp_contractor5:
            if contractor5.is_approve == True:
                no_of_approve.append(contractor5.is_approve)
                contractor_price_info_obj = self.env['labour.contractorinfo'].search([('name', '=', contractor5.labour_id.name)])
                vals = {
                    'name': contractor5.contractor_id.id,
                    'price': contractor5.negotiated_rate,
                    'min_qty': 1,
                    'labour_id': contractor5.labour_id.id,
                    'unit': contractor5.labour_id.unit_no.id,
                    'date': datetime.now(),
                    'is_active': True,
                }
                for line in labour.contractor_ids:
                    if line.name.id == contractor4.contractor_id.id and line.is_active == True:
                        line.write({'price': contractor4.negotiated_rate})

                    line.is_active = False

                labour.contractor_ids.create(vals)

        for contractor6 in self.quotation_comp_contractor6:
            if contractor6.is_approve == True:
                no_of_approve.append(contractor6.is_approve)
                contractor_price_info_obj = self.env['labour.contractorinfo'].search([('name', '=', contractor6.labour_id.name)])
                vals = {
                    'name': contractor6.contractor_id.id,
                    'price': contractor6.negotiated_rate,
                    'min_qty': 1,
                    'labour_id': contractor6.labour_id.id,
                    'unit': contractor6.labour_id.unit_no.id,
                    'date': datetime.now(),
                    'is_active': True,
                }
                contractor_price_info_obj = self.env['labour.contractorinfo'].search([('labour_id', '=', contractor6.labour_id.id), ('is_active', '=', True)])
                for i in contractor_price_info_obj:
                    if i.name.id == contractor6.contractor_id.id:
                        i.write({'is_active': False})

                contractor_price_info_obj.create(vals)

        if len(no_of_approve) != len(no_of_products) or len(no_of_products) == 0:
            raise UserError(_("Kindly check appropriate vendors for approval."))

        self.state = 'confirm'

    @api.onchange('project_wbs_id', 'from_date', 'to_date')
    def onchange_project_wbs1(self):
        # Set labour list
        labour_ids = list(set([labour.labour_id.id for labour in self.project_wbs_id.labour_estimate_line]))
        labour_lines = []
        for labour_id in labour_ids:
            labour_lines.append((0, 0, {'labour_id': labour_id, 'quotation_comp_lab_id': self.id}))

        # Set contractor list
        labour_quotation_lines = self.env['labour.quotation.line'].search([('labour_id', 'in', labour_ids), ('order_id.date_order', '>=', self.from_date), ('order_id.date_order', '<=', self.to_date)])
        contractor_ids = list(set([line.order_id.partner_id.id for line in labour_quotation_lines]))
        contractor_lines = []
        for contractor_id in contractor_ids:
            # Replaced the key name: quotation_comp_cont_id
            contractor_lines.append((0, 0, {'contractor_id': contractor_id, 'quotation_comp_contractor_id': self.id}))
            self.update({
                'labour_line': labour_lines,
                'contractor_line': contractor_lines,
            })

    @api.depends('labour_quotation_details.price_subtotal')
    def compute_total_amount(self):
        for order in self:
            total_amount = 0.0
            for line in order.labour_quotation_details:
                total_amount += line.price_subtotal

            order.update({'total_amount': total_amount, })

    def compute_labour_quotation_details(self):
        # Set quotation line based on selected material, vendor, date range and
        # old quotation
        counter = 0
        for labour_lines in self.labour_line:
            if labour_lines.is_labour:
                counter += 1

        if counter > 2:
            raise UserError(_("You can select maximum two labours."))

        quotation_details_lines = []
        common_line_ids = []
        labour_ids = [line.labour_id.id for line in self.labour_line if line.is_labour]
        old_quotation_lines = [line.id for line in self.labour_quotation_details]

        selected_contractor_ids = [line.contractor_id.id for line in self.contractor_line if line.is_contractor]
        if len(selected_contractor_ids) > 6:
            raise UserError(_("You can select maximum 6 contractors."))

        quotation_ids = self.env['labour.quotation'].search([('date_order', '>=', self.from_date), ('date_order', '<=', self.to_date),
                                                             ('partner_id', 'in', selected_contractor_ids), ('state', 'in', ['confirm'])])

        for quotation in quotation_ids:
            for quotation_line in quotation.order_line:
                if quotation_line.labour_id.id in labour_ids:
                    old_line_flag = False
                    old_line = None
                    for line in self.labour_quotation_details:
                        if line.contractor_id.id == quotation_line.partner_id.id and line.name == quotation.name and line.labour_id.id == quotation_line.labour_id.id:
                            old_line_flag = True
                            old_line = line
                            break

                    if not old_line_flag:  # Add New Line
                        vals = {
                            'name': quotation.name,
                            'date': quotation.date_order,
                            'contractor_id': quotation.partner_id.id,
                            'labour_id': quotation_line.labour_id.id,
                            'tax_id': quotation_line.taxes_id,
                            'tax': quotation_line.price_tax,
                            'labour_qty': quotation_line.labour_qty,
                            'labour_uom': quotation_line.labour_uom.id,
                            'price_unit': quotation_line.price_unit,
                            'negotiated_rate': quotation_line.negotiated_rate,
                            'price_subtotal': quotation_line.price_subtotal,
                        }
                        quotation_details_lines.append((0, 0, vals))
                    else:
                        # Keep old line as it is
                        quotation_details_lines.append((4, old_line.id, False))
                        common_line_ids.append(old_line.id)

        # Remove unused old lines
        for quot_id in old_quotation_lines:
            if quot_id not in common_line_ids:
                quotation_details_lines.append((2, quot_id, False))

        val = {
            'labour_quotation_details': quotation_details_lines,
        }

        # Set selected vendor for comparison header
        for idx, contractor_id in enumerate(selected_contractor_ids, 1):
            contractor = 'contractor' + str(idx)
            val.update({contractor: contractor_id, })

        # If selected vendor is less than set other header to None
        if len(selected_contractor_ids) < 6:
            for idx in range(len(selected_contractor_ids) + 1, 7):
                contractor = 'contractor' + str(idx)
                val.update({contractor: None, })

        self.update(val)

    def compute_quotation_details_dictionary(self):
        # Return computed Dictionary for quotation comparison
        result = {}
        if self.labour_quotation_details:
            for line in self.labour_quotation_details:
                if line.is_use:
                    lab_id = line.labour_id.id
                    cont_id = line.contractor_id.id
                    if result.get(lab_id):
                        # Update existing Rec
                        if not result[lab_id].get(cont_id):
                            result[lab_id].update({cont_id: line})
                        else:
                            continue
                            # fix it if same partner have multiple quotation
                    else:  # Add New rec
                        result.update({lab_id: {cont_id: line}})

        return result

    def compute_selected_quotations(self):
        selected_quotation = []
        if self.labour_quotation_details:
            avg = 0
            particular_lines_list = []
            tax_list = []
            lst = []
            selected_contractor_ids = [line.contractor_id.id for line in self.contractor_line if line.is_contractor]
            lab_list = []

            #################  validation  ####################
            for line in self.labour_quotation_details:
                cost = 0
                if line.is_use:
                    lab_list.append(line.labour_id.id)
                    selected_quotation.append(line.is_use)
                    if 1 < len(set(lab_list)) < 0:
                        raise UserError(_("Please check selected labour."))

                    ############# avg ################
                    labour_lines = self.env['task.labour.line'].search([('labour_id', '=', line.labour_id.id), ('wbs_id', '=', self.project_wbs_id.id)])
                    for labour in labour_lines:
                        cost += labour.labour_rate
                        lst.append(labour.id)

                    avg = cost / len(lst)

                    ################### tax Particular 1  #################
                    if not self.env['labour.tax.particular'].search([('labour_id', '=', line.labour_id.id), ('labour_quotation_comp_taxper_id', '=', self.id)]):
                        labour_tax_detail_data = {
                            'labour_id': line.labour_id.id,
                            'is_approve': 0,
                        }

                        tax_list.append((0, 0, labour_tax_detail_data))

                    self.update({'labour_quotation_comp_tax_particular': tax_list})

        self.labour_quotation_comp_particular.unlink()
        for line in self.labour_line:
            if line.is_labour:
                particular_lines_list = []
                vals = {
                    'labour_id': line.labour_id.id,
                    'labour_uom': line.labour_id.unit_no.id,
                    'price_expt': avg,
                    'labour_quotation_comp_pert_id': self.id
                }
                particular_lines_list.append((0, 0, vals))
                particulat_prod_list = [i.labour_id.id for i in self.labour_quotation_comp_particular]

                if line.labour_id.id not in particulat_prod_list:
                    self.update({
                        'labour_quotation_comp_particular': particular_lines_list
                    })

        if len(selected_quotation) == 0:
            self.labour_quotation_comp_particular.unlink()
            self.quotation_comp_contractor1.unlink()
            self.quotation_comp_contractor2.unlink()
            self.quotation_comp_contractor3.unlink()
            self.quotation_comp_contractor4.unlink()
            self.quotation_comp_contractor5.unlink()
            self.quotation_comp_contractor6.unlink()

        ################### contractor 1  #################
        try:
            quotation_compare_contractor1_list = []
            vals = {}
            old_lines = [line.labour_id.id for line in self.quotation_comp_contractor1]
            quotation_details_dict = self.compute_quotation_details_dictionary()

            for k_parent, v_parent in quotation_details_dict.items():
                for k, v in v_parent.items():
                    if k == selected_contractor_ids[0]:
                        tax_ids = []
                        for tax_line in v.tax_id:
                            tax_ids.append(tax_line.id)

                        vals = {
                            'labour_id': v.labour_id.id,
                            'contractor_id': v.contractor_id.id,
                            'amount': v.price_unit,
                            'negotiated_rate': v.price_unit,
                            'quotation_comp_cont1_id': self.id,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                    elif k != selected_contractor_ids[0]:
                        None
                    else:
                        blank_line1 = self.env['quotation.compare.contractor1'].search([('labour_id', '=', line.labour_id.id), ('contractor_id', '=', None), ('quotation_comp_cont1_id', '=', self.id)])
                        if not blank_line1:
                            vals = {
                                'labour_id': line.labour_id.id,
                                'vendor_id': None,
                                'amount': None,
                                'negotiated_rate': None,
                                'quotation_comp_cont1_id': self.id,
                                'tax_id': None,
                            }

                # if vals not in quotation_compare_vendor1_list:
                quotation_compare_contractor1_list.append((0, 0, vals))
                for quotation_comp_contractor1 in self.quotation_comp_contractor1:
                    if quotation_comp_contractor1.id not in quotation_compare_contractor1_list:
                        quotation_compare_contractor1_list.append((2, quotation_comp_contractor1.id))

                self.update({
                    'quotation_comp_contractor1': quotation_compare_contractor1_list
                })

            ################### contractor 2 #################
            quotation_compare_contractor2_list = []
            vals = {}
            quotation_details_dict = self.compute_quotation_details_dictionary()
            for k_parent, v_parent in quotation_details_dict.items():
                for k, v in v_parent.items():
                    if k == selected_contractor_ids[1]:
                        tax_ids = []
                        for tax_line in v.tax_id:
                            tax_ids.append(tax_line.id)

                        vals = {
                            'labour_id': v.labour_id.id,
                            'contractor_id': v.contractor_id.id,
                            'amount': v.price_unit,
                            'negotiated_rate': v.price_unit,
                            'quotation_comp_cont2_id': self.id,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                    elif k != selected_contractor_ids[1]:
                        pass
                    else:
                        blank_line2 = self.env['quotation.compare.contractor2'].search([('labour_id', '=', line.labour_id.id), ('contractor_id', '=', None), ('quotation_comp_cont2_id', '=', self.id)])
                        if not blank_line2:
                            vals = {
                                'labour_id': line.labour_id.id,
                                'contractor_id': None,
                                'amount': None,
                                'negotiated_rate': None,
                                'quotation_comp_cont2_id': self.id,
                                'tax_id': None,
                            }

                quotation_compare_contractor2_list.append((0, 0, vals))
                for quotation_comp_contractor2 in self.quotation_comp_contractor2:
                    if quotation_comp_contractor2.id not in quotation_compare_contractor2_list:
                        quotation_compare_contractor2_list.append((2, quotation_comp_contractor2.id))

                self.update({
                    'quotation_comp_contractor2': quotation_compare_contractor2_list
                })

            ################### contractor 3 #################
            quotation_compare_contractor3_list = []
            vals = {}
            quotation_details_dict = self.compute_quotation_details_dictionary()
            for k_parent, v_parent in quotation_details_dict.items():
                for k, v in v_parent.items():
                    if k == selected_contractor_ids[2]:
                        tax_ids = []
                        for tax_line in v.tax_id:
                            tax_ids.append(tax_line.id)

                        vals = {
                            'labour_id': v.labour_id.id,
                            'contractor_id': v.contractor_id.id,
                            'amount': v.price_unit,
                            'negotiated_rate': v.price_unit,
                            'quotation_comp_cont3_id': self.id,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                    elif k != selected_contractor_ids[2]:
                        pass
                    else:
                        blank_line3 = self.env['quotation.compare.contractor3'].search([('labour_id', '=', line.labour_id.id), ('contractor_id', '=', None), ('quotation_comp_cont3_id', '=', self.id)])
                        if not blank_line3:
                            vals = {
                                'labour_id': line.labour_id.id,
                                'contractor_id': None,
                                'amount': None,
                                'negotiated_rate': None,
                                'quotation_comp_cont3_id': self.id,
                                'tax_id': None,
                            }

                quotation_compare_contractor3_list.append((0, 0, vals))
                for quotation_comp_contractor3 in self.quotation_comp_contractor3:
                    if quotation_comp_contractor3.id not in quotation_compare_contractor3_list:
                        quotation_compare_contractor3_list.append((2, quotation_comp_contractor3.id))

                self.update({
                    'quotation_comp_contractor3': quotation_compare_contractor3_list
                })

            ################### contractor 4 #################
            quotation_compare_contractor4_list = []
            vals = {}
            quotation_details_dict = self.compute_quotation_details_dictionary()
            for k_parent, v_parent in quotation_details_dict.items():
                for k, v in v_parent.items():
                    if k == selected_contractor_ids[3]:
                        tax_ids = []
                        for tax_line in v.tax_id:
                            tax_ids.append(tax_line.id)

                        vals = {
                            'labour_id': v.labour_id.id,
                            'contractor_id': v.contractor_id.id,
                            'amount': v.price_unit,
                            'negotiated_rate': v.price_unit,
                            'quotation_comp_cont4_id': self.id,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                    elif k != selected_contractor_ids[3]:
                        pass
                    else:
                        blank_line4 = self.env['quotation.compare.contractor4'].search([('labour_id', '=', line.labour_id.id), ('contractor_id', '=', None), ('quotation_comp_cont4_id', '=', self.id)])
                        if not blank_line4:
                            vals = {
                                'labour_id': line.labour_id.id,
                                'vendor_id': None,
                                'amount': None,
                                'negotiated_rate': None,
                                'quotation_comp_cont4_id': self.id,
                                'tax_id': None,
                            }

                quotation_compare_contractor4_list.append((0, 0, vals))
                for quotation_comp_contractor4 in self.quotation_comp_contractor4:
                    if quotation_comp_contractor4.id not in quotation_compare_contractor4_list:
                        quotation_compare_contractor4_list.append((2, quotation_comp_contractor4.id))

                self.update({
                    'quotation_comp_contractor4': quotation_compare_contractor4_list
                })

            ###################  contractor 5 #################
            quotation_compare_contractor5_list = []
            vals = {}
            quotation_details_dict = self.compute_quotation_details_dictionary()
            for k_parent, v_parent in quotation_details_dict.items():
                for k, v in v_parent.items():
                    if k == selected_contractor_ids[4]:
                        tax_ids = []
                        for tax_line in v.tax_id:
                            tax_ids.append(tax_line.id)

                        vals = {
                            'labour_id': v.labour_id.id,
                            'contractor_id': v.contractor_id.id,
                            'amount': v.price_unit,
                            'negotiated_rate': v.price_unit,
                            'quotation_comp_cont5_id': self.id,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                    elif k != selected_contractor_ids[4]:
                        pass
                    else:
                        blank_line5 = self.env['quotation.compare.contractor5'].search([('labour_id', '=', line.labour_id.id), ('contractor_id', '=', None), ('quotation_comp_cont5_id', '=', self.id)])
                        if not blank_line4:
                            vals = {
                                'labour_id': line.labour_id.id,
                                'vendor_id': None,
                                'amount': None,
                                'negotiated_rate': None,
                                'quotation_comp_cont5_id': self.id,
                                'tax_id': None,
                            }

                quotation_compare_contractor5_list.append((0, 0, vals))
                for quotation_comp_contractor5 in self.quotation_comp_contractor5:
                    if quotation_comp_contractor5.id not in quotation_compare_contractor5_list:
                        quotation_compare_contractor5_list.append((2, quotation_comp_contractor5.id))

                self.update({
                    'quotation_comp_contractor5': quotation_compare_contractor5_list
                })

            ################### contractor 6 #################
            quotation_compare_contractor6_list = []
            vals = {}
            quotation_details_dict = self.compute_quotation_details_dictionary()
            for k_parent, v_parent in quotation_details_dict.items():
                for k, v in v_parent.items():
                    if k == selected_contractor_ids[5]:
                        tax_ids = []
                        for tax_line in v.tax_id:
                            tax_ids.append(tax_line.id)

                        vals = {
                            'labour_id': v.labour_id.id,
                            'contractor_id': v.contractor_id.id,
                            'amount': v.price_unit,
                            'negotiated_rate': v.price_unit,
                            'quotation_comp_cont6_id': self.id,
                            'tax_id': [(6, 0, tax_ids)],
                        }
                    elif k != selected_contractor_ids[5]:
                        pass
                    else:
                        blank_line6 = self.env['quotation.compare.contractor6'].search([('labour_id', '=', line.labour_id.id), ('contractor_id', '=', None), ('quotation_comp_cont6_id', '=', self.id)])
                        if not blank_line4:
                            vals = {
                                'labour_id': line.labour_id.id,
                                'vendor_id': None,
                                'amount': None,
                                'negotiated_rate': None,
                                'quotation_comp_cont6_id': self.id,
                                'tax_id': None,
                            }

                quotation_compare_contractor6_list.append((0, 0, vals))
                for quotation_comp_contractor6 in self.quotation_comp_contractor6:
                    if quotation_comp_contractor6.id not in quotation_compare_contractor6_list:
                        quotation_compare_contractor6_list.append((2, quotation_comp_contractor6.id))

                self.update({
                    'quotation_comp_contractor6': quotation_compare_contractor6_list
                })

        except IndexError:
            pass

    @api.depends('quotation_comp_contractor1.amount', 'quotation_comp_contractor2.amount', 'quotation_comp_contractor3.amount',
                 'quotation_comp_contractor4.amount', 'quotation_comp_contractor5.amount', 'quotation_comp_contractor6.amount',
                 'labour_quotation_comp_tax_details1.tax', 'labour_quotation_comp_tax_details2.tax', 'labour_quotation_comp_tax_details3.tax',
                 'labour_quotation_comp_tax_details4.tax', 'labour_quotation_comp_tax_details5.tax', 'labour_quotation_comp_tax_details6.tax')
    def _amount_particular_all(self):
        for order in self:
            total_contractor1 = total_contractor2 = total_contractor3 = total_contractor4 = total_contractor5 = total_contractor6 = 0.0
            total_tax_contractor1 = total_tax_contractor2 = total_tax_contractor3 = total_tax_contractor4 = total_tax_contractor5 = total_tax_contractor6 = 0.0

            for line in order.quotation_comp_contractor1:
                total_contractor1 += line.amount
            for line in order.quotation_comp_contractor2:
                total_contractor2 += line.amount
            for line in order.quotation_comp_contractor3:
                total_contractor3 += line.amount
            for line in order.quotation_comp_contractor4:
                total_contractor4 += line.amount
            for line in order.quotation_comp_contractor5:
                total_contractor5 += line.amount
            for line in order.quotation_comp_contractor6:
                total_contractor6 += line.amount
            for line in order.labour_quotation_comp_tax_details1:
                total_tax_contractor1 += line.tax
            for line in order.labour_quotation_comp_tax_details2:
                total_tax_contractor2 += line.tax
            for line in order.labour_quotation_comp_tax_details3:
                total_tax_contractor3 += line.tax
            for line in order.labour_quotation_comp_tax_details4:
                total_tax_contractor4 += line.tax
            for line in order.labour_quotation_comp_tax_details5:
                total_tax_contractor5 += line.tax
            for line in order.labour_quotation_comp_tax_details6:
                total_tax_contractor6 += line.tax

        order.update({
            'total_contractor1': total_contractor1 + total_tax_contractor1,
            'total_contractor2': total_contractor2 + total_tax_contractor2,
            'total_contractor3': total_contractor3 + total_tax_contractor3,
            'total_contractor4': total_contractor4 + total_tax_contractor4,
            'total_contractor5': total_contractor5 + total_tax_contractor5,
            'total_contractor6': total_contractor6 + total_tax_contractor6,
        })

    def get_taxes1(self):
        if self.quotation_comp_contractor1:
            tax_amount = {}
            self.labour_quotation_comp_tax_details1.unlink()

            for contractor in self.quotation_comp_contractor1:
                for tax_line in contractor.tax_id:
                    if tax_line in tax_amount:
                        tax_amount[tax_line] += (tax_line.amount / 100) * contractor.amount
                        record = self.env['tax.details.contractor1'].search([('tax_id', '=', tax_line.id), ('labour_quotation_comp_tax1_id', '=', self.id)])
                        record.write({
                            'tax': tax_amount[tax_line],
                        })
                    else:
                        tax_amount.update({tax_line: (tax_line.amount / 100) * contractor.amount})
                        self.env['tax.details.contractor1'].create({
                            'tax_id': [(6, 0, [tax_line.id])],
                            'contractor_id': contractor.contractor_id.id,
                            'tax': tax_amount[tax_line],
                            'labour_quotation_comp_tax1_id': self.id
                        })

        if self.quotation_comp_contractor2:
            tax_amount = {}
            self.labour_quotation_comp_tax_details2.unlink()
            for contractor in self.quotation_comp_contractor2:
                for tax_line in contractor.tax_id:
                    if tax_line in tax_amount:
                        tax_amount[tax_line] += (tax_line.amount / 100) * contractor.amount
                        record = self.env['tax.details.contractor2'].search([('tax_id', '=', tax_line.id), ('labour_quotation_comp_tax2_id', '=', self.id)])
                        record.write({
                            'tax': tax_amount[tax_line],
                        })
                    else:
                        tax_amount.update({tax_line: (tax_line.amount / 100) * contractor.amount})
                        self.env['tax.details.contractor2'].create({
                            'tax_id': [(6, 0, [tax_line.id])],
                            'contractor_id': contractor.contractor_id.id,
                            'tax': tax_amount[tax_line],
                            'labour_quotation_comp_tax2_id': self.id
                        })

        if self.quotation_comp_contractor3:
            tax_amount = {}
            self.labour_quotation_comp_tax_details3.unlink()
            for contractor in self.quotation_comp_contractor3:
                for tax_line in contractor.tax_id:
                    if tax_line in tax_amount:
                        tax_amount[tax_line] += (tax_line.amount / 100) * contractor.amount
                        record = self.env['tax.details.contractor3'].search([('tax_id', '=', tax_line.id), ('labour_quotation_comp_tax3_id', '=', self.id)])
                        record.write({
                            'tax': tax_amount[tax_line],
                        })
                    else:
                        tax_amount.update({tax_line: (tax_line.amount / 100) * contractor.amount})
                        self.env['tax.details.contractor3'].create({
                            'tax_id': [(6, 0, [tax_line.id])],
                            'contractor_id': contractor.contractor_id.id,
                            'tax': tax_amount[tax_line],
                            'labour_quotation_comp_tax3_id': self.id
                        })

        if self.quotation_comp_contractor4:
            tax_amount = {}
            self.labour_quotation_comp_tax_details4.unlink()
            for contractor in self.quotation_comp_contractor4:
                for tax_line in contractor.tax_id:
                    if tax_line in tax_amount:
                        tax_amount[tax_line] += (tax_line.amount / 100) * contractor.amount
                        record = self.env['tax.details.contractor4'].search([('tax_id', '=', tax_line.id), ('labour_quotation_comp_tax4_id', '=', self.id)])
                        record.write({
                            'tax': tax_amount[tax_line],
                        })
                    else:
                        tax_amount.update({tax_line: (tax_line.amount / 100) * contractor.amount})
                        self.env['tax.details.contractor4'].create({
                            'tax_id': [(6, 0, [tax_line.id])],
                            'contractor_id': contractor.contractor_id.id,
                            'tax': tax_amount[tax_line],
                            'labour_quotation_comp_tax4_id': self.id
                        })

        if self.quotation_comp_contractor5:
            tax_amount = {}
            self.labour_quotation_comp_tax_details5.unlink()
            for contractor in self.quotation_comp_contractor5:
                for tax_line in contractor.tax_id:
                    if tax_line in tax_amount:
                        tax_amount[tax_line] += (tax_line.amount / 100) * contractor.amount
                        record = self.env['tax.details.contractor5'].search([('tax_id', '=', tax_line.id), ('labour_quotation_comp_tax5_id', '=', self.id)])
                        record.write({
                            'tax': tax_amount[tax_line],
                        })
                    else:
                        tax_amount.update({tax_line: (tax_line.amount / 100) * contractor.amount})
                        self.env['tax.details.contractor5'].create({
                            'tax_id': [(6, 0, [tax_line.id])],
                            'contractor_id': contractor.contractor_id.id,
                            'tax': tax_amount[tax_line],
                            'labour_quotation_comp_tax5_id': self.id
                        })

        if self.quotation_comp_contractor6:
            tax_amount = {}
            self.labour_quotation_comp_tax_details6.unlink()
            for contractor in self.quotation_comp_contractor6:
                for tax_line in contractor.tax_id:
                    if tax_line in tax_amount:
                        tax_amount[tax_line] += (tax_line.amount / 100) * contractor.amount
                        record = self.env['tax.details.contractor6'].search([('tax_id', '=', tax_line.id), ('labour_quotation_comp_tax6_id', '=', self.id)])
                        record.write({
                            'tax': tax_amount[tax_line],
                        })
                    else:
                        tax_amount.update({tax_line: (tax_line.amount / 100) * contractor.amount})
                        self.env['tax.details.contractor6'].create({
                            'tax_id': [(6, 0, [tax_line.id])],
                            'contractor_id': contractor.contractor_id.id,
                            'tax': tax_amount[tax_line],
                            'labour_quotation_comp_tax6_id': self.id
                        })

    @api.depends('quotation_comp_contractor1.negotiated_rate', 'quotation_comp_contractor1.amount', 'labour_quotation_comp_particular.labour_qty')
    @api.onchange('quotation_comp_contractor1', 'labour_quotation_comp_particular')
    def compute_quotation_comp_tax1(self):
        qty_list = []
        for particular in self.labour_quotation_comp_particular:
            qty_list.append(particular.labour_qty)

        index = 0
        for contractor in self.quotation_comp_contractor1:
            contractor.write({'amount': qty_list[index] * contractor.negotiated_rate})
            index += 1

    @api.depends('quotation_comp_contractor2.negotiated_rate', 'quotation_comp_contractor2.amount', 'labour_quotation_comp_particular.labour_qty')
    @api.onchange('quotation_comp_contractor2', 'labour_quotation_comp_particular')
    def compute_quotation_comp_tax2(self):
        qty_list = []
        for particular in self.labour_quotation_comp_particular:
            qty_list.append(particular.labour_qty)

        index = 0
        for contractor in self.quotation_comp_contractor2:
            contractor.write({'amount': qty_list[index] * contractor.negotiated_rate})
            index += 1

    @api.depends('quotation_comp_contractor3.negotiated_rate', 'quotation_comp_contractor3.amount', 'labour_quotation_comp_particular.labour_qty')
    @api.onchange('quotation_comp_contractor3', 'labour_quotation_comp_particular')
    def compute_quotation_comp_tax3(self):
        qty_list = []
        for particular in self.labour_quotation_comp_particular:
            qty_list.append(particular.labour_qty)

        index = 0
        for contractor in self.quotation_comp_contractor3:
            contractor.write({'amount': qty_list[index] * contractor.negotiated_rate})
            index += 1

    @api.depends('quotation_comp_contractor4.negotiated_rate', 'quotation_comp_contractor4.amount', 'labour_quotation_comp_particular.labour_qty')
    @api.onchange('quotation_comp_contractor4', 'labour_quotation_comp_particular')
    def compute_quotation_comp_tax4(self):
        qty_list = []
        for particular in self.labour_quotation_comp_particular:
            qty_list.append(particular.labour_qty)

        index = 0
        for contractor in self.quotation_comp_contractor4:
            contractor.write({'amount': qty_list[index] * contractor.negotiated_rate})
            index += 1

    @api.depends('quotation_comp_contractor5.negotiated_rate', 'quotation_comp_contractor5.amount', 'labour_quotation_comp_particular.labour_qty')
    @api.onchange('quotation_comp_contractor5', 'labour_quotation_comp_particular')
    def compute_quotation_comp_tax5(self):
        qty_list = []
        for particular in self.labour_quotation_comp_particular:
            qty_list.append(particular.labour_qty)

        index = 0
        for contractor in self.quotation_comp_contractor5:
            contractor.write({'amount': qty_list[index] * contractor.negotiated_rate})
            index += 1

    @api.depends('quotation_comp_contractor6.negotiated_rate', 'quotation_comp_contractor6.amount', 'labour_quotation_comp_particular.labour_qty')
    @api.onchange('quotation_comp_contractor6', 'labour_quotation_comp_particular')
    def compute_quotation_comp_tax6(self):
        qty_list = []
        for particular in self.labour_quotation_comp_particular:
            qty_list.append(particular.labour_qty)

        index = 0
        for contractor in self.quotation_comp_contractor6:
            contractor.write({'amount': qty_list[index] * contractor.negotiated_rate})
            index += 1


class LabourList(models.Model):
    _name = 'labour.list'
    _description = 'Labour List'

    quotation_comp_lab_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_id = fields.Many2one('labour.master', 'Labour')
    is_labour = fields.Boolean('Use Labour')


class ContractorList(models.Model):
    _name = "contractor.list"
    _description = 'Contractor List'

    quotation_comp_contractor_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    is_contractor = fields.Boolean('Use Contractor')


class LabourQuotationDetails(models.Model):
    _name = "labour.quotation.details"
    _description = 'Labour Quotation Details'

    name = fields.Char("Quotation No")
    date = fields.Date('Date')
    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    labour_qty = fields.Float('Quantity')
    labour_uom = fields.Many2one('uom.uom', string='Unit')
    price_unit = fields.Float('Rate')
    negotiated_rate = fields.Float('Negotiated Rate')
    price_subtotal = fields.Float('Subtotal')
    is_use = fields.Boolean('Use')
    tax_id = fields.Many2many('account.tax', 'labour_quot_detail_tax_rel', 'tax_id', 'lbr_quot_detail_id', string='Taxes')
    tax_percent = fields.Float('Tax Percent')
    tax = fields.Float('Total Tax')
    labour_quotation_comp_detail_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_details_ = fields.One2many('labour.quotation.compare.particular', 'labour_quotation_comp_pert_detail_id', string='Labour Quotation Details Line')
    quotation_details_cont1 = fields.One2many('quotation.compare.contractor1', 'quotation_comp_cont1_detail_id', string='Quotation Details Contractor1')
    quotation_details_cont2 = fields.One2many('quotation.compare.contractor2', 'quotation_comp_cont2_detail_id', string='Quotation Details Contractor2')
    quotation_details_cont3 = fields.One2many('quotation.compare.contractor3', 'quotation_comp_cont3_detail_id', string='Quotation Details Contractor3')
    quotation_details_cont4 = fields.One2many('quotation.compare.contractor4', 'quotation_comp_cont4_detail_id', string='Quotation Details Contractor4')
    quotation_details_cont5 = fields.One2many('quotation.compare.contractor5', 'quotation_comp_cont5_detail_id', string='Quotation Details Contractor5')
    quotation_details_cont6 = fields.One2many('quotation.compare.contractor6', 'quotation_comp_cont6_detail_id', string='Quotation Details Contractor6')
    labour_quotation_tax_per = fields.One2many('labour.tax.particular', 'labour_quotation_comp_taxper_detail_id', string='Quotation Particular Tax')
    quotation_tax1_detail_per = fields.One2many('tax.details.contractor1', 'labour_quotation_comp_tax1_detail_id', string='Quotation Detail Tax1')
    quotation_tax2_detail_per = fields.One2many('tax.details.contractor2', 'labour_quotation_comp_tax2_detail_id', string='Quotation Detail Tax2')
    quotation_tax3_detail_per = fields.One2many('tax.details.contractor3', 'labour_quotation_comp_tax3_detail_id', string='Quotation Detail Tax3')
    quotation_tax4_detail_per = fields.One2many('tax.details.contractor4', 'labour_quotation_comp_tax4_detail_id', string='Quotation Detail Tax4')
    quotation_tax5_detail_per = fields.One2many('tax.details.contractor5', 'labour_quotation_comp_tax5_detail_id', string='Quotation Detail Tax5')
    quotation_tax6_detail_per = fields.One2many('tax.details.contractor6', 'labour_quotation_comp_tax6_detail_id', string='Quotation Detail Tax6')


class LabourQuotationCompareParticular(models.Model):
    _name = 'labour.quotation.compare.particular'
    _description = 'Labour Quotation  Compare Particular'

    labour_id = fields.Many2one('labour.master', 'Particular')
    price_expt = fields.Float('Expected Rate')
    labour_qty = fields.Float('Quantity', default=1)
    labour_uom = fields.Many2one('uom.uom', string='Unit')
    labour_quotation_comp_pert_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_pert_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Select')


class QuotationCompareContractor1(models.Model):
    _name = "quotation.compare.contractor1"
    _description = "Quotation Compare Contractor 1"

    labour_id = fields.Many2one('labour.master', 'Particular')
    contractor_id = fields.Many2one('res.partner', 'contractor', domain=[('contractor', '=', True)])
    negotiated_rate = fields.Float('Nego.Rate')
    tax_id = fields.Many2many('account.tax', 'labour_quot_con1_tax_rel', 'tax_id', 'lbr_quot_con1_id', string='Taxes')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount = fields.Float('Amount')
    quotation_comp_cont1_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    quotation_comp_cont1_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Approve')


class QuotationCompareContractor2(models.Model):
    _name = "quotation.compare.contractor2"
    _description = "Quotation Compare Contractor 2"

    labour_id = fields.Many2one('labour.master', 'Particular')
    contractor_id = fields.Many2one('res.partner', 'contractor', domain=[('contractor', '=', True)])
    negotiated_rate = fields.Float('Nego.Rate')
    tax_id = fields.Many2many('account.tax', 'labour_quot_con2_tax_rel', 'tax_id', 'lbr_quot_con2_id', string='Taxes')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount = fields.Float('Amount')
    quotation_comp_cont2_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    quotation_comp_cont2_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Approve')


class QuotationCompareContractor3(models.Model):
    _name = "quotation.compare.contractor3"
    _description = "Quotation Compare Contractor 3"

    labour_id = fields.Many2one('labour.master', 'Particular')
    contractor_id = fields.Many2one('res.partner', 'contractor', domain=[('contractor', '=', True)])
    negotiated_rate = fields.Float('Nego.Rate')
    tax_id = fields.Many2many('account.tax', 'labour_quot_con3_tax_rel', 'tax_id', 'lbr_quot_con3_id', string='Taxes')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount = fields.Float('Amount')
    quotation_comp_cont3_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    quotation_comp_cont3_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Approve')


class QuotationCompareContractor4(models.Model):
    _name = "quotation.compare.contractor4"
    _description = "Quotation Compare Contractor 4"

    labour_id = fields.Many2one('labour.master', 'Particular')
    contractor_id = fields.Many2one('res.partner', 'contractor', domain=[('contractor', '=', True)])
    negotiated_rate = fields.Float('Nego.Rate')
    tax_id = fields.Many2many('account.tax', 'labour_quot_con4_tax_rel', 'tax_id', 'lbr_quot_con4_id', string='Taxes')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount = fields.Float('Amount')
    quotation_comp_cont4_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    quotation_comp_cont4_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Approve')


class QuotationCompareContractor5(models.Model):
    _name = "quotation.compare.contractor5"
    _description = "Quotation Compare Contractor 5"

    labour_id = fields.Many2one('labour.master', 'Particular')
    contractor_id = fields.Many2one('res.partner', 'contractor', domain=[('contractor', '=', True)])
    negotiated_rate = fields.Float('Nego.Rate')
    tax_id = fields.Many2many('account.tax', 'labour_quot_con5_tax_rel', 'tax_id', 'lbr_quot_con5_id', string='Taxes')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount = fields.Float('Amount')
    quotation_comp_cont5_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    quotation_comp_cont5_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Approve')


class QuotationCompareContractor6(models.Model):
    _name = "quotation.compare.contractor6"
    _description = "Quotation Compare Contractor 6"

    labour_id = fields.Many2one('labour.master', 'Particular')
    contractor_id = fields.Many2one('res.partner', 'contractor', domain=[('contractor', '=', True)])
    negotiated_rate = fields.Float('Nego.Rate')
    tax_id = fields.Many2many('account.tax', 'labour_quot_con6_tax_rel', 'tax_id', 'lbr_quot_con6_id', string='Taxes')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount = fields.Float('Amount')
    quotation_comp_cont6_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    quotation_comp_cont6_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')
    is_approve = fields.Boolean('Approve')


class LabourTaxParticular(models.Model):
    _name = "labour.tax.particular"
    _description = "Labour Tax Particular"

    labour_id = fields.Many2one('labour.master', 'product')
    labour_quotation_comp_taxper_id = fields.Many2one('labour.quotation.comparison', 'Labour Quotation')
    labour_quotation_comp_taxper_detail_id = fields.Many2one('labour.quotation.details', string='Labour Quotation details', ondelete='cascade')


class TaxDetailsContractor1(models.Model):
    _name = "tax.details.contractor1"
    _description = "Tax Details Contractor 1"

    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    tax_id = fields.Many2many('account.tax', 'tax_detail_con1_tax_rel', 'tax_id', 'tax_detail_con1_id', string='Taxes')
    tax = fields.Float('Tax')
    labour_quotation_comp_tax1_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_tax1_detail_id = fields.Many2one('labour.quotation.details', string='Quotation details', ondelete='cascade')


class TaxDetailsContractor2(models.Model):
    _name = "tax.details.contractor2"
    _description = "Tax Details Contractor 2"

    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    tax_id = fields.Many2many('account.tax', 'tax_detail_con2_tax_rel', 'tax_id', 'tax_detail_con2_id', string='Taxes')
    tax = fields.Float('Tax')
    labour_quotation_comp_tax2_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_tax2_detail_id = fields.Many2one('labour.quotation.details', string='Quotation details', ondelete='cascade')


class TaxDetailsContractor3(models.Model):
    _name = "tax.details.contractor3"
    _description = "Tax Details Contractor 3"

    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    tax_id = fields.Many2many('account.tax', 'tax_detail_con3_tax_rel', 'tax_id', 'tax_detail_con3_id', string='Taxes')
    tax = fields.Float('Tax')
    labour_quotation_comp_tax3_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_tax3_detail_id = fields.Many2one('labour.quotation.details', string='Quotation details', ondelete='cascade')


class TaxDetailsContractor4(models.Model):
    _name = "tax.details.contractor4"
    _description = "Tax Details Contractor 5"

    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    tax_id = fields.Many2many('account.tax', 'tax_detail_con4_tax_rel', 'tax_id', 'tax_detail_con4_id', string='Taxes')
    tax = fields.Float('Tax')
    labour_quotation_comp_tax4_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_tax4_detail_id = fields.Many2one('labour.quotation.details', string='Quotation details', ondelete='cascade')


class TaxDetailsContractor5(models.Model):
    _name = "tax.details.contractor5"
    _description = "Tax Details Contractor 5"

    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    tax_id = fields.Many2many('account.tax', 'tax_detail_con5_tax_rel', 'tax_id', 'tax_detail_con5_id', string='Taxes')
    tax = fields.Float('Tax')
    labour_quotation_comp_tax5_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_tax5_detail_id = fields.Many2one('labour.quotation.details', string='Quotation details', ondelete='cascade')


class TaxDetailsContractor6(models.Model):
    _name = "tax.details.contractor6"
    _description = "Tax Details Contractor 6"

    contractor_id = fields.Many2one('res.partner', 'Contractor', domain=[('contractor', '=', True)])
    labour_id = fields.Many2one('labour.master', 'Labour')
    tax_id = fields.Many2many('account.tax', 'tax_detail_con6_tax_rel', 'tax_id', 'tax_detail_con6_id', string='Taxes')
    tax = fields.Float('Tax')
    labour_quotation_comp_tax6_id = fields.Many2one('labour.quotation.comparison', 'Quotation')
    labour_quotation_comp_tax6_detail_id = fields.Many2one('labour.quotation.details', string='Quotation details', ondelete='cascade')

