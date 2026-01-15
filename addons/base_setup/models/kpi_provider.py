from odoo import api, models


class KpiProvider(models.AbstractModel):
    _name = 'kpi.provider'
    _description = 'KPI Provider'

    @api.model
    def get_kpi_summary(self):
        """
        Other modules can override this method to add their own KPIs to the list.
        This method will be called by the databases module to retrieve the data displayed on the databases list.
        The return value shall be a list of dictionaries with the following keys:

        - id: a unique identifier for the KPI
        - type: the type of data (`integer` or `return_status`)
        - name: the translated name of the KPI, as displayable to the current user
        - value: either the numeric value (for `type=integer`) or one of the statuses (for `type=return_status`):
          - late       one return of this type should have been done already
          - longterm   the deadline of the closest uncompleted return is in more than 3 months
          - to_do      the deadline of the closest uncompleted return is in less than 3 months
          - to_submit  the closest uncompleted return is ready, but still needs an action
          - done       all of the forseeable returns are completed
        """
        return []
