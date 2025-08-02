from odoo import models, fields
from odoo.exceptions import UserError
import os
import csv
from datetime import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        discrepancies = []
        for move_line in self.move_line_ids:
            discrepancy = {
                'source_document': self.origin or '',
                'received_from': self.partner_id.name or '',
                'product_name': move_line.product_id.name or '',
                'demand': move_line.move_id.product_uom_qty or 0,
                'quantity_received': move_line.quantity or 0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            discrepancies.append(discrepancy)

        # Create the discrepancy file regardless of discrepancies
        self.create_discrepancy_file(discrepancies)

        # Check for actual discrepancies
        actual_discrepancies = [d for d in discrepancies if d['demand'] != d['quantity_received']]
        if actual_discrepancies:
            discrepancies_text = "\n".join([
                f"Product: {d['product_name']}, Demand: {d['demand']}, Received: {d['quantity_received']}"
                for d in actual_discrepancies
            ])
            self.notify_warning(message=f"There are discrepancies in the following products:\n{discrepancies_text}", title="Discrepancy Warning")
        
        return super(StockPicking, self).button_validate()

    def create_discrepancy_file(self, discrepancies):
        # Define the directory
        directory = 'home/ubuntu/wms/outputfiles/kids/grn/'  # Update this path
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Create a unique file name based on the current date and time
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(directory, f'GRN_{timestamp}.csv')

        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = ['source_document', 'received_from', 'product_name', 'demand', 'quantity_received', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write the header
            writer.writeheader()
            # Write the data
            for discrepancy in discrepancies:
                writer.writerow(discrepancy)

    def notify_warning(self, message, title):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': True,
                'type': 'warning',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
