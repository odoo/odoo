from __future__ import annotations

import inspect

from odoo import api, models
from odoo.exceptions import ValidationError


def report_section(*, id=None, parent=None, sequence=1, name=None, foldability="collapsed"):
    """Decorator for defining a report section.

    :param str id: Unique section ID (required).
    :param str parent: Parent section ID, if nested.
    :param str name: Section display name.
    :param int sequence: Display order.
    :param str foldability: "static", "collapsed", or "expanded".
    """
    if not id:
        msg = "report_section: 'id' is required."
        raise ValueError(msg)

    def decorator(fn):
        fn._rs_id = id
        fn._rs_name = name
        fn._rs_parent = parent
        fn._rs_sequence = sequence
        fn._rs_foldability = foldability
        return fn

    return decorator


class PosReportHandler(models.AbstractModel):
    _name = 'pos.report.handler'
    _description = 'POS Report Handler'

    def _get_filters(self):
        return []

    def _get_currency(self):
        return self.env.company.currency_id

    def _get_sections_columns(self):
        return {}

    def _get_report_name(self, default_name):
        """Report title for the current context."""
        return default_name

    def _get_pdf_templates(self):
        """Return QWeb template ids overriding individual PDF fragments."""
        return {}

    def _get_xlsx_section_columns(self, section):
        """Columns used to render ``section`` in the XLSX export."""
        return section.get('columns') or self._get_sections_columns().get(section.get('section_id', ''), [])

    def _get_xlsx_row_value(self, line, column):
        """Value written for ``line`` under ``column``; overridable per report."""
        return (line.get('values') or {}).get(column.get('id', ''))

    def _get_sections_data(self):
        """Return section data with metadata (columns, foldability, etc.)"""
        sections = []
        columns_by_section = self._get_sections_columns()
        for fn in self._get_section_methods():
            lines = fn(self)
            normalized = self._normalize_lines(fn, lines)
            if not normalized:
                continue

            for line in normalized:
                line['columns'] = columns_by_section.get(fn._rs_id, [])
                should_expand = (
                    self.env.context.get('unfold_all', False) or line.get('foldability') == 'expanded'
                )
                if should_expand:
                    line['lines'] = self._get_children_for_section(fn._rs_id, record_id=line.get('record_id'))
                sections.append(line)
        return sections

    def _get_children_for_section(self, section_id, record_id=None):
        """Recursively fetch and expand all children of the given section."""
        children = self._get_unfold_lines(section_id, record_id)
        if not children:
            return []

        for child in children:
            should_expand = (
                self.env.context.get('unfold_all', False) or child.get('foldability') == 'expanded'
            )
            if should_expand:
                child['lines'] = self._get_children_for_section(child.get('section_id'), record_id=child.get('record_id'))

        return children

    def _get_unfold_lines(self, section_id, record_id=None):
        children = self._get_section_methods(section_id)
        if not children:
            return []

        handler = self.with_context(record_id=record_id) if record_id else self

        result = []
        for fn in children:
            result.extend(self._normalize_lines(fn, fn(handler)))
        return result

    @api.ormcache('parent_section_id', cache='stable')
    def _get_section_methods(self, parent_section_id=None):
        sections = [
            method
            for _, method in inspect.getmembers(self.__class__, inspect.isfunction)
            if hasattr(method, '_rs_id')
        ]

        if parent_section_id is not None:
            return sorted(
                (method for method in sections if method._rs_parent == parent_section_id),
                key=lambda method: method._rs_sequence,
            )

        return sorted(
            (method for method in sections if method._rs_parent is None),
            key=lambda method: method._rs_sequence,
        )

    @staticmethod
    def _normalize_lines(fn, lines):
        """Normalize and shape lines returned by a section method"""
        if lines is None:
            return []
        if not isinstance(lines, list):
            lines = [lines]

        structural_keys = {
            'record_id', 'section_id', 'name',
            'foldability', 'style', 'sequence', 'lines', 'columns',
        }
        result = []
        for line in lines:
            result.append({
                'section_id': fn._rs_id,
                'record_id': line.get('record_id'),
                'name': line.get('name', fn._rs_name),
                'sequence': line.get('sequence', fn._rs_sequence),
                'foldability': line.get('foldability', fn._rs_foldability),
                'style': line.get('style'),
                'values': {k: v for k, v in line.items() if k not in structural_keys},
                'lines': [],
            })
        return result

    def _register_hook(self):
        self._validate_sections()
        return super()._register_hook()

    def _validate_sections(self):
        sections = {}
        for _, fn in inspect.getmembers(self.__class__, inspect.isfunction):
            if not hasattr(fn, '_rs_id'):
                continue

            sid = fn._rs_id
            if sid in sections:
                raise ValidationError(
                    "Duplicate section ID '%s' found on method '%s'." % (sid, fn.__name__),
                )
            sections[sid] = fn

        for sid, fn in sections.items():
            parent = fn._rs_parent

            if parent is not None and parent not in sections:
                raise ValidationError(
                    "Section '%s' (method '%s') references parent '%s' which does not exist."
                    % (sid, fn.__name__, parent),
                )
