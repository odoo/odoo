# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Mruthul Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models
from odoo.exceptions import ValidationError
import subprocess


class PipInstall(models.TransientModel):
    """Class for adding the fields and functions for wizard"""
    _name = 'pip.install'
    _description = 'Pip Installer'

    name = fields.Char(string='Command', help='Write the pip command to execute.')

    def action_done(self):
        """Function for executing the pip commands in terminal"""
        command = self.name
        try:
            if command.startswith("pip"):
                process = subprocess.Popen(['yes'], stdout=subprocess.PIPE)
                result = subprocess.run(command, shell=True, check=True,
                                        stdin=process.stdout,
                                        stdout=subprocess.PIPE, text=True)
                message = self.env['import.message'].create({'message': result.stdout})
                if result.stdout != '':
                    return {
                        'name': 'Successfully Executed',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'import.message',
                        'res_id': message.id,
                        'target': 'new'
                    }
            else:
                raise ValidationError('Please enter a proper pip install command')
        except subprocess.CalledProcessError:
            raise ValidationError('Please enter a proper pipinstall command')
        except TypeError:
            raise ValidationError('Please enter a proper pip install command')
