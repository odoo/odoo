from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    activity_counts = fields.Json(compute='_compute_activity_counts')

    def _compute_activity_counts(self):
        """
        Compute the list of activity counts to be displayed on the partner list view.

        This method is intended to be overridden by other modules to inject their own counts.
        It should return a list of dictionaries, each representing a count item with the following structure:

            {
                'title': str,               # Display label or tooltip
                'count': int,               # The numeric value to show
                'icon_name': str,           # Font Awesome icon class (e.g. "fa-star")
                'action_name': str,         # Name of the server action or method to trigger
                'groups': str (optional),   # Security group required to display this item
            }

        The returned list will be rendered dynamically in the UI.
        """
        for partner in self:
            partner.activity_counts = []
