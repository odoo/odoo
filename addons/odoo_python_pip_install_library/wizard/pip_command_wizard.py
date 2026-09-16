from odoo import api, fields, models
import subprocess
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class PipCommands(models.TransientModel):
    _name = 'pip.command'
    _description = 'Install python library'
    
    library_name = fields.Char('Library Name')
    pip_versions = fields.Selection(selection=[('pip', 'pip'),('pip3', 'pip3')],string='Pip versions',default='pip', required=True,)
    def install_button(self):
        try:
            result = subprocess.run([self.pip_versions, 'install', self.library_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            raise UserError(result.stdout.decode('utf-8'))
        except subprocess.CalledProcessError as e:
            # Handle errors here
            raise UserError(f"Error: {e.stderr.decode('utf-8')}")
            _logger.info(f"Error: {e.stderr.decode('utf-8')}")