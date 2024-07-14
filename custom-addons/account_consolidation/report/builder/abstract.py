from abc import ABC

from odoo import _
from odoo.tools.float_utils import float_is_zero
from ..handler.show_zero import ShowZeroHandler


class AbstractBuilder(ABC):
    def __init__(self, env, value_formatter):
        """
        Instantiate a builder that will be responsible to create the report lines.
        :param env: the env object in which this builder is used
        :param value_formatter: a function that will be used to format float values in report
        """
        self.env = env
        self.value_formatter = value_formatter

    def _get_lines(self, period_ids: list, options: dict, line_id: str = None) -> list:
        """
        Return the report lines based on selected period ids, the report options and the line from which the report is
        print.
        :param period_ids: list containing the ids of the selected periods
        :type period_ids: list
        :param options: options of the report
        :type options: dict
        :param line_id: the id of the line from which the report is print (or None if whole report is print)
        :type line_id: str
        :return: list of dict representing the report lines
        :rtype:list
        """
        if self._output_will_be_empty(period_ids, options, line_id):
            return []
        params = self._get_params(period_ids, options, line_id)

        if options.get('consolidation_hierarchy'):
            return self._get_hierarchy(options, line_id, **params)
        else:
            return self._get_plain(options, **params)

    def _output_will_be_empty(self, period_ids: list, options: dict, line_id: str = None) -> bool:
        """
        Determine with the initial parameters given to the builder if the output would be empty.
        :param period_ids: the period ids used to generate the report
        :type period_ids: list
        :param options: options of the report
        :type options: dict
        :param line_id: the line id from which this method is called (when you unfold a line)
        :type line_id: str
        :return: True if the result will be empty in any case, False otherwise
        :type: bool
        """
        return False

    def _get_params(self, period_ids: list, options: dict, line_id: str = None) -> dict:
        """
        Get the parameters to give to call stack for the builder. It's mainly useful for children overriding so that
        needed parameters are propagated to all other methods called.
        :param period_ids: the period ids used to generate the report
        :type period_ids: list
        :param options: options of the report
        :type options: dict
        :param line_id: the line id from which this method is called (when you unfold a line)
        :type line_id: str
        :return: a dict of parameters useful for all other methods of the builder to work correctly
        :type: dict
        """
        return {
            'period_ids': period_ids
        }

    def _get_plain(self, options: dict, **kwargs) -> list:
        """
        Return the report lines without any hierarchy. It loads all the accounts of the chart and process them all.
        :param options: options of the report
        :type options: dict
        :return: list of dict representing the report lines
        :rtype: list
        """
        accounts = self._get_all_accounts(options, **kwargs)
        totals, lines = self._handle_accounts(accounts, options, 3, **kwargs)
        if totals:
            lines.append(self._build_total_line(totals, options, **kwargs))
        return lines

    def _get_hierarchy(self, options: dict, line_id: str = None, **kwargs) -> list:
        """
        Return the report lines with the proper hierarchy. These are the main steps of the algorithm :
        1) - If no line_id is given, it starts by getting all accounts without parent ("orphans") and process them to
            get their totals and the lines to add in the output. Then it fetches all the sections without parents
            ("root sections"), these will be used later in the algorithm.
            - If a line_id is given, then the line_id corresponds to a line of a section and is formatted with
            account_reports._get_generic_line_id(). It parses this ID and get the section with is used later in the algorithm.
        2) It processes recursively the children accounts/sections of the computed sections in step 1.
        3) It computes and add the final total line if line_id is not given
        :param options: options of the report
        :type options: dict
        :param line_id: the line id from which this method is called (when you unfold a line)
        :type line_id: str
        :return: list of dict representing the report lines
        :rtype: list
        """
        super_totals = None
        lines = []

        if line_id is None:
            # HANDLE ORPHAN ACCOUNTS
            level = 0
            orphan_totals, orphan_lines = self._handle_orphan_accounts(options, level, **kwargs)
            super_totals = [x + y for x, y in zip(super_totals, orphan_totals)] if super_totals is not None else orphan_totals
            lines += orphan_lines

            # FETCH ALL ROOT SECTIONS
            sections = self._get_root_sections(options, **kwargs)
        else:
            from_section = self.env['consolidation.group'].browse(int(line_id.split('-')[1]))
            level = len(from_section.parent_path.split('/'))
            # For convenience in the following
            sections = [from_section]

        # PROCESS COMPUTED SECTIONS
        if len(sections) > 0:
            section_totals, section_lines = self._handle_sections(sections, options, level, **kwargs)
            super_totals = [x + y for x, y in zip(super_totals, section_totals)] if super_totals is not None else section_totals
            lines += section_lines

        if line_id is None and super_totals:
            lines.append(self._build_total_line(super_totals, options, **kwargs))
        return lines

    def _handle_sections(self, sections, options: dict, level: int, **kwargs) -> tuple:
        """
        Handle the creation of given sections lines
        :param sections: a list or recordset of section objects
        :param options: options of the report
        :type options: dict
        :param level: the level of the line (to allow indentation to be kept)
        :type level: int
        :return: A couple (totals, lines) where :
            - totals the list of the column totals
            - lines the list of generated report line corresponding to given sections
        :rtype: tuple
        """
        all_totals = None
        lines = []
        for section in sections:
            section_totals, section_lines = self._build_section_line(section, level, options, **kwargs)
            # Handle TOTALS
            all_totals = [x + y for x, y in  zip(all_totals, section_totals)] if all_totals is not None else section_totals
            # Handle LINES
            if ShowZeroHandler.section_line_should_be_added(section_lines, options):
                lines += section_lines
        return all_totals, lines

    def _handle_orphan_accounts(self, options: dict, level: int = 1, **kwargs) -> tuple:
        """
        Handle the creation of all orphan account lines for given charts
        :param options: options of the report
        :type options: dict
        :param level: the level of the line (to allow indentation to be kept)
        :type level: int
        :return: A couple (totals, lines) where :
            - totals the list of the column totals
            - lines the list of generated report line corresponding to orphan accounts
        :rtype: tuple
        """
        orphan_accounts = self._get_orphan_accounts(options, **kwargs)
        return self._handle_accounts(orphan_accounts, options, level, **kwargs)

    def _handle_accounts(self, accounts, options: dict, level: int, **kwargs) -> tuple:
        """
        Handle the creation of report lines for given accounts
        :param accounts: a recordset containing all the accounts to handle
        :param options: options of the report
        :type options: dict
        :param level: the level of the line (to allow indentation to be kept)
        :type level: int
        :return: A couple (totals, lines) where :
            - totals the list of the column totals
            - lines the list of generated report line corresponding to given accounts
        :rtype: tuple
        """
        all_totals = None
        lines = []

        if accounts and len(accounts) > 0:
            for account in accounts:
                totals = self._compute_account_totals(account, **kwargs)

                if len(totals) > 0:
                    # Handle TOTALS
                    all_totals = [x + y for x, y in zip(all_totals, totals)] if all_totals is not None else totals

                    # Handle LINES
                    account_line = self._format_account_line(account, None, level, totals, options, **kwargs)

                    if self._account_line_is_shown(account_line, options):
                        lines.append(account_line)

        return all_totals, lines

    def _account_line_is_shown(self, account_line: dict, options: dict) -> bool:
        """
        Determine if an account line should be shown
        :param account_line: the account line
        :type account_line: dict
        :param options: options of the report
        :type options: dict
        :return: True if the account line should be shown, False otherwise
        :rtype: bool
        """
        return ShowZeroHandler.account_line_should_be_added(account_line, options)

    def _get_all_accounts(self, options: dict, **kwargs):
        """
        Get all consolidation accounts, filtered on given chart_ids if given in kwargs
        :param options: options of the report
        :type options: dict
        :return: a recordset of all accounts found
        """
        domain = []
        if kwargs.get('chart_ids', False):
            domain.append(('chart_id', 'in', kwargs['chart_ids']))
        return self.env['consolidation.account'].search(domain)

    def _get_root_sections(self, options: dict, **kwargs):
        """
        Get all root sections (= without parent), filtered on given chart_ids if given in kwargs
        :param options: options of the report
        :type options: dict
        :return: a recordset of all root sections found
        """
        domain = [('parent_id', '=', False)]
        if kwargs.get('chart_ids', False):
            domain.append(('chart_id', 'in', kwargs['chart_ids']))
        return self.env['consolidation.group'].search(domain)

    def _get_orphan_accounts(self, options: dict, **kwargs):
        """
        Get all orphan accounts (= not attached to a section) for given consolidation charts
        :param options: options of the report
        :type options: dict
        :return: a recordset of all orphan accounts found
        """
        domain = [('group_id', '=', False)]
        if kwargs.get('chart_ids', False):
            domain.append(('chart_id', 'in', kwargs['chart_ids']))
        return self.env['consolidation.account'].search(domain)

    def _compute_account_totals(self, account, **kwargs) -> list:
        """
        Compute the totals for a given consolidation account and given periods
        :param account_id: the id of the consolidation account
        :param periods: a recordset containing the periods
        :return: a list of float representing the totals for the account, first cell is for first column, second cell
        for second column, ...
        """
        return []

    def _format_account_line(self, account, parent_id, level: int, totals: list, options: dict, **kwargs) -> dict:
        """
        Build an account line.
        :param account: the account object
        :param level: the level of the line (to allow indentation to be kept)
        :type level: int
        :param totals: the already computed totals for the account
        :param options: options of the report
        :type options: dict
        :return: a formatted dict representing the account line
        :rtype: dict
        """
        # Columns
        cols = [{
            'name': self.value_formatter(total),
            'no_format': total,
            'figure_type': 'monetary',
            'class': 'number' + (' muted' if float_is_zero(total, 6) else ''),
            'is_zero': not total,
            'auditable': True,
        }
            for total in totals]
        # The last column 'total' must not be auditable
        cols[-1]['auditable'] = False

        report = self.env['account.report'].browse(options['report_id'])

        # Line
        name = account.display_name

        if account.group_id:
            account_line_id = report._get_generic_line_id(None, None, markup=f'{account.id}', parent_line_id=parent_id)
            account_line_parent_id = parent_id

        else:
            account_line_id = report._get_generic_line_id(None, None, markup=account.id)
            account_line_parent_id = None

        account_line = {
            'id': account_line_id,
            'name': len(name) > 40 and options['export_mode'] != 'print' and name[:40] + '...' or name,
            'title_hover': _("%s (%s Currency Conversion Method)") % (account.name, account.get_display_currency_mode()),
            'columns': cols,
            'level': level,
        }

        if account_line_parent_id:
            account_line['parent_id'] = account_line_parent_id

        return account_line

    def _build_section_line(self, section, level: int, options: dict, **kwargs) -> tuple:
        """
        Build a section line and all its descendants lines (if any).
        :param section: the section object
        :param level: the level of the line (to allow indentation to be kept)
        :type level: int
        :param options: options of the report
        :type options: dict
        :return: a tuple with :
        - a list of formatted dict containing the section line itself and all the descendant lines of this
        (so that the section line is the first dict of the list)
        - the totals of the section line
        :rtype: tuple
        """
        report = self.env['account.report'].browse(options['report_id'])
        if section.parent_id:
            section_parent_id = report._get_generic_line_id(None, None, markup=f'section_{section.parent_id.id}')
            section_id = report._get_generic_line_id(None, None, markup=f'section_{section.id}', parent_line_id=section_parent_id)
        else:
            section_parent_id = None
            section_id = report._get_generic_line_id(None, None, markup=f'section_{section.id}')

        section_line = {
            'id': section_id,
            'name': section.name,
            'level': level,
            'unfoldable': True,
            'unfolded': options.get('unfold_all', False) or section_id in options.get('unfolded_lines', []),
        }

        if section_parent_id:
            section_line['parent_id'] = section_parent_id

        lines = [section_line]

        if not level:
            level += 1

        # HANDLE CHILDREN
        section_totals = None

        if len(section.child_ids) > 0:
            for child_section in section.child_ids:
                # This will return the section line THEN all subsequent lines
                child_totals, descendant_lines = self._build_section_line(child_section, level + 2, options, **kwargs)
                section_totals = [x + y for x, y in zip(section_totals, child_totals)] if section_totals is not None else child_totals

                if ShowZeroHandler.section_line_should_be_added(descendant_lines, options):
                    lines += descendant_lines

        # HANDLE ACCOUNTS
        if len(section.account_ids) > 0:
            for child_account in section.account_ids:
                account_totals = self._compute_account_totals(child_account, **kwargs)
                account_line = self._format_account_line(child_account, section_id, level + 2, account_totals, options, **kwargs)
                section_totals = [x + y for x, y in zip(section_totals, account_totals)] if section_totals is not None else account_totals

                if ShowZeroHandler.account_line_should_be_added(account_line, options):
                    lines.append(account_line)

        if section_totals is None:
            section_totals = self._get_default_line_totals(options, **kwargs)

        section_line['columns'] = [{
            'name': self.value_formatter(total),
            'no_format': total,
            'figure_type': 'monetary',
            'is_zero': not total,
            'class': 'number' + (' muted' if float_is_zero(total, 6) else ''),
        } for total in section_totals]

        return section_totals, lines

    def _build_total_line(self, totals: list, options: dict, **kwargs) -> dict:
        """
        Build the total line, based on given totals list. Values are formatted using self value formatter.
        :param totals: the list of totals amounts
        :type totals: list
        :param options: options of the report
        :type options: dict
        :return: a formatted dict representing the total line to be displayed on report
        :rtype: dict
        """
        cols = [{
            'name': self.value_formatter(total), 'no_format': total,
            'class': 'number' + (' text-danger' if not float_is_zero(total, 6) else ''),
            'figure_type': 'monetary',
        } for total in totals]

        report = self.env['account.report'].browse(options['report_id'])

        return {
            'id': report._get_generic_line_id(None, None, markup='grouped_accounts_total'),
            'name': _('Total'),
            'class': 'total',
            'columns': cols,
            'level': 0,
        }

    def _get_default_line_totals(self, options: dict, **kwargs) -> list:
        """
        Create a line with default values, this is called when no values have been found to create a line.
        :param options: options of the report
        :type options: dict
        :return: a list of float representing the default values of a line
        :rtype: list
        """
        return []
