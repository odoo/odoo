"""Aggregate collector samples and format benchmark results."""

import logging

from . import collectors
from .collectors import validate_values

logger = logging.getLogger('odoo.benchmark')
stats_logger = logging.getLogger('odoo.benchmark.stats')


class Result:
    """Aggregate one benchmark key's measured samples using each collector's policy.

    Expose metric descriptions, aggregated values, requested ranges and warnings
    for reporting. Construction validates and aggregates without logging;
    publish() emits statistics and warnings once the whole benchmark succeeds.
    """

    def __init__(self, key, samples):
        self.key = key
        self.samples = samples
        self.rounds = len(samples)
        if not samples:
            msg = 'Benchmark results require at least one sample'
            raise ValueError(msg)

        # Aggregation uses fresh instances; collection state belongs to one round.
        instances = tuple(factory() for factory in collectors.COLLECTORS)
        self.descriptions = tuple(metric for collector in instances for metric in collector.metrics)
        for sample in samples:
            validate_values(sample, self.descriptions, 'sample')

        self.metrics = {}
        self.warnings = []
        for collector in instances:
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
        stats_logger.info('benchmark %s rounds=%s %s', self.key, self.rounds, fields)
        for warning in self.warnings:
            logger.warning('%s for %s', warning, self.key)


def format_results_table(results):
    """Format an aligned Markdown table from the results' metric descriptions."""
    show_range = any(result.rounds > 1 for result in results)
    metrics = results[0].descriptions
    headers = ['key', 'rounds']
    for metric in metrics:
        header = f'{metric.label} {metric.unit}'.strip()
        headers.append(header)
        if show_range and metric.show_range:
            headers.append(f'{header} min-max')
    rows = [headers]
    for result in results:
        row = [result.key, str(result.rounds)]
        for metric in metrics:
            row.append(metric.format(result.metrics[metric.key]))
            if show_range and metric.show_range:
                row.append('-' if result.rounds == 1 else '-'.join(map(metric.format, result.ranges[metric.key])))
        rows.append(row)
    rows = [[cell.replace('\\', '\\\\').replace('|', '\\|').replace('\n', ' ') for cell in row] for row in rows]
    widths = [max(3, *map(len, column)) for column in zip(*rows)]
    rows.insert(1, ['-' * width for width in widths])
    return '\n'.join('| ' + ' | '.join(f'{cell:<{width}}' for cell, width in zip(row, widths)) + ' |' for row in rows)
