# -*- coding: utf-8 -*-
"""Odoo-native Postlog Data (Postlog) matching workflow.

Deliberate mirror of models/mv_prelog_fuzzy_matching_service.py. Method names
are identical on purpose so the two services stay diffable and an engineer only
has to learn the shape once.

Divergences from the postlog service, both because a postlog is the single
as-run record for a week rather than a plan that gets re-issued:

  * no ``version`` - one upload per week, so there is nothing to version.
  * no ``removed`` - rows are not soft-removed; Delete is the only removal.

Field-name map against mv.prelog_data:

    airdate          -> air_date
    scheduletime     -> air_time
    schedulelength   -> length            (Selection ``v_60``, not Char "60")
    rate             -> spot_rate
    advertiserproduct-> product
    title            -> commercial_title
"""

import csv
import io
import re
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

from ..services.postlog_import.config_loader import load_program_config
from ..services.import_utils.transforms import normalize_match_text


class MvPostlogMatching(models.Model):
    """Backend service for the Odoo-native Postlog Workbench.

    Same contract as the postlog service: matching is computed live on every
    search and never stored, and the only thing persisted is the chosen
    ``schedule`` on the Postlog row.
    """

    _inherit = 'mv.spot_data'

    _FUZZY_PAGE_SIZE = 200
    _FUZZY_TIME_BUFFER_MINUTES = 120
    _FUZZY_MAX_ALTERNATIVES = 4
    _FUZZY_DAY_ORDER = {
        'mon': 0,
        'tue': 1,
        'wed': 2,
        'thu': 3,
        'fri': 4,
        'sat': 5,
        'sun': 6,
    }

    # ------------------------------------------------------------------
    # Public RPC methods
    # ------------------------------------------------------------------

    @api.model
    def fuzzy_match_get_options(self, program_id=False, week_start=False):
        """Return filters and the current user's latest completed upload."""
        self._fuzzy_check_access()
        programs = self.env['mv.programs'].search([], order='name, id')
        program, selected_week = (
            self._fuzzy_validate_optional_filters(program_id, week_start)
        )

        return {
            'programs': [
                {
                    'id': program.id,
                    'name': program.display_name,
                    'inactive': bool(program.inactive),
                }
                for program in programs
            ],
            'page_size': self._FUZZY_PAGE_SIZE,
            'time_buffer_minutes': self._FUZZY_TIME_BUFFER_MINUTES,
            'latest_upload': self._fuzzy_latest_user_upload(),
        }

    @api.model
    def fuzzy_match_search(
        self,
        program_id,
        week_start,
        offset=0,
        limit=None,
        status='all',
        search_term='',
        air_date=False,
        issue_filter='',
        sort_by='air_date',
        import_job_id=False,
        sort_direction='asc',
    ):
        """Return a classified page for the Postlog Workbench."""
        self._fuzzy_check_access()
        program, selected_week = self._fuzzy_validate_optional_filters(
            program_id,
            week_start,
        )
        offset = max(self._fuzzy_int(offset, default=0), 0)
        limit = self._fuzzy_int(limit, default=self._FUZZY_PAGE_SIZE)
        limit = min(max(limit, 1), self._FUZZY_PAGE_SIZE)
        domain = self._fuzzy_postlog_domain(
            program.id if program else False,
            selected_week,
            unmatched_only=False,
            import_job_id=import_job_id,
        )
        postlogs = self.search(domain, order='air_date asc, air_time asc, id asc')
        all_rows = self._fuzzy_build_rows(
            postlogs,
            program,
            selected_week,
            use_attached=True,
        )
        for row, postlog in zip(all_rows, postlogs):
            self._fuzzy_classify_row(row, postlog)

        counts = {
            'all': len(all_rows),
            'matched': sum(row['status'] == 'matched' for row in all_rows),
            'unmatched': sum(
                row['status'] in ('suggestion', 'no_suggestion')
                for row in all_rows
            ),
            'suggestions': sum(row['status'] == 'suggestion' for row in all_rows),
            'no_suggestion': sum(row['status'] == 'no_suggestion' for row in all_rows),
        }
        rows = self._fuzzy_filter_workbench_rows(
            all_rows,
            status=status,
            search_term=search_term,
            air_date=air_date,
            issue_filter=issue_filter,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        total = len(rows)
        if total:
            offset = min(offset, ((total - 1) // limit) * limit)
        else:
            offset = 0
        return {
            'rows': rows[offset:offset + limit],
            'total': total,
            'offset': offset,
            'limit': limit,
            'page': (offset // limit) + 1 if total else 0,
            'pages': ((total + limit - 1) // limit) if total else 0,
            'counts': counts,
        }

    @api.model
    def fuzzy_match_apply(
        self,
        selections,
        program_id=False,
        week_start=False,
    ):
        """Attach selected schedules directly to unmatched Postlog Data.

        Every selection is validated before the first write, which keeps the
        operation all-or-none. Suggested schedules must still be sold and in
        the same Program/week. Manual overrides are deliberately more
        permissive, but must be explicitly confirmed by the caller.
        """
        self._fuzzy_check_access()
        selections = selections or []
        if not isinstance(selections, list) or not selections:
            raise UserError(_('Select at least one Postlog row to attach.'))
        filter_values = (program_id, week_start)
        expected_filter = False
        if any(value not in (False, None, '') for value in filter_values):
            expected_filter = self._fuzzy_validate_optional_filters(
                program_id,
                week_start,
            )

        normalized = []
        seen_postlog_ids = set()
        for item in selections:
            if not isinstance(item, dict):
                raise UserError(_('A schedule selection has an invalid format.'))
            postlog_id = self._fuzzy_int(item.get('postlog_id'))
            if not postlog_id or postlog_id in seen_postlog_ids:
                raise UserError(_('Each selected Postlog row must be unique.'))
            seen_postlog_ids.add(postlog_id)
            normalized.append({
                'postlog_id': postlog_id,
                'schedule_id': self._fuzzy_int(item.get('schedule_id')),
                'schedule_ref': (item.get('schedule_ref') or '').strip(),
                'source': item.get('source') or 'suggested',
                'confirmed_override': bool(item.get('confirmed_override')),
                'replace_existing': bool(item.get('replace_existing')),
            })

        postlogs = self.search([('id', 'in', list(seen_postlog_ids))])
        postlogs_by_id = {postlog.id: postlog for postlog in postlogs}
        prepared = []
        errors = []

        for item in normalized:
            postlog = postlogs_by_id.get(item['postlog_id'])
            if not postlog:
                errors.append(
                    _('Postlog Data ID %(id)s was not found or is not accessible.')
                    % {'id': item['postlog_id']}
                )
                continue
            if postlog.schedule and not (
                item['source'] == 'manual'
                and item['replace_existing']
                and item['confirmed_override']
            ):
                errors.append(
                    _('%(postlog)s is already matched. Use Replace Schedule to change it.')
                    % {'postlog': postlog.display_name}
                )
                continue
            if expected_filter:
                expected_program, expected_week = expected_filter
                if any((
                    expected_program and postlog.import_program != expected_program,
                    expected_week and postlog.import_week_value != expected_week,
                )):
                    errors.append(
                        _(
                            '%(postlog)s no longer belongs to the active '
                            'Program and week filters. Refresh the '
                            'page and try again.'
                        )
                        % {'postlog': postlog.display_name}
                    )
                    continue

            schedule, resolution_error = self._fuzzy_resolve_schedule(item)
            if resolution_error:
                errors.append(
                    _('%(postlog)s: %(error)s')
                    % {'postlog': postlog.display_name, 'error': resolution_error}
                )
                continue

            if item['source'] == 'suggested':
                if schedule.status != 'sold':
                    errors.append(
                        _('%(postlog)s: only a sold schedule can be attached as a suggestion.')
                        % {'postlog': postlog.display_name}
                    )
                    continue
                analysis = self._fuzzy_analyze_schedule(
                    postlog,
                    postlog.import_program,
                    schedule,
                )
                if not all(
                    analysis[key]
                    for key in (
                        'network_match',
                        'deal_match',
                        'rate_match',
                        'day_match',
                    )
                ):
                    errors.append(
                        _(
                            '%(postlog)s: the suggested schedule no longer '
                            'meets the network, deal, rate, and day criteria.'
                        )
                        % {'postlog': postlog.display_name}
                    )
                    continue
                if (
                    (
                        not analysis['time_match']
                        or not analysis['length_match']
                    )
                    and not item['confirmed_override']
                ):
                    errors.append(
                        _('%(postlog)s: confirm the time or length mismatch before attaching.')
                        % {'postlog': postlog.display_name}
                    )
                    continue
                if (
                    not postlog.import_program
                    or schedule.deal_parent.program != postlog.import_program
                    or schedule.week != postlog.import_week_value
                ):
                    errors.append(
                        _('%(postlog)s: the suggested schedule no longer belongs to the same Program and week.')
                        % {'postlog': postlog.display_name}
                    )
                    continue
            elif item['source'] == 'manual':
                if not item['confirmed_override']:
                    errors.append(
                        _('%(postlog)s: confirm the manual schedule override before attaching.')
                        % {'postlog': postlog.display_name}
                    )
                    continue
            else:
                errors.append(
                    _('%(postlog)s: unknown selection source.')
                    % {'postlog': postlog.display_name}
                )
                continue

            prepared.append((postlog, schedule, item['source'], postlog.schedule))

        if errors:
            raise UserError('\n'.join(errors))

        now = fields.Datetime.now()
        user_name = self.env.user.display_name
        for postlog, schedule, source, previous_schedule in prepared:
            audit_line = _(
                'Schedule %(schedule)s attached from Postlog Workbench '
                '(%(source)s) by %(user)s on %(date)s.'
            ) % {
                'schedule': schedule.display_name,
                'source': _('manual override') if source == 'manual' else _('suggestion'),
                'user': user_name,
                'date': fields.Datetime.to_string(now),
            }
            if previous_schedule:
                audit_line = _(
                    'Schedule %(previous)s replaced with %(schedule)s from '
                    'Postlog Workbench by %(user)s on %(date)s.'
                ) % {
                    'previous': previous_schedule.display_name,
                    'schedule': schedule.display_name,
                    'user': user_name,
                    'date': fields.Datetime.to_string(now),
                }
            detail = '\n'.join(
                part
                for part in (postlog.import_match_detail, audit_line)
                if part
            )
            postlog.write({
                'schedule': schedule.id,
                'import_match_status': 'matched',
                'import_match_detail': detail,
            })

        return {
            'attached': len(prepared),
            'message': _('%(count)s schedule(s) successfully attached.')
            % {'count': len(prepared)},
        }

    @api.model
    def fuzzy_workbench_bulk_action(
        self,
        action_name,
        selection,
        program_id=False,
        week_start=False,
        status='all',
        search_term='',
        air_date=False,
        issue_filter='',
        sort_by='air_date',
        import_job_id=False,
        confirmed_fuzzy=False,
        sort_direction='asc',
    ):
        """Apply a Workbench action to explicit rows or every filtered row."""
        self._fuzzy_check_access()
        action_name = (action_name or '').strip().lower()
        if action_name not in {'attach', 'delete'}:
            raise UserError(_('Unknown Postlog Workbench bulk action.'))

        postlogs, rows = self._fuzzy_resolve_workbench_selection(
            selection,
            program_id,
            week_start,
            status,
            search_term,
            air_date,
            issue_filter,
            sort_by,
            import_job_id,
            sort_direction,
        )
        if action_name == 'attach':
            row_by_id = {row['id']: row for row in rows}
            attachable = [
                row_by_id[postlog.id]
                for postlog in postlogs
                if (
                    row_by_id[postlog.id]['status'] == 'suggestion'
                    and row_by_id[postlog.id].get('suggested')
                    and row_by_id[postlog.id].get('suggestion_attachable')
                )
            ]
            fuzzy_count = sum(
                row.get('match_quality') != 'exact' for row in attachable
            )
            if fuzzy_count and not confirmed_fuzzy:
                return {
                    'requires_confirmation': True,
                    'selected': len(postlogs),
                    'attachable': len(attachable),
                    'fuzzy': fuzzy_count,
                }
            if not attachable:
                return {
                    'attached': 0,
                    'skipped': len(postlogs),
                    'message': _('No selected rows have an attachable suggestion.'),
                }
            payload = [{
                'postlog_id': row['id'],
                'schedule_id': row['suggested']['id'],
                'source': 'suggested',
                'confirmed_override': row.get('match_quality') != 'exact',
            } for row in attachable]
            result = self.fuzzy_match_apply(
                payload,
                program_id,
                week_start,
            )
            result['skipped'] = len(postlogs) - len(attachable)
            if result['skipped']:
                result['message'] += ' ' + _(
                    '%(count)s selected row(s) without an attachable suggestion were skipped.'
                ) % {'count': result['skipped']}
            return result

        deleted = len(postlogs)
        postlogs.unlink()
        return {
            'deleted': deleted,
            'message': _('%(count)s Postlog row(s) permanently deleted.')
            % {'count': deleted},
        }

    @api.model
    def fuzzy_match_detach(
        self,
        postlog_ids,
        program_id=False,
        week_start=False,
        import_job_id=False,
    ):
        self._fuzzy_check_access()
        postlogs = self._fuzzy_validate_selected_postlogs(
            postlog_ids,
            program_id,
            week_start,
            import_job_id,
        )
        now = fields.Datetime.now()
        detached = 0
        for postlog in postlogs.filtered('schedule'):
            line = _(
                'Schedule %(schedule)s detached in Postlog Workbench '
                'by %(user)s on %(date)s.'
            ) % {
                'schedule': postlog.schedule.display_name,
                'user': self.env.user.display_name,
                'date': fields.Datetime.to_string(now),
            }
            postlog.write({
                'schedule': False,
                'import_match_status': 'created_without_schedule',
                'import_match_detail': '\n'.join(
                    part for part in (postlog.import_match_detail, line) if part
                ),
            })
            detached += 1
        return {
            'updated': detached,
            'message': _('%(count)s schedule(s) detached.') % {'count': detached},
        }

    @api.model
    def fuzzy_match_export_csv(self, program_id, week_start):
        """Build the filtered exception report as a downloadable CSV."""
        self._fuzzy_check_access()
        program, selected_week = self._fuzzy_validate_filters(
            program_id,
            week_start,
        )
        postlogs = self.search(
            self._fuzzy_postlog_domain(
                program.id,
                selected_week,
                unmatched_only=False,
            ),
            order='air_date asc, air_time asc, id asc',
        )
        rows = self._fuzzy_build_rows(
            postlogs,
            program,
            selected_week,
            use_attached=True,
        )

        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow([
            'Name',
            'Network',
            'Air Date',
            'Day',
            'Air Time',
            'Postlog Data Length',
            'Rate',
            'Week',
            'Network Deal #',
            'Adv/Product',
            'Reason',
        ])
        exported = 0
        for row in rows:
            if not (
                row['reason']
                or row['time_mismatch']
                or row['length_mismatch']
            ):
                continue
            writer.writerow(self._fuzzy_csv_row([
                row['name'],
                row['network'],
                row['air_date'],
                row['day'],
                row['air_time'],
                row['length'],
                row['rate'],
                row['week'],
                row['deal_number'],
                row['advertiser_product'],
                row['reason'],
            ]))
            exported += 1

        safe_program = re.sub(
            r'[^A-Za-z0-9_-]+',
            '-',
            program.display_name,
        ).strip('-')
        filename = 'PostlogMatching-%s-%s.csv' % (
            safe_program or 'Program',
            fields.Date.to_string(selected_week),
        )
        return {
            'filename': filename,
            'content': output.getvalue(),
            'count': exported,
        }

    @api.model
    def fuzzy_workbench_export_csv(
        self,
        program_id,
        week_start,
        status='all',
        search_term='',
        air_date=False,
        issue_filter='',
        sort_by='air_date',
        import_job_id=False,
        sort_direction='asc',
    ):
        """Export the active workbench tab and its current filters."""
        self._fuzzy_check_access()
        program, selected_week = self._fuzzy_validate_optional_filters(
            program_id, week_start
        )
        postlogs = self.search(
            self._fuzzy_postlog_domain(
                program.id if program else False,
                selected_week,
                unmatched_only=False,
                import_job_id=import_job_id,
            ),
            order='air_date asc, air_time asc, id asc',
        )
        rows = self._fuzzy_build_rows(
            postlogs, program, selected_week, use_attached=True
        )
        for row, postlog in zip(rows, postlogs):
            self._fuzzy_classify_row(row, postlog)
        rows = self._fuzzy_filter_workbench_rows(
            rows,
            status=status,
            search_term=search_term,
            air_date=air_date,
            issue_filter=issue_filter,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow([
            'Postlog Data', 'Status', 'Match Quality', 'Network', 'Air Date',
            'Air Time', 'Length', 'Rate', 'Week', 'Network Deal #',
            'Adv/Product', 'Schedule', 'Reason',
        ])
        for row in rows:
            schedule = row.get('attached') or row.get('suggested') or {}
            writer.writerow(self._fuzzy_csv_row([
                row['name'], row['status_label'], row['match_quality_label'],
                row['network'], row['air_date'], row['air_time'], row['length'],
                row['rate'], row['week'], row['deal_number'],
                row['advertiser_product'], schedule.get('name', ''), row['reason'],
            ]))
        safe_program = re.sub(
            r'[^A-Za-z0-9_-]+',
            '-',
            program.display_name if program else 'All-Programs',
        ).strip('-')
        filename = 'PostlogWorkbench-%s-%s-%s.csv' % (
            safe_program or 'All-Programs',
            fields.Date.to_string(selected_week) if selected_week else 'All-Weeks',
            status,
        )
        return {'filename': filename, 'content': output.getvalue(), 'count': len(rows)}

    # ------------------------------------------------------------------
    # Query and result construction
    # ------------------------------------------------------------------

    @api.model
    def _fuzzy_check_access(self):
        if not self.env.user.has_group(
            'marathon_ventures.group_postlog_matching'
        ):
            raise UserError(
                _(
                    'You do not have permission to use the Postlog Workbench. '
                    'Ask an administrator for the Postlog Workbench / '
                    'Operator access right.'
                )
            )

    @api.model
    def _fuzzy_latest_user_upload(self):
        """Return metadata only; the uploaded filename is intentionally hidden."""
        if 'mv.postlog_import_job' not in self.env.registry.models:
            return False
        job = self.env['mv.postlog_import_job'].search([
            ('state', '=', 'completed'),
            ('submitted_by_id', '=', self.env.user.id),
            ('postlog_ids', '!=', False),
        ], order='finished_at desc, id desc', limit=1)
        if not job:
            return False
        return {
            'id': job.id,
            'program_id': job.program_id.id,
            'program_name': job.program_id.display_name,
            'week_start': fields.Date.to_string(job.import_week),
            'submitted_at': (
                fields.Datetime.to_string(job.finished_at or job.create_date)
            ),
            'submitted_by': job.submitted_by_id.display_name,
            'row_count': len(job.postlog_ids),
        }

    @api.model
    def _fuzzy_validate_filters(self, program_id, week_start):
        parsed_program_id = self._fuzzy_int(program_id)
        program = self.env['mv.programs'].search(
            [('id', '=', parsed_program_id)],
            limit=1,
        )
        if not program:
            raise UserError(_('Select a valid Program.'))
        try:
            selected_week = fields.Date.to_date(week_start)
        except (TypeError, ValueError):
            selected_week = False
        if not selected_week:
            raise UserError(_('Select a valid week start date.'))
        if selected_week.weekday() != 0:
            raise UserError(
                _('Week must be the Monday that starts the broadcast week.')
            )
        return program, selected_week

    @api.model
    def _fuzzy_validate_optional_filters(self, program_id, week_start):
        """Validate each Workbench filter independently; blank means all."""
        program = False
        if program_id not in (False, None, '', 0, '0'):
            parsed_program_id = self._fuzzy_int(program_id)
            program = self.env['mv.programs'].search(
                [('id', '=', parsed_program_id)],
                limit=1,
            )
            if not program:
                raise UserError(_('Select a valid Program.'))

        selected_week = False
        if week_start not in (False, None, ''):
            try:
                selected_week = fields.Date.to_date(week_start)
            except (TypeError, ValueError):
                selected_week = False
            if not selected_week:
                raise UserError(_('Select a valid week start date.'))
            if selected_week.weekday() != 0:
                raise UserError(
                    _('Week must be the Monday that starts the broadcast week.')
                )

        return program, selected_week

    @api.model
    def _fuzzy_postlog_domain(
        self,
        program_id,
        selected_week,
        unmatched_only=True,
        import_job_id=False,
    ):
        domain = []
        if program_id:
            domain.append(('import_program', '=', program_id))
        if selected_week:
            domain.append(('import_week_value', '=', selected_week))
        if unmatched_only:
            domain.insert(0, ('schedule', '=', False))
        if import_job_id:
            domain.append(('import_job', '=', self._fuzzy_int(import_job_id)))
        return domain

    @api.model
    def _fuzzy_classify_row(self, row, postlog):
        if postlog.schedule:
            status = 'matched'
        elif row.get('suggested'):
            status = 'suggestion'
        else:
            status = 'no_suggestion'
        row.update({
            'status': status,
            'status_label': {
                'matched': _('Matched'),
                'suggestion': _('Fuzzy Suggestion'),
                'no_suggestion': _('No Suggestion'),
            }[status],
            'attached': (
                self._fuzzy_schedule_payload(postlog.schedule)
                if postlog.schedule else False
            ),
            'agency': postlog.agency or '',
            'title': postlog.commercial_title or '',
            'match_detail': postlog.import_match_detail or '',
            'import_job_name': postlog.import_job.name if postlog.import_job else '',
        })

    @api.model
    def _fuzzy_filter_workbench_rows(
        self,
        rows,
        status='all',
        search_term='',
        air_date=False,
        issue_filter='',
        sort_by='air_date',
        sort_direction='asc',
    ):
        status = status if status in {
            'all', 'matched', 'unmatched', 'suggestions', 'no_suggestion'
        } else 'all'
        status_map = {
            'matched': 'matched',
            'suggestions': 'suggestion',
            'no_suggestion': 'no_suggestion',
        }
        if status == 'all':
            result = list(rows)
        elif status == 'unmatched':
            result = [
                row for row in rows
                if row['status'] in ('suggestion', 'no_suggestion')
            ]
        else:
            result = [row for row in rows if row['status'] == status_map[status]]

        needle = normalize_match_text(search_term)
        if needle:
            result = [
                row for row in result
                if needle in normalize_match_text(' '.join([
                    str(row.get('name') or ''),
                    str(row.get('advertiser_product') or ''),
                    str(row.get('deal_number') or ''),
                    str((row.get('attached') or {}).get('name') or ''),
                    str((row.get('suggested') or {}).get('name') or ''),
                ]))
            ]
        if air_date:
            try:
                normalized_date = fields.Date.to_string(fields.Date.to_date(air_date))
            except (TypeError, ValueError):
                normalized_date = ''
            if normalized_date:
                result = [row for row in result if row['air_date'] == normalized_date]

        issue_checks = {
            'time': lambda row: row['time_mismatch'],
            'length': lambda row: row['length_mismatch'],
            'rate': lambda row: row['rate_mismatch'],
            'day': lambda row: row['day_mismatch'],
            'ready': lambda row: (
                row['status'] == 'suggestion' and row['match_quality'] == 'exact'
            ),
            'ambiguous': lambda row: row['ambiguous_count'] > 1,
            'missing_deal': lambda row: row['reason'] == _('Missing deal number'),
        }
        if issue_filter in issue_checks:
            result = [row for row in result if issue_checks[issue_filter](row)]

        def natural_text(value):
            return tuple(
                (0, int(part)) if part.isdigit() else (1, part)
                for part in re.split(r'(\d+)', normalize_match_text(value))
                if part
            )

        def time_value(row):
            parsed = self._fuzzy_parse_time(row.get('air_time'))
            return (
                (parsed.hour * 3600) + (parsed.minute * 60) + parsed.second
                if parsed else 0
            )

        def schedule_name(row):
            schedule = row.get('attached') or row.get('suggested') or {}
            return schedule.get('name') or ''

        def visible_reason(row):
            return row.get('reason') or (
                _('Schedule attached')
                if row.get('status') == 'matched'
                else _('Ready to attach')
            )

        sort_keys = {
            'status': lambda row: (
                natural_text(row.get('status_label')), row['air_date'], row['id']
            ),
            'name': lambda row: (
                natural_text(row.get('name')), row['air_date'], row['id']
            ),
            'network': lambda row: (
                natural_text(row.get('network')), row['air_date'], row['id']
            ),
            'air_date': lambda row: (
                row.get('air_date') or '', time_value(row), row['id']
            ),
            'length': lambda row: (
                self._fuzzy_parse_length(row.get('length')) or 0,
                row['air_date'], row['id'],
            ),
            'rate': lambda row: (
                float(row.get('rate') or 0), row['air_date'], row['id']
            ),
            'deal_number': lambda row: (
                natural_text(row.get('deal_number')), row['air_date'], row['id']
            ),
            'advertiser_product': lambda row: (
                natural_text(row.get('advertiser_product')), row['air_date'], row['id']
            ),
            'schedule': lambda row: (
                natural_text(schedule_name(row)), row['air_date'], row['id']
            ),
            'reason': lambda row: (
                natural_text(visible_reason(row)), row['air_date'], row['id']
            ),
        }
        sort_by = sort_by if sort_by in sort_keys else 'air_date'
        reverse = str(sort_direction or '').lower() == 'desc'
        missing_checks = {
            'status': lambda row: not row.get('status_label'),
            'name': lambda row: not row.get('name'),
            'network': lambda row: not row.get('network'),
            'air_date': lambda row: not row.get('air_date'),
            'length': lambda row: self._fuzzy_parse_length(row.get('length')) is None,
            'rate': lambda row: row.get('rate') in (None, ''),
            'deal_number': lambda row: not row.get('deal_number'),
            'advertiser_product': lambda row: not row.get('advertiser_product'),
            'schedule': lambda row: not schedule_name(row),
            'reason': lambda row: not visible_reason(row),
        }
        has_missing_value = missing_checks[sort_by]
        populated = [row for row in result if not has_missing_value(row)]
        missing = [row for row in result if has_missing_value(row)]
        return (
            sorted(populated, key=sort_keys[sort_by], reverse=reverse)
            + sorted(missing, key=lambda row: row['id'])
        )

    @api.model
    def _fuzzy_validate_selected_postlogs(
        self,
        postlog_ids,
        program_id=False,
        week_start=False,
        import_job_id=False,
    ):
        ids = []
        for value in postlog_ids or []:
            parsed_id = self._fuzzy_int(value)
            if parsed_id and parsed_id not in ids:
                ids.append(parsed_id)
        if not ids:
            raise UserError(_('Select at least one Postlog row.'))
        program, selected_week = self._fuzzy_validate_optional_filters(
            program_id,
            week_start,
        )
        domain = self._fuzzy_postlog_domain(
            program.id if program else False,
            selected_week,
            unmatched_only=False,
            import_job_id=import_job_id,
        ) + [('id', 'in', ids)]
        postlogs = self.search(domain)
        if len(postlogs) != len(ids):
            raise UserError(
                _('One or more selected rows no longer belong to the active upload and filters.')
            )
        return postlogs

    @api.model
    def _fuzzy_resolve_workbench_selection(
        self,
        selection,
        program_id=False,
        week_start=False,
        status='all',
        search_term='',
        air_date=False,
        issue_filter='',
        sort_by='air_date',
        import_job_id=False,
        sort_direction='asc',
    ):
        if not isinstance(selection, dict):
            raise UserError(_('The selected Postlog rows have an invalid format.'))
        program, selected_week = (
            self._fuzzy_validate_optional_filters(program_id, week_start)
        )
        postlogs = self.search(
            self._fuzzy_postlog_domain(
                program.id if program else False,
                selected_week,
                unmatched_only=False,
                import_job_id=import_job_id,
            ),
            order='air_date asc, air_time asc, id asc',
        )
        rows = self._fuzzy_build_rows(
            postlogs,
            program,
            selected_week,
            use_attached=True,
        )
        for row, postlog in zip(rows, postlogs):
            self._fuzzy_classify_row(row, postlog)
        filtered_rows = self._fuzzy_filter_workbench_rows(
            rows,
            status=status,
            search_term=search_term,
            air_date=air_date,
            issue_filter=issue_filter,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        filtered_ids = [row['id'] for row in filtered_rows]
        filtered_id_set = set(filtered_ids)
        if selection.get('all_matching'):
            excluded_ids = {
                self._fuzzy_int(value)
                for value in selection.get('excluded_ids', [])
                if self._fuzzy_int(value)
            }
            selected_ids = [
                row_id for row_id in filtered_ids if row_id not in excluded_ids
            ]
        else:
            selected_ids = []
            for value in selection.get('ids', []):
                row_id = self._fuzzy_int(value)
                if row_id and row_id not in selected_ids:
                    selected_ids.append(row_id)
            if any(row_id not in filtered_id_set for row_id in selected_ids):
                raise UserError(
                    _('One or more selected rows no longer belong to the active view. Refresh and try again.')
                )
        if not selected_ids:
            raise UserError(_('Select at least one Postlog row.'))
        selected_set = set(selected_ids)
        selected_rows = [
            row for row in filtered_rows if row['id'] in selected_set
        ]
        records_by_id = {postlog.id: postlog for postlog in postlogs}
        selected_postlogs = self.browse()
        for row_id in selected_ids:
            selected_postlogs |= records_by_id[row_id]
        return selected_postlogs, selected_rows

    @api.model
    def _fuzzy_build_rows(
        self,
        postlogs,
        program,
        selected_week,
        use_attached=False,
    ):
        groups = {}
        contexts = {}
        for postlog in postlogs:
            row_program = postlog.import_program or program
            row_week = postlog.import_week_value or selected_week
            key = (row_program.id if row_program else False, row_week)
            groups.setdefault(key, self.browse())
            groups[key] |= postlog
            contexts[key] = (row_program, row_week)

        candidate_maps = {}
        accepted_networks = {}
        for key, grouped_postlogs in groups.items():
            row_program, row_week = contexts[key]
            candidate_maps[key] = self._fuzzy_candidate_map(
                grouped_postlogs,
                row_program,
                row_week,
            )
            accepted_networks[key] = self._fuzzy_network_names(row_program)

        result = []
        for postlog in postlogs:
            row_program = postlog.import_program or program
            row_week = postlog.import_week_value or selected_week
            key = (row_program.id if row_program else False, row_week)
            result.append(self._fuzzy_build_row(
                postlog,
                row_program,
                candidate_maps[key].get(
                    (postlog.network_deal_number or '').strip(),
                    [],
                ),
                accepted_networks[key],
                postlog.schedule if use_attached else False,
            ))
        return result

    @api.model
    def _fuzzy_candidate_map(self, postlogs, program, selected_week):
        if not program or not selected_week:
            return {}
        deal_numbers = sorted({
            (postlog.network_deal_number or '').strip()
            for postlog in postlogs
            if (postlog.network_deal_number or '').strip()
        })
        if not deal_numbers:
            return {}
        schedules = self.env['mv.schedules'].search([
            ('week', '=', selected_week),
            ('deal_parent.program', '=', program.id),
            ('deal_parent.network_deal_number', 'in', deal_numbers),
        ], order='id')
        result = {}
        for schedule in schedules:
            deal_number = (
                schedule.deal_parent.network_deal_number or ''
            ).strip()
            result.setdefault(deal_number, []).append(schedule)
        return result

    @api.model
    def _fuzzy_build_row(
        self,
        postlog,
        program,
        schedules,
        accepted_networks=None,
        attached_schedule=False,
    ):
        day = postlog.air_date.strftime('%a') if postlog.air_date else ''
        reason = ''
        suggested = False
        suggested_analysis = False
        ambiguous_count = 0
        alternatives = []

        if attached_schedule:
            suggested_analysis = self._fuzzy_analyze_schedule(
                postlog,
                program,
                attached_schedule,
                accepted_networks,
            )
            suggested = attached_schedule
        elif not (postlog.network_deal_number or '').strip():
            reason = _('Missing deal number')
        elif not (postlog.air_time or '').strip():
            reason = _('Missing air time')
        elif not postlog.air_date:
            # Distinct from a day *mismatch*: with no date there is nothing to
            # compare, so offering a schedule would be a guess.
            reason = _('Missing air date')
        else:
            analyses = [
                self._fuzzy_analyze_schedule(
                    postlog,
                    program,
                    schedule,
                    accepted_networks,
                )
                for schedule in schedules
            ]
            # Network is the only hard boundary: a different network's
            # schedule is genuinely the wrong record. A rate or day mismatch is
            # a real trafficking discrepancy the operator should SEE against the
            # schedule it nearly matched, so those stay eligible and surface as
            # fuzzy suggestions with a reason instead of vanishing.
            eligible = [
                analysis
                for analysis in analyses
                if analysis['network_match']
            ]
            if eligible:
                eligible.sort(key=self._fuzzy_analysis_sort_key)
                suggested_analysis = eligible[0]
                suggested = suggested_analysis['schedule']
                winning_key = self._fuzzy_analysis_quality_key(
                    suggested_analysis
                )
                ambiguous_count = sum(
                    1
                    for analysis in eligible
                    if self._fuzzy_analysis_quality_key(analysis) == winning_key
                )
                # Every candidate was already analysed and ranked; keeping the
                # runners-up lets the drawer offer them instead of throwing the
                # work away. Capped so a deal with 150 schedules cannot bloat
                # the payload.
                alternatives = [
                    self._fuzzy_alternative_payload(analysis)
                    for analysis in eligible[1:self._FUZZY_MAX_ALTERNATIVES + 1]
                ]
            else:
                reason = self._fuzzy_no_suggestion_reason(analyses)

        length_mismatch = False
        time_mismatch = False
        rate_mismatch = False
        deal_mismatch = False
        network_mismatch = False
        day_mismatch = False
        suggestion_attachable = False

        if suggested_analysis:
            time_mismatch = not suggested_analysis['time_match']
            length_mismatch = not suggested_analysis['length_match']
            rate_mismatch = not suggested_analysis['rate_match']
            deal_mismatch = not suggested_analysis['deal_match']
            network_mismatch = not suggested_analysis['network_match']
            day_mismatch = not suggested_analysis['day_match']
            suggestion_attachable = suggested.status == 'sold'

            if not suggested_analysis['network_match']:
                reason = _('Network mismatch')
            elif not suggested_analysis['week_match']:
                reason = _('Week mismatch')
            elif not suggested_analysis['deal_match']:
                reason = _('Deal number mismatch')
            elif not suggested_analysis['rate_match']:
                reason = _('Rate mismatch')
            elif not suggested_analysis['day_match']:
                reason = _('Day mismatch')
            elif suggested.status == 'canceled':
                reason = _('Canceled')
            elif suggested.status and suggested.status != 'sold':
                reason = (
                    self._fuzzy_selection_label(suggested, 'status')
                    or suggested.status
                )
            elif time_mismatch:
                reason = _('Out of Rotation')
            elif length_mismatch:
                reason = _(
                    'Length mismatch: postlog=%(postlog)s, schedule=%(schedule)s'
                ) % {
                    'postlog': (
                        self._fuzzy_parse_length(postlog.length)
                        or ''
                    ),
                    'schedule': (
                        suggested_analysis['schedule_length']
                        or ''
                    ),
                }
            elif ambiguous_count > 1:
                reason = _(
                    '%(count)s equally ranked schedules; review before attaching'
                ) % {'count': ambiguous_count}
            elif not suggested_analysis['exact_time_match']:
                reason = _(
                    'Within fuzzy buffer (%(minutes)s minute(s) from rotation)'
                ) % {'minutes': suggested_analysis['time_distance'] or 0}

        exact_match = bool(
            suggested_analysis
            and suggested.status == 'sold'
            and ambiguous_count <= 1
            and suggested_analysis['network_match']
            and suggested_analysis['deal_match']
            and suggested_analysis['week_match']
            and suggested_analysis['rate_match']
            and suggested_analysis['day_match']
            and suggested_analysis['exact_time_match']
            and suggested_analysis['length_match']
        )

        return {
            'id': postlog.id,
            'name': postlog.display_name or '',
            'network': (
                postlog.broadcast_network
                or postlog.network
                or (program.display_name if program else '')
                or ''
            ),
            'air_date': (
                fields.Date.to_string(postlog.air_date)
                if postlog.air_date
                else ''
            ),
            'day': day,
            'air_time': postlog.air_time or '',
            'length': self._fuzzy_parse_length(postlog.length) or '',
            'rate': postlog.spot_rate or 0.0,
            'week': (
                fields.Date.to_string(postlog.import_week_value)
                if postlog.import_week_value
                else ''
            ),
            'deal_number': postlog.network_deal_number or '',
            'advertiser_product': postlog.product or '',
            'reason': reason or '',
            'suggested': (
                self._fuzzy_schedule_payload(suggested)
                if suggested
                else False
            ),
            'suggestion_attachable': suggestion_attachable,
            'match_quality': 'exact' if exact_match else ('fuzzy' if suggested else ''),
            'match_quality_label': _('Exact') if exact_match else (_('Fuzzy') if suggested else ''),
            'explanation': self._fuzzy_match_explanation(
                suggested_analysis,
                reason,
                ambiguous_count,
            ),
            'ambiguous_count': ambiguous_count,
            'alternatives': alternatives,
            'time_mismatch': time_mismatch,
            'length_mismatch': length_mismatch,
            'rate_mismatch': rate_mismatch,
            'deal_mismatch': deal_mismatch,
            'network_mismatch': network_mismatch,
            'day_mismatch': day_mismatch,
        }

    @api.model
    def _fuzzy_analyze_schedule(
        self,
        postlog,
        program,
        schedule,
        accepted_networks=None,
    ):
        schedule_length = self._fuzzy_schedule_length(schedule)
        postlog_length = self._fuzzy_parse_length(postlog.length)
        time_match, time_distance = self._fuzzy_time_window_analysis(
            postlog.air_time,
            self._fuzzy_selection_label(schedule, 'start_time'),
            self._fuzzy_selection_label(schedule, 'end_time'),
            self._FUZZY_TIME_BUFFER_MINUTES,
        )
        exact_time_match, unused_exact_distance = self._fuzzy_time_window_analysis(
            postlog.air_time,
            self._fuzzy_selection_label(schedule, 'start_time'),
            self._fuzzy_selection_label(schedule, 'end_time'),
            0,
        )
        length_match = postlog_length == schedule_length
        return {
            'schedule': schedule,
            'network_match': self._fuzzy_network_matches(
                postlog,
                program,
                schedule,
                accepted_networks,
            ),
            'deal_match': bool(
                (
                    schedule.deal_parent.network_deal_number
                    or ''
                ).strip()
                == (postlog.network_deal_number or '').strip()
            ),
            'week_match': schedule.week == postlog.import_week_value,
            'rate_match': self._fuzzy_rate_matches(postlog, schedule),
            'day_match': self._fuzzy_day_matches(postlog, schedule),
            'time_match': time_match,
            'exact_time_match': exact_time_match,
            'time_distance': time_distance,
            'length_match': length_match,
            'schedule_length': schedule_length,
        }

    @api.model
    def _fuzzy_match_explanation(self, analysis, reason, ambiguous_count):
        if not analysis:
            return reason or _('No eligible sold schedule was found.')
        parts = []
        if analysis['network_match']:
            parts.append(_('network matches'))
        if analysis['deal_match']:
            parts.append(_('deal matches'))
        if analysis['rate_match']:
            parts.append(_('rate matches'))
        if analysis['day_match']:
            parts.append(_('air day matches'))
        if analysis['exact_time_match']:
            parts.append(_('airtime is inside rotation'))
        elif analysis['time_match']:
            parts.append(
                _('airtime is %(minutes)s minute(s) from rotation')
                % {'minutes': analysis['time_distance'] or 0}
            )
        if analysis['length_match']:
            parts.append(_('length matches'))
        if ambiguous_count > 1:
            parts.append(_('%(count)s schedules are tied') % {'count': ambiguous_count})
        return '; '.join(parts) + (('. ' + reason) if reason else '')

    @api.model
    def _fuzzy_no_suggestion_reason(self, analyses):
        if not analyses:
            return _('No schedules found for deal number')
        network_matches = [
            analysis
            for analysis in analyses
            if analysis['network_match']
        ]
        if not network_matches:
            return _('No network match')
        rate_matches = [
            analysis
            for analysis in network_matches
            if analysis['rate_match']
        ]
        if not rate_matches:
            return _('No rate match')
        day_matches = [
            analysis
            for analysis in rate_matches
            if analysis['day_match']
        ]
        if not day_matches:
            return _('No day match')
        return _('No time match')

    @api.model
    def _fuzzy_analysis_sort_key(self, analysis):
        schedule = analysis['schedule']
        return (
            self._fuzzy_status_priority(schedule.status),
            # Where the postlog physically aired decides which schedule it belongs
            # to: day first, then how far it sat from the rotation. Rate and
            # length are attributes that can be mis-keyed, so they rank *after* -
            # a mis-typed rate on the correct rotation must not push the postlog
            # onto a different rotation that happens to carry the right rate.
            # Note time_match alone cannot separate these, because the 120-minute
            # buffer marks a 22-minute miss as a match; time_distance is what
            # actually discriminates.
            0 if analysis['day_match'] else 1,
            0 if analysis['time_match'] else 1,
            (
                analysis['time_distance']
                if analysis['time_distance'] is not None
                else 10 ** 9
            ),
            0 if analysis['rate_match'] else 1,
            0 if analysis['length_match'] else 1,
            schedule.display_name or '',
            schedule.id,
        )

    @api.model
    def _fuzzy_analysis_quality_key(self, analysis):
        schedule = analysis['schedule']
        return (
            self._fuzzy_status_priority(schedule.status),
            bool(analysis['day_match']),
            bool(analysis['time_match']),
            analysis['time_distance'],
            bool(analysis['rate_match']),
            bool(analysis['length_match']),
        )

    @api.model
    def _fuzzy_alternative_payload(self, analysis):
        """A runner-up schedule plus the checks it fails, for the drawer."""
        payload = self._fuzzy_schedule_payload(analysis['schedule'])
        problems = []
        if not analysis['day_match']:
            problems.append(_('day'))
        if not analysis['time_match']:
            problems.append(_('time'))
        elif analysis['time_distance']:
            problems.append(
                _('%(minutes)s min from rotation')
                % {'minutes': analysis['time_distance']}
            )
        if not analysis['rate_match']:
            problems.append(_('rate'))
        if not analysis['length_match']:
            problems.append(_('length'))
        payload.update({
            'why': ', '.join(problems) or _('matches on every check'),
            'attachable': analysis['schedule'].status == 'sold',
            'exact': bool(
                analysis['day_match']
                and analysis['exact_time_match']
                and analysis['rate_match']
                and analysis['length_match']
            ),
        })
        return payload

    @api.model
    def _fuzzy_schedule_payload(self, schedule):
        if not schedule:
            return False
        days = sorted(
            [
                day.name
                for day in schedule.days_allowed
                if day.name
            ],
            key=lambda value: self._FUZZY_DAY_ORDER.get(
                value[:3].strip().lower(),
                99,
            ),
        )
        start_time = self._fuzzy_selection_label(
            schedule,
            'start_time',
        ) or ''
        end_time = self._fuzzy_selection_label(
            schedule,
            'end_time',
        ) or ''
        return {
            'id': schedule.id,
            'name': schedule.display_name or '',
            'time_range': (
                '%s-%s' % (start_time, end_time)
                if start_time and end_time
                else ''
            ),
            'days_allowed': ', '.join(days),
            'rate': schedule.rate or 0.0,
            'length': self._fuzzy_schedule_length(schedule) or '',
            'deal_number': (
                schedule.deal_parent.network_deal_number
                or ''
            ),
            'network': (
                self._fuzzy_selection_label(schedule, 'networks')
                or ''
            ),
            'status': schedule.status or '',
            'status_label': (
                self._fuzzy_selection_label(schedule, 'status')
                or ''
            ),
        }

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------

    @api.model
    def _fuzzy_network_names(self, program):
        if not program:
            return False
        config = load_program_config(program.display_name)
        config_names = config.get('networkNames', [])
        field_map = config.get('fieldMap', {})
        if not config_names and not field_map.get('network'):
            return False
        names = set()
        for value in config_names:
            normalized = normalize_match_text(value)
            if normalized:
                names.add(normalized)
        program_name = normalize_match_text(program.display_name)
        if program_name:
            names.add(program_name)
        return names

    @api.model
    def _fuzzy_network_matches(
        self,
        postlog,
        program,
        schedule,
        accepted_networks=None,
    ):
        if (
            not program
            or not schedule.deal_parent
            or schedule.deal_parent.program != program
        ):
            return False
        raw_network = normalize_match_text(
            postlog.broadcast_network or postlog.network
        )
        if not raw_network:
            return True
        accepted_networks = (
            accepted_networks
            if accepted_networks is not None
            else self._fuzzy_network_names(program)
        )
        if accepted_networks is False:
            return True
        return raw_network in accepted_networks

    @api.model
    def _fuzzy_resolve_schedule(self, selection):
        Schedule = self.env['mv.schedules']
        schedule = False
        if selection['schedule_id']:
            schedule = Schedule.search(
                [('id', '=', selection['schedule_id'])],
                limit=1,
            )
        reference = selection['schedule_ref']
        if not schedule and reference:
            if reference.isdigit():
                schedule = Schedule.search(
                    [('id', '=', int(reference))],
                    limit=1,
                )
            if not schedule:
                matches = Schedule.search(
                    [('name', '=', reference)],
                    limit=2,
                )
                if len(matches) > 1:
                    return False, _(
                        'Schedule name "%(name)s" is ambiguous; '
                        'enter its numeric Odoo ID.'
                    ) % {'name': reference}
                schedule = matches[:1]
        if not schedule:
            label = reference or selection['schedule_id'] or ''
            return False, (
                _('Schedule not found: %(schedule)s')
                % {'schedule': label}
            )
        return schedule, False

    @api.model
    def _fuzzy_rate_matches(self, postlog, schedule):
        rounding = (
            postlog.currency_id.rounding
            or schedule.currency_id.rounding
            or 0.01
        )
        return float_compare(
            postlog.spot_rate or 0.0,
            schedule.rate or 0.0,
            precision_rounding=rounding,
        ) == 0

    @api.model
    def _fuzzy_day_matches(self, postlog, schedule):
        if not postlog.air_date or not schedule.days_allowed:
            return False
        postlog_day = postlog.air_date.strftime('%a').lower()
        allowed = {
            (day.name or '')[:3].lower()
            for day in schedule.days_allowed
            if day.name
        }
        return postlog_day in allowed

    @api.model
    def _fuzzy_schedule_length(self, schedule):
        if schedule.unitlength not in (None, False, ''):
            try:
                return int(schedule.unitlength)
            except (TypeError, ValueError):
                pass
        if schedule.deal_parent and schedule.deal_parent.length:
            return self._fuzzy_parse_length(
                self._fuzzy_selection_label(
                    schedule.deal_parent,
                    'length',
                )
            )
        return None

    @api.model
    def _fuzzy_time_window_analysis(
        self,
        air_time,
        start_time,
        end_time,
        buffer_minutes=None,
    ):
        """Return ``(inside buffered rotation, minutes from rotation)``.

        The comparison is circular across midnight and uses real minute
        arithmetic instead of Salesforce's HHMM integer approximation.
        """
        buffer_minutes = (
            self._FUZZY_TIME_BUFFER_MINUTES
            if buffer_minutes is None
            else max(self._fuzzy_int(buffer_minutes, default=0), 0)
        )
        air_value = self._fuzzy_parse_time(air_time)
        start_value = self._fuzzy_parse_time(start_time)
        end_value = self._fuzzy_parse_time(end_time)
        if not air_value or not start_value or not end_value:
            return False, None

        air_minutes = (air_value.hour * 60) + air_value.minute
        start_minutes = (start_value.hour * 60) + start_value.minute
        end_minutes = (end_value.hour * 60) + end_value.minute
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60

        distances = []
        for candidate in (
            air_minutes - (24 * 60),
            air_minutes,
            air_minutes + (24 * 60),
        ):
            if start_minutes <= candidate <= end_minutes:
                distance = 0
            else:
                distance = min(
                    abs(candidate - start_minutes),
                    abs(candidate - end_minutes),
                )
            distances.append(distance)
        distance = min(distances)
        return distance <= buffer_minutes, distance

    @staticmethod
    def _fuzzy_parse_time(value):
        if value in (None, False, ''):
            return None
        text = str(value).strip().upper().replace(' ', '')
        if text.endswith('A') and not text.endswith('AM'):
            text += 'M'
        elif text.endswith('P') and not text.endswith('PM'):
            text += 'M'
        for time_format in (
            '%H:%M:%S',
            '%H:%M',
            '%I:%M:%S%p',
            '%I:%M%p',
        ):
            try:
                return datetime.strptime(text, time_format).time()
            except ValueError:
                continue
        return None

    @staticmethod
    def _fuzzy_parse_length(value):
        """Seconds from a length value.

        Diverges from the prelog service: mv.spot_data.length is a Selection
        keyed ``v_60`` where mv.prelog_data.schedulelength is a Char "60", so
        the ``v_`` prefix is stripped before parsing. Plain numeric strings and
        ints still work, which keeps this usable for the schedule side too.
        """
        if value in (None, False, ''):
            return None
        text = str(value).strip()
        if text.lower().startswith('v_'):
            text = text[2:]
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fuzzy_selection_label(record, field_name):
        if not record or not record[field_name]:
            return False
        selection = record._fields[field_name].selection
        if callable(selection):
            selection = selection(record.env)
        return dict(selection).get(record[field_name], record[field_name])

    @staticmethod
    def _fuzzy_status_priority(status):
        return {
            'sold': 0,
            'sold_unflighted': 1,
            False: 2,
            'canceled': 3,
        }.get(status, 2)

    @staticmethod
    def _fuzzy_csv_row(values):
        safe_values = []
        for value in values:
            if (
                isinstance(value, str)
                and value.lstrip().startswith(('=', '+', '-', '@'))
            ):
                value = "'%s" % value
            safe_values.append(value)
        return safe_values

    @staticmethod
    def _fuzzy_int(value, default=False):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
