from odoo import models, fields,api
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)
from io import BytesIO
import base64
import pandas as pd


class Contract(models.Model):
    _name = "contract"
    _description = "Description of the Contract model"

    name = fields.Char(string='Name', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('contract'))
    category = fields.Selection([
        ('trading', 'Trading'),
        ('supplying', 'Supplying')
    ], 'Category')
    is_transit = fields.Boolean()
    type = fields.Selection([
        ('efet', 'EFET'),
        ('other', 'OTHER')
    ], 'Type')
    product = fields.Selection([
        ('energy', 'Energy'),
        ('cbc', 'Capacity')
    ], 'Product')
    position = fields.Selection([
        ('buy', 'Buy'),
        ('sell', 'Sell')
    ], 'Position', required=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    power = fields.Float(string='Power per time unit')
    powerUnit = fields.Selection([('mwh', 'MWh'), ('kwh', 'kWh')])
    timeUnit = fields.Selection([('60', '60 min'), ('15', '15 min')])
    total_contract_power = fields.Float(string='Total Power')
    price = fields.Float(string='Price Unit')
    total_contract_value = fields.Float(string='Total Contract Value - no VAT')
    vat = fields.Boolean(string='VAT')
    total_contract_value_with_vat = fields.Float(string='Total Contract Value - with VAT')
    status = fields.Selection([
        ('initial', 'Initial'),  # draft
        ('executing', 'Executing'),  # running | active
        ('finished', 'Finished')  # done
    ], 'Status', required=True, default='initial')
    master_contract_id = fields.Many2one('master_contract', string='Master Contract')
    parent_contract_id = fields.Many2one('contract', string='Parent Contract', domain="[('is_transit','=', False)]",
                                         help='When transit, the contract is derived from a parent contract')
    delivery_point_id = fields.Many2one('border', string='Delivery Point')
    cai_code = fields.Char(string='CAI Code')
    profile_id = fields.Many2one('profile', string='Profile')
    period_id = fields.Many2one('period', string='Period')
    loadshape_details_ids = fields.One2many('loadshape_details', 'contract_id', string='Load Shape Details')
    distribution_order_ids = fields.One2many('distribution.order', 'contract_id', string='Distribution Details')
    external_id = fields.Char(string='External ID')
    risk = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], 'Risk')
    cai_code = fields.Char(string='CAI Code')
    contract_price_ids = fields.One2many('contract_prices', 'contract_id', string='Contract Prices')
    excel_file = fields.Binary(string="Excel File", attachment=True, help="Upload your Excel file here.")
    payment_terms_id = fields.Many2one('payment_terms', string='Payment Terms')

    @api.onchange('start_date', 'end_date', 'period_id', 'profile_id')
    def _compute_loadshape_details(self):
        for record in self:
            if record.start_date and record.end_date:
                date_range = (record.end_date - record.start_date).days + 1
                loadshape_details = []
                record.loadshape_details_ids.unlink()

                for i in range(date_range):
                    load_date = record.start_date + timedelta(days=i)
                    for hour in range(24):
                        loadshape_details.append((0, 0, {
                            'contract_id': record.id,
                            'powerdate': load_date,
                            'powerhour': hour+1,
                            'powerprice': record.price,
                            'powerunit': record.powerUnit,
                            'powerfinalprice': 0,
                            'powerfinal': 0,
                            'power': record.power
                        }))

                self.write({'loadshape_details_ids': loadshape_details})

                #record.loadshape_details_ids = loadshape_details
    
    @api.onchange('contract_price_ids', 'loadshape_details_ids', 'vat')
    def _compute_value_total(self):
        for record in self:
            record.total_contract_value = 0
            record.total_contract_power = 0
            for item in  record.loadshape_details_ids:
                record.total_contract_value = record.total_contract_value + (item.power * item.powerprice)
                record.total_contract_power = record.total_contract_power + item.power 
        if record.vat:
            record.total_contract_value_with_vat = record.total_contract_value * 1.2
        else:
            record.total_contract_value_with_vat = record.total_contract_value

    @api.onchange('contract_price_ids')
    def _compute_price(self):
        for record in self:
            record.price = 0
            for item in record.contract_price_ids:
                record.price = record.price + item.value

    def action_delete_detail(self):
        for record in self:
            record.loadshape_details_ids.unlink()
    
    def action_import_excel(self):
        # Get the uploaded Excel file data
        excel_file = self.excel_file
        if not excel_file:
            # Handle if no file is uploaded
            return

        # Decode the base64 data
        excel_data = base64.b64decode(excel_file)

        # Create a pandas DataFrame from the Excel data
        excel_df = pd.read_excel(BytesIO(excel_data), sheet_name='data')

        # Process the DataFrame as needed (e.g., create records)
        for index, row in excel_df.iterrows():
            # Example: Create a record for each row
            self.env['loadshape_details'].create({
                # Add more fields as needed
                'contract_id': self.id,
                'powerdate': row['powerdate'],
                'powerhour': row['powerhour'],
                'powerprice': row['powerprice'],
                'powerunit': row['powerunit'],
                'powerfinalprice': row['powerfinalprice'],
                'powerfinal': row['powerfinal'],
                'power': row['power'],
            })

        # Optionally, display a success message or perform additional actions
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Successful',
                'message': 'Excel data imported successfully!',
            }
        }

    def activate_contract(self):
        self.write({'status': 'executing'})

    def finish_contract(self):
        # TODO: cron job - every once a day check - if contract is active based on start-end date
        self.write({'status': 'finished'})

    def action_open_transit_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'contract',
            'type': 'ir.actions.act_window',
            'context': {'default_parent_contract_id': self.id},
            'domain': [('parent_contract_id', '=', self.id)],
        }
