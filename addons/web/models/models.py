# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_progress_bar(self, domain, group_by, progress_bar):
        """
        Gets the data needed for all the kanban column progressbars.
        These are fetched alongside read_group operation.

        :param domain - the domain used in the kanban view to filter records
        :param group_by - the name of the field used to group records into
                        kanban columns
        :param progress_bar - the <progressbar/> declaration attributes
                            (field, colors, sum)
        :return a dictionnary mapping group_by values to dictionnaries mapping
                progress bar field values to the related number of records
        """
        fields = [progress_bar['field'], group_by]
        records_values = self.search_read(domain or [], fields)

        data = {}
        for record_values in records_values:
            group_by_value = record_values[group_by]
            if type(group_by_value) == tuple:
                group_by_value = group_by_value[1] # FIXME should use technical value (0)

            if group_by_value not in data:
                data[group_by_value] = {}
                for key in progress_bar['colors']:
                    data[group_by_value][key] = 0

            field_value = record_values[progress_bar['field']]
            if field_value in data[group_by_value]:
                data[group_by_value][field_value] += 1

        return data
