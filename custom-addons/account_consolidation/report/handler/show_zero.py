# -*- coding: utf-8 -*-
from odoo.tools.float_utils import float_is_zero


class ShowZeroHandler:
    @classmethod
    def account_line_should_be_added(cls, line: dict, options: dict = None, key: str = 'consolidation_show_zero_balance_accounts') -> bool:
        """
        Determine if an account line should be added or not to the list of report lines.
        An account should be shown no matter what if options key ("consolidation_show_zero_balance_accounts" by default) is True,
        else it has to be shown if its total is not zero.
        :param line: the account line to check
        :type line: dict
        :param options: options of the report
        :type options: dict
        :param key: the options key of the show zero parameter, "consolidation_show_zero_balance_accounts" by default
        :type key: str
        :return: True if the section's lines should be added, False otherwise
        """
        if options is not None and options.get(key):
            return True
        else:
            return cls._line_is_not_zero(line)

    @classmethod
    def section_line_should_be_added(cls, section_lines: list, options: dict = None, key: str = 'consolidation_show_zero_balance_accounts') -> bool:
        """
        Determine if a section's lines should be added or not to the list of report lines.
        A section should be shown no matter what if options "consolidation_show_zero_balance_accounts" is True, else it has to be
        shown if it has children or if its total is not zero.
        :param section_lines: the section lines corresponding to the generation of lines for a given section
        :type section_lines: list
        :param options: options of the report
        :type options: list
        :param key: the options key of the show zero parameter, "consolidation_show_zero_balance_accounts" by default
        :type key: str
        :return: True if the section's lines should be added, False otherwise
        """
        if options is None or options.get(key, False):
            return True
        return cls._section_line_has_children(section_lines) or cls._section_line_is_not_zero(section_lines)

    @staticmethod
    def _line_is_not_zero(line: dict) -> bool:
        """
        Check if a line has a total of zero
        :param line: the line to test (formatted as to be renderer in a report)
        :type line: dict
        :return: True is the line has a total of zero (no columns, all columns are 0 or sum of columns = 0),
        False otherwise
        :rtype: bool
        """
        cols = line.get('columns', [{}])
        total = sum([col.get('no_format', 0) for col in cols])
        return not float_is_zero(total, 6)

    @staticmethod
    def _section_line_has_children(section_lines: list) -> bool:
        """
        Determine if a section line has children or not
        :param section_lines: the section lines corresponding to the generation of lines for a given section
        :type section_lines: list
        :return: True if section line has children, this means the generation returns at least 2 lines (the one
        representing the sections and one representing a child), False otherwise.
        :rtype: bool
        """
        return len(section_lines) > 1

    @classmethod
    def _section_line_is_not_zero(cls, section_lines: list) -> bool:
        """
        Check if section line has a total of 0
        :param section_lines: the section lines corresponding to the generation of lines for a given section
        :return: True if the section is not empty and has a total > 0, False otherwise
        :rtype: bool
        """
        return len(section_lines) > 0 and cls._line_is_not_zero(section_lines[0])
