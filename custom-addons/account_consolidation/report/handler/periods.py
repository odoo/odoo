# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .abstract import AbstractHandler


class PeriodsHandler(AbstractHandler):
    key = 'periods'

    def __init__(self, env, max_amount_of_periods: int = 5):
        """
        Create a PeriodsHandler which handles the "Comparison" filter consolidation in trial balance report.
        :param env: the env
        :param max_amount_of_periods: the maximum amount of periods to show in the filter.
        :type max_amount_of_periods: int
        """
        super().__init__(env)
        self.max_amount_of_periods = max_amount_of_periods

    # OVERRIDES
    def handle(self, client_state: dict, base_period, current_options) -> list:
        if client_state is None:
            selected_period_ids = []
        else:
            selected_period_ids = [cs['id'] for cs in client_state if cs['selected']]
        return [self._to_option_dict(period, selected_period_ids)
                for period in self.get_all_available_values(base_period)]

    @classmethod
    def get_selected_values(cls, options: dict) -> list:
        periods_dict = options.get(cls.key, [])
        return [p['id'] for p in periods_dict if p['selected']]

    def get_all_available_values(self, base_period):
        """
        Get all available periods for filter based on a given period
        :param base_period: the period
        :return: a recordset containing similar periods based on the given period
        """
        return base_period._get_similar_periods(limit=self.max_amount_of_periods)

    @staticmethod
    def _to_option_dict(period, selected_period_ids: list) -> dict:
        """
        Transform a period in a option dict
        :param period: the period
        :param selected_period_ids: the list containing all selected period ids
        :type selected_period_ids: list
        :return: a dict containing the id, the name and the selected boolean for the given period.
        :rtype: dict
        """
        return {
            'id': period.id,
            'name': f'{period.display_name} ({period.display_dates})',
            'selected': period.id in selected_period_ids
        }
