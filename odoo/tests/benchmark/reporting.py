"""Aggregate collector samples and format benchmark results."""

import logging

from .collectors import validate_values

_logger = logging.getLogger('odoo.benchmark')
_logger_stats = logging.getLogger('odoo.benchmark.stats')


class Result:
    """Represents samples and summary statistics for one test or named measurement block."""

    def __init__(self, key, samples, collectors):
        self.key = key
        self.samples = samples
        self.rounds = len(samples)
        if not samples:
            msg = 'Benchmark results require at least one sample'
            raise ValueError(msg)

        self.descriptions = tuple(metric for collector in collectors for metric in collector.metrics)
        for sample in samples:
            validate_values(sample, self.descriptions, 'sample')

        self.metrics = {}
        self.warnings = []
        for collector in collectors:
            collected = [{metric.key: sample[metric.key] for metric in collector.metrics} for sample in samples]
            aggregated = collector.aggregate(collected)
            validate_values(aggregated.values, collector.metrics, collector.name)
            self.metrics.update(aggregated.values)
            self.warnings.extend(aggregated.warnings)

        self.ranges = {
            metric.key: (min(sample[metric.key] for sample in samples), max(sample[metric.key] for sample in samples))
            for metric in self.descriptions if metric.show_range
        }

    def publish(self):
        fields = ' '.join(
            f'{metric.key}={metric.format(self.metrics[metric.key])}'
            for metric in self.descriptions
        )
        _logger_stats.info('benchmark %s rounds=%s %s', self.key, self.rounds, fields)
        for warning in self.warnings:
            _logger.warning('%s for %s', warning, self.key)


def format_results_table(results):
    """Display benchmark summaries as a Markdown table."""
    groups = {}
    for result in results:
        test, _, user = result.key.partition('@')
        test, _, scope = test.partition('#')
        context, separator, method = test.rpartition('.')
        if not separator:
            method = test
        label = (f'#{scope}' if scope else '') + (f'@{user}' if user else '')
        groups.setdefault(context, {}).setdefault(method, []).append((label, result))

    tables = []
    for context, methods in groups.items():
        class_results = [result for measurements in methods.values() for _, result in measurements]
        show_range = any(result.rounds > 1 for result in class_results)
        metrics = class_results[0].descriptions
        headers = ['measurement', 'rounds']
        for metric in metrics:
            header = f'{metric.label} {metric.unit}'.strip()
            headers.append(header)
            if show_range and metric.show_range:
                headers.append(f'{header} min-max')
        rows = [headers]
        for method, measurements in methods.items():
            if any(label for label, _ in measurements):
                rows.append([method] + [''] * (len(headers) - 1))
            for label, result in measurements:
                row = [f'↳ {label}' if label else method, str(result.rounds)]
                for metric in metrics:
                    row.append(metric.format(result.metrics[metric.key]))
                    if show_range and metric.show_range:
                        row.append('-' if result.rounds == 1 else '-'.join(map(metric.format, result.ranges[metric.key])))
                rows.append(row)
        table = _format_table(rows)
        if context:
            # Keep the shared path outside the grid so it does not widen the columns.
            heading = context.removeprefix('benchmark/').replace(':', ' / ', 1)
            table = f'{heading}\n\n{table}'
        tables.append(table)
    return '\n\n'.join(tables)


def _format_table(rows):
    rows = [[cell.replace('\\', '\\\\').replace('|', '\\|').replace('\n', ' ') for cell in row] for row in rows]
    widths = [max(3, *map(len, column)) for column in zip(*rows)]
    rows.insert(1, ['-' * width for width in widths])
    return '\n'.join('| ' + ' | '.join(f'{cell:<{width}}' for cell, width in zip(row, widths)) + ' |' for row in rows)
