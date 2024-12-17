# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_session_info(self, allowed_companies):
        '''
        Args:
            allowed_companies: The companies allowed to the user when creating the session_info.
                               These can be the user companies, or the user companies with the ancestors.

        Returns:
            A dictionary of the company values to be added to the session_info

        '''
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'sequence': self.sequence,
            'child_ids': (self.child_ids & allowed_companies).ids,
            'parent_id': self.parent_id.id,
        }
