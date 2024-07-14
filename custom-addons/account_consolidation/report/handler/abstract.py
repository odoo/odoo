# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from abc import ABC


class AbstractHandler(ABC):
    key = None

    def __init__(self, env):
        """
        Create a DefautltHandler which handles a filter in trial balance report.
        :param env: the env
        """
        self.env = env

    def handle(self, client_state: dict, base_period, current_options) -> list:
        """
        Handle the filter values.
        :param client_state: the filter state sent by the client app
        :type client_state: dict
        :param base_period: the base period used to display trial balance report
        :param current_options: the current options
        :type current_options: dict
        :return: a list of dict representing the new state of the filter
        :rtype: list
        """
        return []

    @classmethod
    def get_selected_values(cls, options: dict) -> list:
        """
        Get selected filter value ids based on given options dict
        :param options: the options dict
        :type options: dict
        :return: a list containing all selected value ids.
        :rtype list:
        """
        return []

    # STATICS
    @classmethod
    def is_set(cls, options: dict) -> bool:
        """
        Determine if the filter is set or not in the given options
        :param options: the options
        :type options: dict
        :return: True if filter is set, False otherwise
        :rtype: bool
        """
        return len(cls.get_selected_values(options)) > 0
