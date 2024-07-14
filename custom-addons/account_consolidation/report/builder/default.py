from .abstract import AbstractBuilder


class DefaultBuilder(AbstractBuilder):
    def __init__(self, env, value_formatter, journals):
        """
        Instantiate the default builder which is used when only one period is selected. It handles the filtering based
        on this section journals.
        :param env: the env object in which this builder is used
        :param value_formatter: a function that will be used to format float values in report
        :param journals: a recordset containing the journals to use in this builder
        """
        super().__init__(env, value_formatter)
        self.journals = journals

    def _get_params(self, period_ids: list, options: dict, line_id: str = None) -> dict:
        chart_ids = self.env['consolidation.chart'].search([('period_ids', 'in', period_ids)]).ids

        cols_amount = len(self.journals) + 1
        params = super()._get_params(period_ids, options, line_id)
        params.update({
            'chart_ids': chart_ids,
            'cols_amount': cols_amount
        })
        return params

    def _compute_account_totals(self, account, **kwargs) -> list:
        totals = []
        line_total = 0
        JournalLine = self.env['consolidation.journal.line']

        # Computing columns
        for journal in self.journals:
            # Check if a journal line exists
            domain = [('account_id', '=', account.id), ('journal_id', '=', journal.id)]
            groupby_res = JournalLine._read_group(domain, [], ['amount:sum'])
            journal_total_balance = groupby_res[0][0]
            journal_total_balance *= account.sign
            # Update totals
            totals.append(journal_total_balance)
            line_total += journal_total_balance

        totals.append(line_total)
        return totals

    def _format_account_line(self, account, parent_id, level: int, totals: list, options: dict, **kwargs) -> dict:
        line = super()._format_account_line(account, parent_id, level, totals, options, **kwargs)
        for col, journal in zip(line['columns'], self.journals):
            domain = [('account_id', '=', account.id), ('journal_id', '=', journal.id)]
            journal_lines_amount = self.env['consolidation.journal.line'].search_count(domain)
            if journal_lines_amount > 0:
                col['journal_id'] = journal.id if journal.company_period_id else False
        return line

    def _get_default_line_totals(self, options: dict, **kwargs) -> list:
        return kwargs.get('cols_amount', len(self.journals) if self.journals else 0) * [0.0]
