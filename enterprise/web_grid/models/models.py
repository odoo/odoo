# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def grid_update_cell(self, domain, measure_field_name, value):
        """Update a grid cell

        :param list domain: domain to apply to fetch the records in the cell
        :param str measure_field_name: the field name used as measure
        :param float value: value to add
        """
        raise NotImplementedError()

    @api.model
    def grid_unavailability(self, start_date, end_date, groupby='', res_ids=None):
        """ Get the unavailability intervals for the grid view when the column is a Date

            :start_date (Date): the start date of the grid view.
            :end_date (Date): the end date of the grid view.
            :groupby (str): field to use to group by the unavailability intervals.
            :res_ids (List): the ids to use to correctly groupby without adding new data in the grid.

            :returns: dict in which the key is the field specified in the groupby parameter
                      (or just false) and values will be a list of unavailability dates.
                      Example if
                        - the groupby is many2one foo_id,
                        - start_date: 2022-12-19,
                        - end_date: 2022-12-25,
                        - res_ids: [1, 2]
                      then the result will be:
                        result = {
                            1: ["2022-12-24", "2022-12-25"],
                            2: ["2022-12-23", "2022-12-24", "2022-12-25"],
                        }
        """
        return {}
