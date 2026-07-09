# -*- coding: utf-8 -*-

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from itertools import groupby
from time import perf_counter

from odoo import SUPERUSER_ID, api, models, sql_db
from odoo.modules.registry import Registry
from odoo.tools import SQL, float_round


_tax_details_snapshot_worker_initialized = set()


def _process_tax_details_snapshot_worker(dbname, uid, context, domain, fallback):
    if dbname not in _tax_details_snapshot_worker_initialized:
        sql_db.close_db(dbname)
        Registry.delete(dbname)
        _tax_details_snapshot_worker_initialized.add(dbname)
    with Registry(dbname).cursor() as cr:
        env = api.Environment(cr, uid, context)
        start = perf_counter()
        rows = env['account.move.line']._get_python_tax_details_from_snapshot_domain(domain, fallback=fallback)
        return {
            'rows': rows,
            'elapsed': perf_counter() - start,
            'row_count': len(rows),
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_query_tax_details_from_domain(self, domain, fallback=True, use_simplified_query=False) -> SQL:
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param domain:      An orm domain on account.move.line.
        :param fallback:    Fallback on an approximated mapping if the mapping failed.
        :return:            query as SQL object
        """
        query = self.env['account.move.line']._search(domain)
        if use_simplified_query:
            return self._get_query_tax_details_simplified(query.from_clause, query.where_clause)
        return self._get_query_tax_details(query.from_clause, query.where_clause, fallback=fallback)

    @api.model
    def _get_extra_query_base_tax_line_mapping(self) -> SQL:
        #TO OVERRIDE
        return SQL()

    @api.model
    def _is_python_base_tax_line_mapping_allowed(self, base_line, tax_line):
        """Python counterpart of _get_extra_query_base_tax_line_mapping."""
        return True

    @api.model
    def _get_python_tax_details_from_domain(self, domain, fallback=True, use_simplified_query=False):
        """Return tax details rows using a Python implementation of the SQL query.

        This helper keeps the account.move.line domain as the entry point, then
        groups the selected lines by move so the tax/base-line matching logic is
        readable and easy to compare with the SQL query.
        """
        selected_lines = self.search(domain, order='move_id, id')
        tax_details = []
        for _move_id, lines_iter in groupby(selected_lines, key=lambda line: line.move_id.id):
            move_lines = self.browse([line.id for line in lines_iter])
            if use_simplified_query:
                tax_details += self._get_python_tax_details_simplified(move_lines)
            else:
                tax_details += self._get_python_tax_details(move_lines, fallback=fallback)
        return tax_details

    @api.model
    def _get_python_tax_details_from_snapshot_domain(self, domain, fallback=True):
        query = self.env['account.move.line']._search(domain)
        return self._get_python_tax_details_from_snapshot_query(query.from_clause, query.where_clause, fallback=fallback)

    @api.model
    def _get_python_tax_details_from_snapshot_domain_parallel(self, domain, fallback=True, batch_size=100, max_workers=4):
        move_ids = self.search(domain, order='move_id').move_id.ids
        if not move_ids:
            return [], []

        batches = [
            move_ids[index:index + batch_size]
            for index in range(0, len(move_ids), batch_size)
        ]
        context = {
            key: value
            for key, value in self.env.context.items()
            if key in ('allowed_company_ids', 'lang', 'tz')
        }
        uid = self.env.uid or SUPERUSER_ID
        dbname = self.env.cr.dbname
        worker_args = [
            (dbname, uid, context, domain + [('move_id', 'in', batch)], fallback)
            for batch in batches
        ]

        rows = []
        timings = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(_process_tax_details_snapshot_worker, *zip(*worker_args)):
                rows.extend(result['rows'])
                timings.append({
                    'elapsed': result['elapsed'],
                    'row_count': result['row_count'],
                })
        return sorted(rows, key=lambda row: (row['tax_line_id'], row['base_line_id'], row['src_line_id'])), timings

    @api.model
    def _get_python_tax_details_snapshot(self, table_references, search_condition):
        self.env.cr.execute(SQL(
            '''
            WITH selected_lines AS MATERIALIZED (
                SELECT account_move_line.id, account_move_line.move_id
                  FROM %(table_references)s
                 WHERE %(search_condition)s
            ),
            selected_moves AS MATERIALIZED (
                SELECT DISTINCT move_id
                  FROM selected_lines
            ),
            selected_move_lines AS MATERIALIZED (
                SELECT
                    aml.id,
                    aml.move_id,
                    aml.display_type,
                    aml.tax_repartition_line_id,
                    aml.tax_line_id,
                    aml.group_tax_id,
                    aml.balance,
                    aml.amount_currency,
                    aml.quantity,
                    aml.account_id,
                    aml.partner_id,
                    aml.currency_id,
                    aml.company_currency_id,
                    aml.analytic_distribution,
                    move.move_type,
                    move.tax_cash_basis_rec_id,
                    move.always_tax_exigible,
                    aml.id IN (SELECT id FROM selected_lines) AS selected,
                    COALESCE(
                        ARRAY_AGG(tax_rel.account_tax_id ORDER BY tax.sequence, tax_rel.account_tax_id)
                        FILTER (WHERE tax_rel.account_tax_id IS NOT NULL),
                        ARRAY[]::integer[]
                    ) AS tax_ids
                FROM account_move_line aml
                JOIN selected_moves selected_move ON selected_move.move_id = aml.move_id
                JOIN account_move move ON move.id = aml.move_id
                LEFT JOIN account_move_line_account_tax_rel tax_rel ON tax_rel.account_move_line_id = aml.id
                LEFT JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                GROUP BY aml.id, move.id
            ),
            referenced_taxes AS MATERIALIZED (
                SELECT DISTINCT tax_id
                  FROM (
                    SELECT tax_line_id AS tax_id FROM selected_move_lines WHERE tax_line_id IS NOT NULL
                    UNION ALL
                    SELECT group_tax_id AS tax_id FROM selected_move_lines WHERE group_tax_id IS NOT NULL
                    UNION ALL
                    SELECT UNNEST(tax_ids) AS tax_id FROM selected_move_lines
                  ) sub
            ),
            referenced_taxes_with_children AS MATERIALIZED (
                SELECT tax_id FROM referenced_taxes
                UNION
                SELECT rel.child_tax
                  FROM referenced_taxes
                  JOIN account_tax_filiation_rel rel ON rel.parent_tax = referenced_taxes.tax_id
            )
            SELECT
                'line' AS row_type,
                to_jsonb(selected_move_lines.*) AS payload
              FROM selected_move_lines
            UNION ALL
            SELECT
                'tax' AS row_type,
                jsonb_build_object(
                    'id', tax.id,
                    'sequence', tax.sequence,
                    'amount', tax.amount,
                    'amount_type', tax.amount_type,
                    'is_base_affected', tax.is_base_affected,
                    'include_base_amount', tax.include_base_amount,
                    'tax_exigibility', tax.tax_exigibility,
                    'cash_basis_transition_account_id', tax.cash_basis_transition_account_id,
                    'analytic', tax.analytic,
                    'children_tax_ids', COALESCE(children.children_tax_ids, ARRAY[]::integer[])
                ) AS payload
              FROM account_tax tax
              JOIN referenced_taxes_with_children ref ON ref.tax_id = tax.id
         LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(rel.child_tax ORDER BY child.sequence, rel.child_tax) AS children_tax_ids
                  FROM account_tax_filiation_rel rel
                  JOIN account_tax child ON child.id = rel.child_tax
                 WHERE rel.parent_tax = tax.id
              ) children ON TRUE
            UNION ALL
            SELECT
                'tax_rep' AS row_type,
                jsonb_build_object(
                    'id', tax_rep.id,
                    'tax_id', tax_rep.tax_id,
                    'account_id', tax_rep.account_id,
                    'factor_percent', tax_rep.factor_percent,
                    'use_in_tax_closing', tax_rep.use_in_tax_closing
                ) AS payload
              FROM account_tax_repartition_line tax_rep
              JOIN selected_move_lines line ON line.tax_repartition_line_id = tax_rep.id
            UNION ALL
            SELECT
                'currency' AS row_type,
                jsonb_build_object(
                    'id', currency.id,
                    'decimal_places', currency.decimal_places
                ) AS payload
              FROM res_currency currency
             WHERE currency.id IN (
                    SELECT currency_id FROM selected_move_lines
                    UNION
                    SELECT company_currency_id FROM selected_move_lines
                )
            ORDER BY row_type
            ''',
            table_references=table_references,
            search_condition=search_condition,
        ))

        snapshot = {
            'lines_by_move_id': defaultdict(list),
            'taxes': {},
            'tax_reps': {},
            'currencies': {},
        }
        for row in self.env.cr.dictfetchall():
            payload = row['payload']
            if row['row_type'] == 'line':
                snapshot['lines_by_move_id'][payload['move_id']].append(payload)
            elif row['row_type'] == 'tax':
                snapshot['taxes'][payload['id']] = payload
            elif row['row_type'] == 'tax_rep':
                snapshot['tax_reps'][payload['id']] = payload
            elif row['row_type'] == 'currency':
                snapshot['currencies'][payload['id']] = payload

        for lines in snapshot['lines_by_move_id'].values():
            lines.sort(key=lambda line: line['id'])
        return snapshot

    @api.model
    def _get_python_tax_details_from_snapshot_query(self, table_references, search_condition, fallback=True):
        snapshot = self._get_python_tax_details_snapshot(table_references, search_condition)
        tax_details = []
        for move_id in sorted(snapshot['lines_by_move_id']):
            tax_details += self._get_python_tax_details_from_snapshot_move(snapshot, snapshot['lines_by_move_id'][move_id], fallback=fallback)
        return tax_details

    @api.model
    def _get_python_tax_details_from_snapshot_move(self, snapshot, move_lines, fallback=True):
        def sign(value):
            return (value > 0) - (value < 0)

        def is_null(value):
            return value is None or value is False

        def round_digits(value, precision_digits):
            return float_round(value, precision_digits=precision_digits) if value else 0.0

        def prorata_amount(cumulated_amount, total_amount, amount_to_dispatch, precision_digits):
            if not total_amount:
                return 0.0
            return round_digits(
                sign(cumulated_amount) * amount_to_dispatch * abs(cumulated_amount) / total_amount,
                precision_digits,
            )

        def base_value(base_line, amount, tax):
            if tax['amount_type'] == 'fixed':
                return sign(amount) * abs(base_line['quantity'] or 1.0)
            return amount

        def flattened_base_affected_tax_ids(line):
            tax_ids = []
            for tax_id in line['tax_ids']:
                tax = snapshot['taxes'][tax_id]
                if not tax['is_base_affected']:
                    continue
                flattened_tax_ids = tax['children_tax_ids'] if tax['amount_type'] == 'group' else [tax_id]
                tax_ids += [
                    (snapshot['taxes'][flattened_tax_id]['sequence'], flattened_tax_id)
                    for flattened_tax_id in flattened_tax_ids
                ]
            return [tax_id for _sequence, tax_id in sorted(tax_ids)]

        def line_matches_mapping(base_line, tax_line):
            tax = snapshot['taxes'][tax_line['tax_line_id']]
            tax_rep = snapshot['tax_reps'][tax_line['tax_repartition_line_id']]
            effective_tax_id = tax_line['group_tax_id'] or tax['id']
            is_cash_basis_transition = tax['tax_exigibility'] == 'on_payment' and tax['cash_basis_transition_account_id']
            return not (
                base_line['tax_repartition_line_id']
                or effective_tax_id not in base_line['tax_ids']
                or base_line['move_id'] != tax_line['move_id']
                or (
                    base_line['move_type'] == 'entry'
                    and not is_cash_basis_transition
                    and sign(tax_line['balance']) != sign(base_line['balance'] * tax['amount'] * tax_rep['factor_percent'])
                )
                or base_line['partner_id'] != tax_line['partner_id']
                or base_line['currency_id'] != tax_line['currency_id']
                or (
                    (tax_rep['account_id'] or base_line['account_id']) != tax_line['account_id']
                    and not is_cash_basis_transition
                )
                or not (
                    (not tax['analytic'] and tax_rep['use_in_tax_closing'])
                    or (is_null(base_line['analytic_distribution']) and is_null(tax_line['analytic_distribution']))
                    or base_line['analytic_distribution'] == tax_line['analytic_distribution']
                )
            )

        def build_base_tax_line_mapping():
            mapping_rows = []
            for tax_line in [line for line in move_lines if line['selected'] and line['tax_repartition_line_id']]:
                tax = snapshot['taxes'][tax_line['tax_line_id']]
                tax_line_tax_ids = flattened_base_affected_tax_ids(tax_line)
                for base_line in move_lines:
                    if not line_matches_mapping(base_line, tax_line):
                        continue
                    if tax['include_base_amount']:
                        expected_tax_ids = [tax['id']] + tax_line_tax_ids
                        if flattened_base_affected_tax_ids(base_line)[-len(expected_tax_ids):] != expected_tax_ids:
                            continue
                    mapping_rows.append({
                        'tax_line': tax_line,
                        'base_line': base_line,
                        'base_amount': base_line['balance'],
                        'base_amount_currency': base_line['amount_currency'],
                    })
            return mapping_rows

        def add_fallback_rows(mapping_rows):
            if not fallback:
                return mapping_rows

            mapped_tax_line_ids = {row['tax_line']['id'] for row in mapping_rows}
            fallback_rows = []
            for tax_line in [line for line in move_lines if line['selected'] and line['tax_repartition_line_id']]:
                if tax_line['id'] in mapped_tax_line_ids:
                    continue
                effective_tax_id = tax_line['group_tax_id'] or tax_line['tax_line_id']
                for base_line in move_lines:
                    if (
                        base_line['tax_repartition_line_id']
                        or base_line['move_id'] != tax_line['move_id']
                        or base_line['currency_id'] != tax_line['currency_id']
                        or effective_tax_id not in base_line['tax_ids']
                    ):
                        continue
                    fallback_rows.append({
                        'tax_line': tax_line,
                        'base_line': base_line,
                        'base_amount': base_line['balance'],
                        'base_amount_currency': base_line['amount_currency'],
                    })
            return mapping_rows + fallback_rows

        def dispatch_affecting_base_amounts(mapping_rows):
            rows = []
            rows_by_tax_line_id = defaultdict(list)
            rows_by_base_line_id = defaultdict(list)
            for row in mapping_rows:
                rows_by_tax_line_id[row['tax_line']['id']].append(row)
                rows_by_base_line_id[row['base_line']['id']].append(row)

            grouped_dispatch_rows = defaultdict(list)
            source_tax_lines = [
                line
                for line in move_lines
                if line['selected']
                and line['tax_repartition_line_id']
                and snapshot['taxes'][line['tax_line_id']]['include_base_amount']
            ]
            for source_tax_line in source_tax_lines:
                for source_row in rows_by_tax_line_id[source_tax_line['id']]:
                    base_line = source_row['base_line']
                    for affected_tax_id in source_tax_line['tax_ids']:
                        for matching_row in rows_by_base_line_id[base_line['id']]:
                            target_tax_line = matching_row['tax_line']
                            if target_tax_line['tax_line_id'] != affected_tax_id:
                                continue
                            grouped_dispatch_rows[(target_tax_line['id'], source_tax_line['id'])].append({
                                'tax_line': target_tax_line,
                                'base_line': base_line,
                                'src_line': source_tax_line,
                                'tax': snapshot['taxes'][affected_tax_id],
                                'base_amount': base_line['balance'],
                                'base_amount_currency': base_line['amount_currency'],
                                'total_tax_amount': source_tax_line['balance'],
                                'total_tax_amount_currency': source_tax_line['amount_currency'],
                            })

            for dispatch_rows in grouped_dispatch_rows.values():
                dispatch_rows.sort(key=lambda row: (row['tax']['id'], row['base_line']['id']))
                total_base_amount = sum(
                    base_value(row['base_line'], row['base_amount'], row['tax'])
                    for row in dispatch_rows
                )
                total_base_amount_currency = sum(
                    base_value(row['base_line'], row['base_amount_currency'], row['tax'])
                    for row in dispatch_rows
                )
                cumulated_base_amount = cumulated_base_amount_currency = 0.0
                previous_base_amount = previous_base_amount_currency = 0.0
                for row in dispatch_rows:
                    tax_line = row['tax_line']
                    base_line = row['base_line']
                    tax = row['tax']
                    cumulated_base_amount += base_value(base_line, row['base_amount'], tax)
                    cumulated_base_amount_currency += base_value(base_line, row['base_amount_currency'], tax)
                    base_amount = prorata_amount(
                        cumulated_base_amount,
                        total_base_amount,
                        row['total_tax_amount'],
                        snapshot['currencies'][tax_line['company_currency_id']]['decimal_places'],
                    )
                    base_amount_currency = prorata_amount(
                        cumulated_base_amount_currency,
                        total_base_amount_currency,
                        row['total_tax_amount_currency'],
                        snapshot['currencies'][tax_line['currency_id']]['decimal_places'],
                    )
                    rows.append({
                        'tax_line': tax_line,
                        'base_line': base_line,
                        'src_line': row['src_line'],
                        'base_amount': base_amount - previous_base_amount,
                        'base_amount_currency': base_amount_currency - previous_base_amount_currency,
                    })
                    previous_base_amount = base_amount
                    previous_base_amount_currency = base_amount_currency
            return rows

        base_tax_line_mapping = build_base_tax_line_mapping()
        base_tax_matching_base_amounts = [
            {
                **row,
                'src_line': row['base_line'],
            }
            for row in add_fallback_rows(base_tax_line_mapping)
        ]
        base_tax_matching_base_amounts += dispatch_affecting_base_amounts(base_tax_line_mapping)

        grouped_rows = defaultdict(list)
        for row in base_tax_matching_base_amounts:
            grouped_rows[row['tax_line']['id']].append(row)

        results = []
        for tax_line_id in sorted(grouped_rows):
            rows = sorted(
                grouped_rows[tax_line_id],
                key=lambda row: (row['tax_line']['tax_line_id'], row['base_line']['id'], row['src_line']['id']),
            )
            tax_line = rows[0]['tax_line']
            tax = snapshot['taxes'][tax_line['tax_line_id']]
            total_base_amount = sum(base_value(row['base_line'], row['base_amount'], tax) for row in rows)
            total_base_amount_currency = sum(
                base_value(row['base_line'], row['base_amount_currency'], tax)
                for row in rows
            )
            cumulated_base_amount = cumulated_base_amount_currency = 0.0
            previous_tax_amount = previous_tax_amount_currency = 0.0
            for row in rows:
                base_line = row['base_line']
                src_line = row['src_line']
                cumulated_base_amount += base_value(base_line, row['base_amount'], tax)
                cumulated_base_amount_currency += base_value(base_line, row['base_amount_currency'], tax)
                tax_amount = prorata_amount(
                    cumulated_base_amount,
                    total_base_amount,
                    tax_line['balance'],
                    snapshot['currencies'][tax_line['company_currency_id']]['decimal_places'],
                )
                tax_amount_currency = prorata_amount(
                    cumulated_base_amount_currency,
                    total_base_amount_currency,
                    tax_line['amount_currency'],
                    snapshot['currencies'][tax_line['currency_id']]['decimal_places'],
                )
                results.append({
                    'id': f"{tax_line['id']}-{base_line['id']}-{src_line['id']}",
                    'base_line_id': base_line['id'],
                    'tax_line_id': tax_line['id'],
                    'display_type': tax_line['display_type'],
                    'src_line_id': src_line['id'],
                    'tax_id': tax['id'],
                    'group_tax_id': tax_line['group_tax_id'] or None,
                    'tax_exigible': (
                        True
                        if (
                            tax['tax_exigibility'] != 'on_payment'
                            or tax_line['tax_cash_basis_rec_id']
                            or tax_line['always_tax_exigible']
                        )
                        else None
                    ),
                    'base_account_id': base_line['account_id'],
                    'tax_repartition_line_id': tax_line['tax_repartition_line_id'],
                    'base_amount': row['base_amount'],
                    'tax_amount': tax_amount - previous_tax_amount,
                    'base_amount_currency': row['base_amount_currency'],
                    'tax_amount_currency': tax_amount_currency - previous_tax_amount_currency,
                })
                previous_tax_amount = tax_amount
                previous_tax_amount_currency = tax_amount_currency
        return results

    def _get_python_tax_details_simplified(self, filtered_lines):
        def sign(value):
            return (value > 0) - (value < 0)

        def is_null(value):
            return value is None or value is False

        rows_by_tax = defaultdict(list)
        base_lines = filtered_lines.filtered(lambda line: not line.tax_repartition_line_id)
        tax_lines = filtered_lines.filtered('tax_repartition_line_id')

        for base_line in base_lines:
            for applied_tax in base_line.tax_ids:
                for tax_line in tax_lines:
                    tax_rep = tax_line.tax_repartition_line_id
                    effective_tax = tax_line.group_tax_id or tax_line.tax_line_id
                    is_cash_basis_transition = (
                        applied_tax.tax_exigibility == 'on_payment'
                        and applied_tax.cash_basis_transition_account_id
                    )
                    if (
                        tax_line.currency_id != base_line.currency_id
                        or tax_line.partner_id != base_line.partner_id
                        or effective_tax != applied_tax
                        or (
                            base_line.move_id.move_type == 'entry'
                            and not is_cash_basis_transition
                            and sign(base_line.balance) != sign(
                                tax_line.balance * applied_tax.amount * tax_rep.factor_percent
                            )
                        )
                        or (
                            (tax_rep.account_id or base_line.account_id) != tax_line.account_id
                            and not is_cash_basis_transition
                        )
                        or not (
                            (not applied_tax.analytic and tax_rep.use_in_tax_closing)
                            or (is_null(base_line.analytic_distribution) and is_null(tax_line.analytic_distribution))
                            or base_line.analytic_distribution == tax_line.analytic_distribution
                        )
                    ):
                        continue

                    rows_by_tax[(tax_line.id, applied_tax.id)].append({
                        'move_id': base_line.move_id.id,
                        'tax_line_id': tax_line.id,
                        'base_line_id': base_line.id,
                        'tax_id': applied_tax.id,
                        'sequence': applied_tax.sequence,
                        'base_value': base_line.balance if applied_tax.amount_type != 'fixed' else base_line.quantity,
                        'tax_amount': tax_line.balance,
                    })

        results = []
        for rows in rows_by_tax.values():
            rows.sort(key=lambda row: (row['sequence'], row['base_line_id']))
            total_base = sum(row['base_value'] for row in rows)
            previous_tax_amount = 0.0
            base_cumul = 0.0
            for row in rows:
                base_cumul += row['base_value']
                if total_base:
                    tax_amount = float_round(
                        row['tax_amount'] * base_cumul / total_base,
                        precision_digits=2,
                    )
                else:
                    tax_amount = None
                results.append({
                    'move_id': row['move_id'],
                    'tax_line_id': row['tax_line_id'],
                    'base_line_id': row['base_line_id'],
                    'tax_amount': tax_amount - previous_tax_amount if tax_amount is not None else None,
                })
                if tax_amount is not None:
                    previous_tax_amount = tax_amount
        return sorted(results, key=lambda row: (row['tax_line_id'], row['base_line_id']))

    def _get_python_tax_details(self, filtered_lines, fallback=True):
        def sign(value):
            return (value > 0) - (value < 0)

        def is_null(value):
            return value is None or value is False

        def round_digits(value, precision_digits):
            return float_round(value, precision_digits=precision_digits) if value else 0.0

        def prorata_amount(cumulated_amount, total_amount, amount_to_dispatch, precision_digits):
            if not total_amount:
                return 0.0
            return round_digits(
                sign(cumulated_amount) * amount_to_dispatch * abs(cumulated_amount) / total_amount,
                precision_digits,
            )

        def base_value(base_line, amount, tax):
            if tax.amount_type == 'fixed':
                return sign(amount) * abs(base_line.quantity or 1.0)
            return amount

        def flattened_base_affected_tax_ids(line):
            tax_ids = []
            for tax in line.tax_ids:
                if not tax.is_base_affected:
                    continue
                flattened_taxes = tax.children_tax_ids if tax.amount_type == 'group' else tax
                tax_ids += [(tax.sequence, flattened_tax.id) for flattened_tax in flattened_taxes]
            return [tax_id for _sequence, tax_id in sorted(tax_ids)]

        def build_base_tax_line_mapping():
            mapping_rows = []
            for tax_line in filtered_lines.filtered('tax_repartition_line_id'):
                tax = tax_line.tax_line_id
                tax_rep = tax_line.tax_repartition_line_id
                effective_tax = tax_line.group_tax_id or tax
                tax_line_tax_ids = flattened_base_affected_tax_ids(tax_line)
                is_cash_basis_transition = tax.tax_exigibility == 'on_payment' and tax.cash_basis_transition_account_id

                for base_line in tax_line.move_id.line_ids:
                    if (
                        base_line.tax_repartition_line_id
                        or effective_tax not in base_line.tax_ids
                        or base_line.move_id != tax_line.move_id
                        or (
                            base_line.move_id.move_type == 'entry'
                            and not is_cash_basis_transition
                            and sign(tax_line.balance) != sign(base_line.balance * tax.amount * tax_rep.factor_percent)
                        )
                        or base_line.partner_id != tax_line.partner_id
                        or base_line.currency_id != tax_line.currency_id
                        or (
                            (tax_rep.account_id or base_line.account_id) != tax_line.account_id
                            and not is_cash_basis_transition
                        )
                        or not (
                            (not tax.analytic and tax_rep.use_in_tax_closing)
                            or (is_null(base_line.analytic_distribution) and is_null(tax_line.analytic_distribution))
                            or base_line.analytic_distribution == tax_line.analytic_distribution
                        )
                        or not self._is_python_base_tax_line_mapping_allowed(base_line, tax_line)
                    ):
                        continue

                    if tax.include_base_amount:
                        expected_tax_ids = [tax.id] + tax_line_tax_ids
                        if flattened_base_affected_tax_ids(base_line)[-len(expected_tax_ids):] != expected_tax_ids:
                            continue

                    mapping_rows.append({
                        'tax_line': tax_line,
                        'base_line': base_line,
                        'base_amount': base_line.balance,
                        'base_amount_currency': base_line.amount_currency,
                    })
            return mapping_rows

        def add_fallback_rows(mapping_rows):
            if not fallback:
                return mapping_rows

            mapped_tax_line_ids = {row['tax_line'].id for row in mapping_rows}
            fallback_rows = []
            for tax_line in filtered_lines.filtered('tax_repartition_line_id'):
                if tax_line.id in mapped_tax_line_ids:
                    continue

                effective_tax = tax_line.group_tax_id or tax_line.tax_line_id
                for base_line in tax_line.move_id.line_ids:
                    if (
                        base_line.tax_repartition_line_id
                        or base_line.move_id != tax_line.move_id
                        or base_line.currency_id != tax_line.currency_id
                        or effective_tax not in base_line.tax_ids
                    ):
                        continue
                    fallback_rows.append({
                        'tax_line': tax_line,
                        'base_line': base_line,
                        'base_amount': base_line.balance,
                        'base_amount_currency': base_line.amount_currency,
                    })
            return mapping_rows + fallback_rows

        def dispatch_affecting_base_amounts(mapping_rows):
            rows = []
            rows_by_tax_line_id = defaultdict(list)
            rows_by_base_line_id = defaultdict(list)
            for row in mapping_rows:
                rows_by_tax_line_id[row['tax_line'].id].append(row)
                rows_by_base_line_id[row['base_line'].id].append(row)

            grouped_dispatch_rows = defaultdict(list)
            source_tax_lines = filtered_lines.filtered(
                lambda line: line.tax_repartition_line_id and line.tax_line_id.include_base_amount
            )
            for source_tax_line in source_tax_lines:
                for source_row in rows_by_tax_line_id[source_tax_line.id]:
                    base_line = source_row['base_line']
                    for affected_tax in source_tax_line.tax_ids:
                        for matching_row in rows_by_base_line_id[base_line.id]:
                            target_tax_line = matching_row['tax_line']
                            if target_tax_line.tax_line_id != affected_tax:
                                continue
                            grouped_dispatch_rows[(target_tax_line.id, source_tax_line.id)].append({
                                'tax_line': target_tax_line,
                                'base_line': base_line,
                                'src_line': source_tax_line,
                                'tax': affected_tax,
                                'base_amount': base_line.balance,
                                'base_amount_currency': base_line.amount_currency,
                                'total_tax_amount': source_tax_line.balance,
                                'total_tax_amount_currency': source_tax_line.amount_currency,
                            })

            for dispatch_rows in grouped_dispatch_rows.values():
                dispatch_rows.sort(key=lambda row: (row['tax'].id, row['base_line'].id))
                total_base_amount = sum(
                    base_value(row['base_line'], row['base_amount'], row['tax'])
                    for row in dispatch_rows
                )
                total_base_amount_currency = sum(
                    base_value(row['base_line'], row['base_amount_currency'], row['tax'])
                    for row in dispatch_rows
                )
                cumulated_base_amount = cumulated_base_amount_currency = 0.0
                previous_base_amount = previous_base_amount_currency = 0.0
                for row in dispatch_rows:
                    tax_line = row['tax_line']
                    base_line = row['base_line']
                    tax = row['tax']
                    cumulated_base_amount += base_value(base_line, row['base_amount'], tax)
                    cumulated_base_amount_currency += base_value(base_line, row['base_amount_currency'], tax)
                    base_amount = prorata_amount(
                        cumulated_base_amount,
                        total_base_amount,
                        row['total_tax_amount'],
                        tax_line.company_currency_id.decimal_places,
                    )
                    base_amount_currency = prorata_amount(
                        cumulated_base_amount_currency,
                        total_base_amount_currency,
                        row['total_tax_amount_currency'],
                        tax_line.currency_id.decimal_places,
                    )
                    rows.append({
                        'tax_line': tax_line,
                        'base_line': base_line,
                        'src_line': row['src_line'],
                        'base_amount': base_amount - previous_base_amount,
                        'base_amount_currency': base_amount_currency - previous_base_amount_currency,
                    })
                    previous_base_amount = base_amount
                    previous_base_amount_currency = base_amount_currency
            return rows

        base_tax_line_mapping = build_base_tax_line_mapping()
        base_tax_matching_base_amounts = [
            {
                **row,
                'src_line': row['base_line'],
            }
            for row in add_fallback_rows(base_tax_line_mapping)
        ]
        base_tax_matching_base_amounts += dispatch_affecting_base_amounts(base_tax_line_mapping)

        grouped_rows = defaultdict(list)
        for row in base_tax_matching_base_amounts:
            grouped_rows[row['tax_line'].id].append(row)

        results = []
        for tax_line_id in sorted(grouped_rows):
            rows = sorted(
                grouped_rows[tax_line_id],
                key=lambda row: (row['tax_line'].tax_line_id.id, row['base_line'].id, row['src_line'].id),
            )
            tax_line = rows[0]['tax_line']
            tax = tax_line.tax_line_id
            total_base_amount = sum(base_value(row['base_line'], row['base_amount'], tax) for row in rows)
            total_base_amount_currency = sum(
                base_value(row['base_line'], row['base_amount_currency'], tax)
                for row in rows
            )
            cumulated_base_amount = cumulated_base_amount_currency = 0.0
            previous_tax_amount = previous_tax_amount_currency = 0.0
            for row in rows:
                base_line = row['base_line']
                src_line = row['src_line']
                cumulated_base_amount += base_value(base_line, row['base_amount'], tax)
                cumulated_base_amount_currency += base_value(base_line, row['base_amount_currency'], tax)
                tax_amount = prorata_amount(
                    cumulated_base_amount,
                    total_base_amount,
                    tax_line.balance,
                    tax_line.company_currency_id.decimal_places,
                )
                tax_amount_currency = prorata_amount(
                    cumulated_base_amount_currency,
                    total_base_amount_currency,
                    tax_line.amount_currency,
                    tax_line.currency_id.decimal_places,
                )
                results.append({
                    'id': f'{tax_line.id}-{base_line.id}-{src_line.id}',
                    'base_line_id': base_line.id,
                    'tax_line_id': tax_line.id,
                    'display_type': tax_line.display_type,
                    'src_line_id': src_line.id,
                    'tax_id': tax.id,
                    'group_tax_id': tax_line.group_tax_id.id or None,
                    'tax_exigible': (
                        True
                        if (
                            tax.tax_exigibility != 'on_payment'
                            or tax_line.move_id.tax_cash_basis_rec_id
                            or tax_line.move_id.always_tax_exigible
                        )
                        else None
                    ),
                    'base_account_id': base_line.account_id.id,
                    'tax_repartition_line_id': tax_line.tax_repartition_line_id.id,
                    'base_amount': row['base_amount'],
                    'tax_amount': tax_amount - previous_tax_amount,
                    'base_amount_currency': row['base_amount_currency'],
                    'tax_amount_currency': tax_amount_currency - previous_tax_amount_currency,
                })
                previous_tax_amount = tax_amount
                previous_tax_amount_currency = tax_amount_currency
        return results

    def _get_query_tax_details_simplified(self, table_references, search_condition):
        return SQL('''
            WITH filtered_aml AS MATERIALIZED (
                SELECT account_move_line.*, filtered_move.move_type AS move_type
                FROM %(table_references)s
                JOIN account_move filtered_move ON filtered_move.id = account_move_line.move_id
                WHERE %(search_condition)s
            ),
            base_lines AS (
                SELECT f.*, rel.account_tax_id AS applied_tax_id
                FROM filtered_aml f
                JOIN account_move_line_account_tax_rel rel ON f.id = rel.account_move_line_id
                WHERE f.tax_repartition_line_id IS NULL
            ),
            tax_lines AS (
                SELECT
                    f.*,
                    tax_rep.tax_id,
                    tax_rep.account_id AS rep_account_id,
                    tax_rep.factor_percent AS factor_percent,
                    tax_rep.use_in_tax_closing AS use_in_tax_closing,
                    COALESCE(f.group_tax_id, f.tax_line_id) AS effective_tax_id
                FROM filtered_aml f
                JOIN account_tax_repartition_line tax_rep ON tax_rep.id = f.tax_repartition_line_id
            ),
            tax_data AS (
                SELECT
                    lt.id AS tax_line_id, lt.balance AS tax_amount,
                    aml.id AS base_line_id, aml.move_id,
                    t.sequence, t.id AS tax_id,
                    CASE WHEN t.amount_type <> 'fixed' THEN aml.balance ELSE aml.quantity END AS base_value
                FROM base_lines aml
                JOIN tax_lines lt
                ON lt.move_id = aml.move_id
                AND lt.currency_id = aml.currency_id
                AND lt.partner_id IS NOT DISTINCT FROM aml.partner_id
                AND lt.effective_tax_id = aml.applied_tax_id
                JOIN account_tax t ON aml.applied_tax_id = t.id
                WHERE (
                    aml.move_type != 'entry'
                    OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                    OR sign(aml.balance) = sign(lt.balance * t.amount * lt.factor_percent)
                ) AND (
                    COALESCE(rep_account_id, aml.account_id) = lt.account_id
                    OR (t.tax_exigibility = 'on_payment' AND t.cash_basis_transition_account_id IS NOT NULL)
                ) AND (
                    (t.analytic IS NOT TRUE AND use_in_tax_closing IS TRUE)
                    OR (aml.analytic_distribution IS NULL AND lt.analytic_distribution IS NULL)
                    OR aml.analytic_distribution = lt.analytic_distribution
                )
            ),
            aggregated AS (
                SELECT
                    *,
                    SUM(base_value) OVER (
                        PARTITION BY tax_line_id, tax_id
                        ORDER BY sequence, base_line_id
                    ) AS base_cumul,
                    SUM(base_value) OVER (PARTITION BY tax_line_id, tax_id) AS base
                FROM tax_data
            )
            SELECT
                move_id,
                tax_line_id,
                base_line_id,
                ROUND(tax_amount * base_cumul / NULLIF(base, 0), 2)
                - LAG(ROUND(tax_amount * base_cumul / NULLIF(base, 0), 2), 1, 0.0)
                    OVER (PARTITION BY tax_line_id, tax_id ORDER BY tax_line_id, base_line_id)
                    AS tax_amount
            FROM aggregated
            ORDER BY tax_line_id, base_line_id;
            ''',
            table_references=table_references,
            search_condition=search_condition,
        )

    @api.model
    def _get_query_tax_details(self, table_references, search_condition, fallback=True) -> SQL:
        """ Create the tax details sub-query based on the orm domain passed as parameter.

        :param table_references:    The query to inject after the FROM, as an SQL object.
        :param search_condition:    The query to inject in the WHERE clause, as an SQL object.
        :param fallback:            Fallback on an approximated mapping if the mapping failed.
        :return:                    query as an SQL object
        """
        group_taxes = self.env['account.tax'].search([('amount_type', '=', 'group')])

        group_taxes_query_list = []
        for group_tax in group_taxes:
            children_taxes = group_tax.children_tax_ids
            if not children_taxes:
                continue

            children_taxes_in_query = SQL(','.join('%s' for dummy in children_taxes),
                                          *children_taxes.ids)
            group_taxes_query_list.append(SQL('WHEN tax.id = %s THEN ARRAY[%s]', group_tax.id, children_taxes_in_query))

        if group_taxes_query_list:
            group_taxes_query = SQL('''UNNEST(CASE %s ELSE ARRAY[tax.id] END)''', SQL(' ').join(group_taxes_query_list))
        else:
            group_taxes_query = SQL('tax.id')

        if fallback:
            fallback_query = SQL(
                '''
                UNION ALL

                SELECT
                    account_move_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    base_line.id AS src_line_id,
                    base_line.balance AS base_amount,
                    base_line.amount_currency AS base_amount_currency
                FROM %(table_references)s
                LEFT JOIN base_tax_line_mapping ON
                    base_tax_line_mapping.tax_line_id = account_move_line.id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_tax_id = COALESCE(account_move_line.group_tax_id, account_move_line.tax_line_id)
                JOIN account_move_line base_line ON
                    base_line.id = tax_rel.account_move_line_id
                    AND base_line.tax_repartition_line_id IS NULL
                    AND base_line.move_id = account_move_line.move_id
                    AND base_line.currency_id = account_move_line.currency_id
                WHERE base_tax_line_mapping.tax_line_id IS NULL
                AND %(search_condition)s
                ''',
                table_references=table_references,
                search_condition=search_condition,
            )
        else:
            fallback_query = SQL()

        extra_query_base_tax_line_mapping = self._get_extra_query_base_tax_line_mapping()

        return SQL(
            '''
            /*
            As example to explain the different parts of the query, we'll consider a move with the following lines:
            Name            Tax_line_id         Tax_ids                 Debit       Credit      Base lines
            ---------------------------------------------------------------------------------------------------
            base_line_1                         10_affect_base, 20      1000
            base_line_2                         10_affect_base, 5       2000
            base_line_3                         10_affect_base, 5       3000
            tax_line_1      10_affect_base      20                                  100         base_line_1
            tax_line_2      20                                                      220         base_line_1
            tax_line_3      10_affect_base      5                                   500         base_line_2/3
            tax_line_4      5                                                       275         base_line_2/3
            */

            WITH base_tax_line_mapping AS (

                /*
                Create the mapping of each tax lines with their corresponding base lines.

                In the example, it will give the following values:
                    base_line_id     tax_line_id    base_amount
                    -------------------------------------------
                    base_line_1      tax_line_1         1000
                    base_line_1      tax_line_2         1000
                    base_line_2      tax_line_3         2000
                    base_line_2      tax_line_4         2000
                    base_line_3      tax_line_3         3000
                    base_line_3      tax_line_4         3000
                */

                SELECT
                    account_move_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    base_line.balance AS base_amount,
                    base_line.amount_currency AS base_amount_currency

                FROM %(table_references)s
                JOIN account_tax_repartition_line tax_rep ON
                    tax_rep.id = account_move_line.tax_repartition_line_id
                JOIN account_tax tax ON
                    tax.id = account_move_line.tax_line_id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_tax_id = COALESCE(account_move_line.group_tax_id, account_move_line.tax_line_id)
                JOIN account_move move ON
                    move.id = account_move_line.move_id
                JOIN account_move_line base_line ON
                    base_line.id = tax_rel.account_move_line_id
                    AND base_line.tax_repartition_line_id IS NULL
                    AND base_line.move_id = account_move_line.move_id
                    AND (
                        move.move_type != 'entry'
                        OR (tax.tax_exigibility = 'on_payment' AND tax.cash_basis_transition_account_id IS NOT NULL)
                        OR sign(account_move_line.balance) = sign(base_line.balance * tax.amount * tax_rep.factor_percent)
                    )
                    AND COALESCE(base_line.partner_id, 0) = COALESCE(account_move_line.partner_id, 0)
                    AND base_line.currency_id = account_move_line.currency_id
                    AND (
                        COALESCE(tax_rep.account_id, base_line.account_id) = account_move_line.account_id
                        OR (tax.tax_exigibility = 'on_payment' AND tax.cash_basis_transition_account_id IS NOT NULL)
                    )
                    AND (
                        (tax.analytic IS NOT TRUE AND tax_rep.use_in_tax_closing IS TRUE)
                        OR (base_line.analytic_distribution IS NULL AND account_move_line.analytic_distribution IS NULL)
                        OR base_line.analytic_distribution = account_move_line.analytic_distribution
                    )
                    %(extra_query_base_tax_line_mapping)s
                JOIN res_currency curr ON
                    curr.id = account_move_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = account_move_line.company_currency_id
                LEFT JOIN LATERAL (
                    /*
                        This table builds a reference table based on the tax_ids field, with the following changes:
                          - flatten the group of taxes
                          - exclude the taxes having 'is_base_affected' set to False.
                        Those allow to match only base_line_1 when finding the base lines of tax_line_1, as we need to find
                        base lines having a 'affecting_base_tax_ids' ending with [10_affect_base, 20], not only containing
                        '10_affect_base'. Otherwise, base_line_2/3 would also be matched.
                        In our example, as all the taxes are set to be affected by previous ones affecting the base, the
                        result is similar to the table 'account_move_line_account_tax_rel':
                        Id                 Tax_ids
                        -------------------------------------------
                        base_line_1        [10_affect_base, 20]
                        base_line_2        [10_affect_base, 5]
                        base_line_3        [10_affect_base, 5]
                    */
                    SELECT ARRAY_AGG(sub.tax_id ORDER BY sub.sequence, sub.tax_id) AS tax_ids
                    FROM (
                        SELECT
                            %(group_taxes_query)s AS tax_id,
                            tax.sequence
                        FROM account_move_line_account_tax_rel tax_rel
                        JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                        WHERE tax.is_base_affected
                        AND tax_rel.account_move_line_id = account_move_line.id
                    ) AS sub
                ) tax_line_tax_ids ON TRUE
                LEFT JOIN LATERAL (
                    SELECT ARRAY_AGG(sub.tax_id ORDER BY sub.sequence, sub.tax_id) AS tax_ids
                    FROM (
                        SELECT
                            %(group_taxes_query)s AS tax_id,
                            tax.sequence
                        FROM account_move_line_account_tax_rel tax_rel
                        JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
                        WHERE tax.is_base_affected
                        AND tax_rel.account_move_line_id = base_line.id
                    ) AS sub
                ) base_line_tax_ids ON TRUE
                WHERE account_move_line.tax_repartition_line_id IS NOT NULL
                    AND %(search_condition)s
                    AND (
                        -- keeping only the rows from affecting_base_tax_lines that end with the same taxes applied (see comment in tax_line_tax_ids)
                        NOT tax.include_base_amount
                        OR base_line_tax_ids.tax_ids[ARRAY_LENGTH(base_line_tax_ids.tax_ids, 1) - COALESCE(ARRAY_LENGTH(tax_line_tax_ids.tax_ids, 1), 0):ARRAY_LENGTH(base_line_tax_ids.tax_ids, 1)]
                            = ARRAY[account_move_line.tax_line_id] || COALESCE(tax_line_tax_ids.tax_ids, ARRAY[]::INTEGER[])
                    )
            ),


            tax_amount_affecting_base_to_dispatch AS (

                /*
                Computes the total amount to dispatch in case of tax lines affecting the base of subsequent taxes.
                Such tax lines are an additional base amount for others lines, that will be truly dispatch in next
                CTE.

                In the example:
                    - tax_line_1 is an additional base of 100.0 from base_line_1 for tax_line_2.
                    - tax_line_3 is an additional base of 2/5 * 500.0 = 200.0 from base_line_2 for tax_line_4.
                    - tax_line_3 is an additional base of 3/5 * 500.0 = 300.0 from base_line_3 for tax_line_4.

                    src_line_id    base_line_id     tax_line_id    total_base_amount
                    -------------------------------------------------------------
                    tax_line_1     base_line_1      tax_line_2         1000
                    tax_line_3     base_line_2      tax_line_4         5000
                    tax_line_3     base_line_3      tax_line_4         5000
                */

                SELECT
                    tax_line.id AS tax_line_id,
                    base_line.id AS base_line_id,
                    account_move_line.id AS src_line_id,

                    tax_line.company_id,
                    comp_curr.id AS company_currency_id,
                    comp_curr.decimal_places AS comp_curr_prec,
                    curr.id AS currency_id,
                    curr.decimal_places AS curr_prec,

                    tax_line.tax_line_id AS tax_id,

                    base_line.balance AS base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.balance
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id ORDER BY tax_line.tax_line_id, base_line.id) AS cumulated_base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.balance
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id) AS total_base_amount,
                    account_move_line.balance AS total_tax_amount,

                    base_line.amount_currency AS base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id ORDER BY tax_line.tax_line_id, base_line.id) AS cumulated_base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE base_line.amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id, account_move_line.id) AS total_base_amount_currency,
                    account_move_line.amount_currency AS total_tax_amount_currency

                FROM %(table_references)s
                JOIN account_tax tax_include_base_amount ON
                    tax_include_base_amount.include_base_amount
                    AND tax_include_base_amount.id = account_move_line.tax_line_id
                JOIN base_tax_line_mapping base_tax_line_mapping ON
                    base_tax_line_mapping.tax_line_id = account_move_line.id
                JOIN account_move_line_account_tax_rel tax_rel ON
                    tax_rel.account_move_line_id = base_tax_line_mapping.tax_line_id
                JOIN account_tax tax ON
                    tax.id = tax_rel.account_tax_id
                JOIN base_tax_line_mapping tax_line_matching ON
                    tax_line_matching.base_line_id = base_tax_line_mapping.base_line_id
                JOIN account_move_line tax_line ON
                    tax_line.id = tax_line_matching.tax_line_id
                    AND tax_line.tax_line_id = tax_rel.account_tax_id
                JOIN res_currency curr ON
                    curr.id = tax_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = tax_line.company_currency_id
                JOIN account_move_line base_line ON
                    base_line.id = base_tax_line_mapping.base_line_id
                WHERE %(search_condition)s
            ),


            base_tax_matching_base_amounts AS (

                /*
                Build here the full mapping tax lines <=> base lines containing the final base amounts.
                This is done in a 3-parts union.

                Note: src_line_id is used only to build a unique ID.
                */

                /*
                PART 1: raw mapping computed in base_tax_line_mapping.
                */

                SELECT
                    tax_line_id,
                    base_line_id,
                    base_line_id AS src_line_id,
                    base_amount,
                    base_amount_currency
                FROM base_tax_line_mapping

                UNION ALL

                /*
                PART 2: Dispatch the tax amount of tax lines affecting the base of subsequent ones, using
                tax_amount_affecting_base_to_dispatch.

                This will effectively add the following rows:
                base_line_id    tax_line_id     src_line_id     base_amount
                -------------------------------------------------------------
                base_line_1     tax_line_2      tax_line_1      100
                base_line_2     tax_line_4      tax_line_3      200
                base_line_3     tax_line_4      tax_line_3      300
                */

                SELECT
                    sub.tax_line_id,
                    sub.base_line_id,
                    sub.src_line_id,

                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id, sub.src_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ) AS base_amount,

                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id, sub.src_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ) AS base_amount_currency
                FROM tax_amount_affecting_base_to_dispatch sub
                JOIN account_move_line tax_line ON
                    tax_line.id = sub.tax_line_id

                /*
                PART 3: In case of the matching failed because the configuration changed or some journal entries
                have been imported, construct a simple mapping as a fallback. This mapping is super naive and only
                build based on the 'tax_ids' and 'tax_line_id' fields, nothing else. Hence, the mapping will not be
                exact but will give an acceptable approximation.

                Skipped if the 'fallback' method parameter is False.
                */
                %(fallback_query)s
            ),


            base_tax_matching_all_amounts AS (

                /*
                Complete base_tax_matching_base_amounts with the tax amounts (prorata):
                base_line_id    tax_line_id     src_line_id     base_amount     tax_amount
                --------------------------------------------------------------------------
                base_line_1     tax_line_1      base_line_1     1000            100
                base_line_1     tax_line_2      base_line_1     1000            (1000 / 1100) * 220 = 200
                base_line_1     tax_line_2      tax_line_1      100             (100 / 1100) * 220 = 20
                base_line_2     tax_line_3      base_line_2     2000            (2000 / 5000) * 500 = 200
                base_line_2     tax_line_4      base_line_2     2000            (2000 / 5500) * 275 = 100
                base_line_2     tax_line_4      tax_line_3      200             (200 / 5500) * 275 = 10
                base_line_3     tax_line_3      base_line_3     3000            (3000 / 5000) * 500 = 300
                base_line_3     tax_line_4      base_line_3     3000            (3000 / 5500) * 275 = 150
                base_line_3     tax_line_4      tax_line_3      300             (300 / 5500) * 275 = 15
                */

                SELECT
                    sub.tax_line_id,
                    sub.base_line_id,
                    sub.src_line_id,

                    tax_line.tax_line_id AS tax_id,
                    tax_line.group_tax_id,
                    tax_line.tax_repartition_line_id,

                    tax_line.company_id,
                    tax_line.display_type AS display_type,
                    comp_curr.id AS company_currency_id,
                    comp_curr.decimal_places AS comp_curr_prec,
                    curr.id AS currency_id,
                    curr.decimal_places AS curr_prec,
                    (
                        tax.tax_exigibility != 'on_payment'
                        OR tax_move.tax_cash_basis_rec_id IS NOT NULL
                        OR tax_move.always_tax_exigible
                    ) AS tax_exigible,
                    base_line.account_id AS base_account_id,

                    sub.base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount
                        END
                    ) OVER (PARTITION BY tax_line.id ORDER BY tax_line.tax_line_id, sub.base_line_id, sub.src_line_id) AS cumulated_base_amount,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.balance < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount
                        END
                    ) OVER (PARTITION BY tax_line.id) AS total_base_amount,
                    tax_line.balance AS total_tax_amount,

                    sub.base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id ORDER BY tax_line.tax_line_id, sub.base_line_id, sub.src_line_id) AS cumulated_base_amount_currency,
                    SUM(
                        CASE WHEN tax.amount_type = 'fixed'
                        THEN CASE WHEN base_line.amount_currency < 0 THEN -1 ELSE 1 END * ABS(COALESCE(base_line.quantity, 1.0))
                        ELSE sub.base_amount_currency
                        END
                    ) OVER (PARTITION BY tax_line.id) AS total_base_amount_currency,
                    tax_line.amount_currency AS total_tax_amount_currency

                FROM base_tax_matching_base_amounts sub
                JOIN account_move_line tax_line ON
                    tax_line.id = sub.tax_line_id
                JOIN account_move tax_move ON
                    tax_move.id = tax_line.move_id
                JOIN account_move_line base_line ON
                    base_line.id = sub.base_line_id
                JOIN account_tax tax ON
                    tax.id = tax_line.tax_line_id
                JOIN res_currency curr ON
                    curr.id = tax_line.currency_id
                JOIN res_currency comp_curr ON
                    comp_curr.id = tax_line.company_currency_id

            )


           /* Final select that makes sure to deal with rounding errors, using LAG to dispatch the last cents. */

            SELECT
                sub.tax_line_id || '-' || sub.base_line_id || '-' || sub.src_line_id AS id,

                sub.base_line_id,
                sub.tax_line_id,
                sub.display_type,
                sub.src_line_id,

                sub.tax_id,
                sub.group_tax_id,
                sub.tax_exigible,
                sub.base_account_id,
                sub.tax_repartition_line_id,

                sub.base_amount,
                COALESCE(
                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount) * sub.total_tax_amount * ABS(sub.cumulated_base_amount) / NULLIF(sub.total_base_amount, 0.0), 0.0),
                        sub.comp_curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ),
                    0.0
                ) AS tax_amount,

                sub.base_amount_currency,
                COALESCE(
                    ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    )
                    - LAG(ROUND(
                        COALESCE(SIGN(sub.cumulated_base_amount_currency) * sub.total_tax_amount_currency * ABS(sub.cumulated_base_amount_currency) / NULLIF(sub.total_base_amount_currency, 0.0), 0.0),
                        sub.curr_prec
                    ), 1, 0.0)
                    OVER (
                        PARTITION BY sub.tax_line_id ORDER BY sub.tax_id, sub.base_line_id
                    ),
                    0.0
                ) AS tax_amount_currency
            FROM base_tax_matching_all_amounts sub
            ''',
            extra_query_base_tax_line_mapping=extra_query_base_tax_line_mapping,
            group_taxes_query=group_taxes_query,
            search_condition=search_condition,
            table_references=table_references,
            fallback_query=fallback_query,
        )
