# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .abstract import AbstractHandler
from .periods import PeriodsHandler


class JournalsHandler(AbstractHandler):
    key = 'consolidation_journals'

    # OVERRIDES
    def handle(self, client_state: dict, base_period, current_options) -> list:
        if PeriodsHandler.is_set(current_options):
            return self.get_option_values(base_period, {})
        else:
            return self.get_option_values(base_period, client_state)

    @classmethod
    def get_selected_values(cls, options: dict) -> list:
        if options:
            options_journals = options.get('consolidation_journals', [])
            at_least_one_selected = any(opt_journal['selected'] for opt_journal in options_journals)
            if options_journals is not None and len(options_journals) > 0:
                return [journal['id'] for journal in options_journals if
                        not at_least_one_selected or journal['selected']]
        return []

    def get_all_available_values(self, base_period):
        """
        Get all available values for given base period
        :param base_period: the base period object
        :return: a recordset containing all found journals
        """
        domain = [('period_id', '=', base_period.id)]
        return self.env['consolidation.journal'].search(domain)

    def get_option_values(self, base_period, client_state: dict) -> list:
        """
        Get all option values with the right state
        :param base_period: the base period
        :param client_state: the filter state sent by the client app
        :type client_state: dict
        :return: a list of all journals formatted as a dict to be shown in filter on client.
        """
        client_state_dict = {j['id']: j['selected'] for j in client_state} if client_state is not None else {}
        all_journals = self.get_all_available_values(base_period)
        return [
            self.to_option_dict(journal, client_state_dict.get(journal.id, False))
            for journal in all_journals
        ]

    @staticmethod
    def to_option_dict(journal, selected) -> dict:
        """
        Transform a journal in a option dict
        :param journal: the journal object
        :param selected: a boolean representing the fact that the journal is selected or not
        :type selected: bool
        :return: the formatted dict corresponding to the given journal
        :rtype: dict
        """
        return {'id': journal.id, 'name': journal.name, 'selected': selected}
