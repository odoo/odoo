# -*- coding: utf-8 -*-

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from itertools import groupby
from time import perf_counter

from odoo import SUPERUSER_ID, api, models, sql_db
from odoo.modules.registry import Registry
from odoo.tools import float_round


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
    def _get_query_tax_details_from_domain(self, domain, fallback=True):
        return self._get_python_tax_details_from_cache_domain(domain, fallback=fallback)

    @api.model
    def _is_python_base_tax_line_mapping_allowed(self, base_line, tax_line):
        return True

    @api.model
    def _get_python_tax_details_from_domain(self, domain, fallback=True):
        """Return tax details rows for the account.move.line domain.

        This helper keeps the account.move.line domain as the entry point, then
        groups the selected lines by move so the tax/base-line matching logic is
        readable.
        """
        selected_lines = self.search(domain, order='move_id, id')
        tax_details = []
        for _move_id, lines_iter in groupby(selected_lines, key=lambda line: line.move_id.id):
            move_lines = self.browse([line.id for line in lines_iter])
            tax_details += self._get_python_tax_details(move_lines, fallback=fallback)
        return tax_details

    @api.model
    def _get_tax_details_from_domain(self, domain, fallback=True):
        """Return tax details rows using the Python implementation over a cached scalar snapshot."""
        return self._get_query_tax_details_from_domain(domain, fallback=fallback)

    @api.model
    def _warm_tax_details_cache(
        self,
        domain=None,
        selected_lines=None,
        extra_line_fields=None,
        extra_move_fields=None,
        extra_tax_fields=None,
        offset=0,
        limit=None,
        order='move_id, id',
    ):
        line_fields = list(dict.fromkeys([
            'move_id',
            'display_type',
            'tax_repartition_line_id',
            'tax_line_id',
            'group_tax_id',
            'balance',
            'amount_currency',
            'quantity',
            'account_id',
            'partner_id',
            'currency_id',
            'company_currency_id',
            'analytic_distribution',
            'tax_ids',
            *(extra_line_fields or []),
        ]))
        move_fields = list(dict.fromkeys([
            'move_type',
            'tax_cash_basis_rec_id',
            'always_tax_exigible',
            'line_ids',
            *(extra_move_fields or []),
        ]))
        tax_fields = list(dict.fromkeys([
            'sequence',
            'amount',
            'amount_type',
            'is_base_affected',
            'include_base_amount',
            'tax_exigibility',
            'cash_basis_transition_account_id',
            'analytic',
            'children_tax_ids',
            *(extra_tax_fields or []),
        ]))
        if selected_lines is None:
            selected_lines = self.search_fetch(domain, line_fields, offset=offset, limit=limit, order=order)
        else:
            selected_lines.fetch(line_fields)
        move_lines = selected_lines.move_id.line_ids
        move_lines.fetch(line_fields)
        selected_lines.move_id.fetch(move_fields)
        taxes = move_lines.tax_ids | move_lines.tax_line_id | move_lines.group_tax_id
        taxes.fetch(tax_fields)
        taxes.children_tax_ids.fetch(tax_fields)
        move_lines.tax_repartition_line_id.fetch(['tax_id', 'account_id', 'factor_percent', 'use_in_tax_closing'])
        (move_lines.currency_id | move_lines.company_currency_id).fetch(['decimal_places'])
        return selected_lines, move_lines, taxes

    @api.model
    def _raw_ids_from_rel_cache(self, value):
        if not value:
            return []
        if hasattr(value, '_ids'):
            return list(value._ids)
        if isinstance(value, (tuple, list, set, frozenset)):
            return list(value)
        return list(value)

    @api.model
    def _get_python_tax_details_from_cache_domain(self, domain, fallback=True):
        selected_lines, move_lines, taxes = self._warm_tax_details_cache(domain)
        return self._get_python_tax_details_from_prefetched_lines(selected_lines, move_lines, taxes, fallback=fallback)

    @api.model
    def _get_python_tax_details_from_prefetched_lines(self, selected_lines, move_lines, taxes, fallback=True):
        selected_line_ids = set(selected_lines.ids)

        snapshot = {
            'lines_by_move_id': defaultdict(list),
            'taxes': {},
            'tax_reps': {},
            'currencies': {},
        }

        move_fields = self.env['account.move']._fields
        move_cache = {
            'move_type': move_fields['move_type']._get_cache(self.env),
            'tax_cash_basis_rec_id': move_fields['tax_cash_basis_rec_id']._get_cache(self.env),
            'always_tax_exigible': move_fields['always_tax_exigible']._get_cache(self.env),
        }
        line_fields = self._fields
        line_cache = {
            name: line_fields[name]._get_cache(self.env)
            for name in (
                'move_id',
                'display_type',
                'tax_repartition_line_id',
                'tax_line_id',
                'group_tax_id',
                'balance',
                'amount_currency',
                'quantity',
                'account_id',
                'partner_id',
                'currency_id',
                'company_currency_id',
                'analytic_distribution',
                'tax_ids',
            )
        }

        for line_id in move_lines.ids:
            move_id = line_cache['move_id'][line_id]
            snapshot['lines_by_move_id'][move_id].append({
                'id': line_id,
                'move_id': move_id,
                'display_type': line_cache['display_type'][line_id],
                'tax_repartition_line_id': line_cache['tax_repartition_line_id'].get(line_id),
                'tax_line_id': line_cache['tax_line_id'].get(line_id),
                'group_tax_id': line_cache['group_tax_id'].get(line_id),
                'balance': line_cache['balance'][line_id],
                'amount_currency': line_cache['amount_currency'][line_id],
                'quantity': line_cache['quantity'][line_id],
                'account_id': line_cache['account_id'].get(line_id),
                'partner_id': line_cache['partner_id'].get(line_id),
                'currency_id': line_cache['currency_id'][line_id],
                'company_currency_id': line_cache['company_currency_id'][line_id],
                'analytic_distribution': line_cache['analytic_distribution'].get(line_id),
                'move_type': move_cache['move_type'][move_id],
                'tax_cash_basis_rec_id': move_cache['tax_cash_basis_rec_id'].get(move_id),
                'always_tax_exigible': move_cache['always_tax_exigible'][move_id],
                'selected': line_id in selected_line_ids,
                'tax_ids': self._raw_ids_from_rel_cache(line_cache['tax_ids'].get(line_id)),
            })

        tax_fields = self.env['account.tax']._fields
        tax_cache = {
            name: tax_fields[name]._get_cache(self.env)
            for name in (
                'sequence',
                'amount',
                'amount_type',
                'is_base_affected',
                'include_base_amount',
                'tax_exigibility',
                'cash_basis_transition_account_id',
                'analytic',
                'children_tax_ids',
            )
        }
        for tax_id in taxes.ids + taxes.children_tax_ids.ids:
            if not tax_id:
                continue
            snapshot['taxes'][tax_id] = {
                'id': tax_id,
                'sequence': tax_cache['sequence'][tax_id],
                'amount': tax_cache['amount'][tax_id],
                'amount_type': tax_cache['amount_type'][tax_id],
                'is_base_affected': tax_cache['is_base_affected'][tax_id],
                'include_base_amount': tax_cache['include_base_amount'][tax_id],
                'tax_exigibility': tax_cache['tax_exigibility'][tax_id],
                'cash_basis_transition_account_id': tax_cache['cash_basis_transition_account_id'].get(tax_id),
                'analytic': tax_cache['analytic'][tax_id],
                'children_tax_ids': self._raw_ids_from_rel_cache(tax_cache['children_tax_ids'].get(tax_id)),
            }

        tax_reps = move_lines.tax_repartition_line_id
        rep_fields = self.env['account.tax.repartition.line']._fields
        rep_cache = {
            name: rep_fields[name]._get_cache(self.env)
            for name in ('tax_id', 'account_id', 'factor_percent', 'use_in_tax_closing')
        }
        for rep_id in tax_reps.ids:
            snapshot['tax_reps'][rep_id] = {
                'id': rep_id,
                'tax_id': rep_cache['tax_id'][rep_id],
                'account_id': rep_cache['account_id'].get(rep_id),
                'factor_percent': rep_cache['factor_percent'][rep_id],
                'use_in_tax_closing': rep_cache['use_in_tax_closing'][rep_id],
            }

        currency_cache = self.env['res.currency']._fields['decimal_places']._get_cache(self.env)
        for currency_id in (move_lines.currency_id | move_lines.company_currency_id).ids:
            snapshot['currencies'][currency_id] = {
                'id': currency_id,
                'decimal_places': currency_cache[currency_id],
            }

        for lines in snapshot['lines_by_move_id'].values():
            lines.sort(key=lambda line: line['id'])

        tax_details = []
        for move_id in sorted(snapshot['lines_by_move_id']):
            tax_details += self._get_python_tax_details_from_snapshot_move(snapshot, snapshot['lines_by_move_id'][move_id], fallback=fallback)
        return tax_details

    @api.model
    def _get_python_tax_details_from_snapshot_domain(self, domain, fallback=True):
        return self._get_python_tax_details_from_cache_domain(domain, fallback=fallback)

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
                company_precision_digits = snapshot['currencies'][tax_line['company_currency_id']]['decimal_places']
                currency_precision_digits = snapshot['currencies'][tax_line['currency_id']]['decimal_places']
                tax_amount = prorata_amount(
                    cumulated_base_amount,
                    total_base_amount,
                    tax_line['balance'],
                    company_precision_digits,
                )
                tax_amount_currency = prorata_amount(
                    cumulated_base_amount_currency,
                    total_base_amount_currency,
                    tax_line['amount_currency'],
                    currency_precision_digits,
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
                    'tax_amount': round_digits(tax_amount - previous_tax_amount, company_precision_digits),
                    'base_amount_currency': row['base_amount_currency'],
                    'tax_amount_currency': round_digits(tax_amount_currency - previous_tax_amount_currency, currency_precision_digits),
                })
                previous_tax_amount = tax_amount
                previous_tax_amount_currency = tax_amount_currency
        return results

    def _get_python_tax_details(self, filtered_lines, fallback=True):
        """ This is double as a reference for the dict snapshot one"""
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
                company_precision_digits = tax_line.company_currency_id.decimal_places
                currency_precision_digits = tax_line.currency_id.decimal_places
                tax_amount = prorata_amount(
                    cumulated_base_amount,
                    total_base_amount,
                    tax_line.balance,
                    company_precision_digits,
                )
                tax_amount_currency = prorata_amount(
                    cumulated_base_amount_currency,
                    total_base_amount_currency,
                    tax_line.amount_currency,
                    currency_precision_digits,
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
                    'tax_amount': round_digits(tax_amount - previous_tax_amount, company_precision_digits),
                    'base_amount_currency': row['base_amount_currency'],
                    'tax_amount_currency': round_digits(tax_amount_currency - previous_tax_amount_currency, currency_precision_digits),
                })
                previous_tax_amount = tax_amount
                previous_tax_amount_currency = tax_amount_currency
        return results
