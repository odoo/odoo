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
    name = fields.Char()
    category = fields.Selection([('trading', 'Trading'), ('supplying', 'Supplying')
                             ], 'Category'
                             )
    type = fields.Selection([('efet', 'EFET'), ('other', 'OTHER')],
                            'Type')
    position = fields.Selection([('buy', 'Buy'), ('sell', 'Sell')],
                                'Position')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    power = fields.Float(string='Power')
    powerUnit = fields.Selection([('mwh', 'MWh'), ('kwh', 'kWh')])
    powerUnit = fields.Selection([('mwh', 'MWh'), ('kwh', 'kWh')])
    timeUnit = fields.Selection([('60', '60 min'), ('15', '15 min')])
    price = fields.Float(string='Price')
    status = fields.Selection([('initial', 'Initial'), ('executing', 'Executing'),('finished', 'Finished')], 'Status')
    master_contract_id = fields.Many2one('master_contract', string='Master Contract')
    delivery_point_id = fields.Many2one('border', string='Delivery Point')
    end_point_id = fields.Many2one('border', string='End Point')
    transit_border = fields.Boolean()
    transit_border_ids = fields.Many2many('border',"contract_transit_id", string='Transit Border')
    other_border = fields.Boolean()
    other_border_ids = fields.Many2many('border',"contract_other_id", string='Other Border')
    profile_id = fields.Many2one('profile', string='Profile')
    period_id = fields.Many2one('period', string='Period')
    loadshape_details_ids = fields.One2many('loadshape_details', 'contract_id', string='Load Shape Details')
    external_id = fields.Char(string='External ID')
    risk = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], 'Risk')
    cai_code = fields.Char(string='CAI Code')
    contract_price_ids = fields.One2many('contract_prices', 'contract_id', string='Contract Prices')
    excel_file = fields.Binary(string="Excel File", attachment=True, help="Upload your Excel file here.")

    @api.onchange('start_date', 'end_date','period_id','profile_id','power','powerUnit','price')
    def _compute_loadshape_details(self):
        for record in self:
            if record.start_date and record.end_date:
                date_range = (record.end_date - record.start_date).days + 1
                loadshape_details = []
                for i in range(date_range):
                    load_date = record.start_date + timedelta(days=i)
                    for hour in range(24):
                        loadshape_details.append((0, 0, {
                            'contract_id': record.id,
                            'powerdate': load_date,
                            'powerhour': hour,
                            'powerprice': record.price,
                            'powerunit': record.powerUnit,
                            'powerfinalprice': 0,
                            'powerfinal': 0,
                            'power': record.power
                        }))
                record.loadshape_details_ids = loadshape_details
    
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
