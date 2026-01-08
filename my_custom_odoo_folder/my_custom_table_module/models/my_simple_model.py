# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

# Define the new model
class MySimpleData(models.Model):
    """
    This class defines a simple model. Odoo will automatically create a
    database table named 'my_simple_data' based on this definition
    when the module is installed.
    """
    # Internal Odoo technical name for the model.
    # Convention: use dots. Odoo creates the table name by replacing dots with underscores.
    _name = 'my.simple.data'

    # Description shown in Odoo UI when referring to the model (optional but good practice)
    _description = 'My Simple Data Table'

    # Define fields for the model. These will become columns in the table.
    name = fields.Char(
        string='Record Name', # Label shown in the UI
        required=True,      # Makes the database column NOT NULL
        help="The main identifier for this record." # Tooltip in the UI
        )
    description = fields.Text(
        string='Description',
        help="A longer description for this record."
        )
    record_date = fields.Date(
        string='Date',
        default=fields.Date.today # Set a default value for the column
        )
    is_active = fields.Boolean(
        string='Is Active?',
        default=True, # Default value for new records
        help="Check if this record is currently active."
        )

    # Odoo automatically adds standard fields like 'id', 'create_date', 'create_uid',
    # 'write_date', 'write_uid' to the table.
