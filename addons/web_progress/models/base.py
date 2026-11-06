# Part of web_progress. See LICENSE file for full copyright and licensing details.
from odoo import models, api, registry, fields, _
import logging

_logger = logging.getLogger(__name__)


class GeneratorWithLenIndexable(object):
    """
    A class that mimics a generator, but also supports length and indexing
    """

    def __init__(self, gen, length, data):
        self.gen = gen
        self.length = length
        self.data = data

    def __len__(self):
        return self.length

    def __iter__(self):
        return self.gen

    def __getitem__(self, key):
        return self.data.__getitem__(key)

    def __getattr__(self, key):
        return getattr(self.data, key)


class Base(models.AbstractModel):
    _inherit = 'base'

    #
    # Progress reporting
    #

    def with_progress(self, msg='', total=None, cancellable=True, log_level="info"):
        """
        Wrap self (current recordset) with progress reporting generator
        :param msg: msg to mass in progress report
        :param total: provide total directly to avoid calling len on data (which fails on generators)
        :param cancellable: indicates whether the operation is cancellable
        :param log_level: log level to use when logging progress
        :return: yields every element of data
        """
        return self.web_progress_iter(self, msg=msg, total=total, cancellable=cancellable, log_level=log_level)

    @api.model
    def web_progress_percent(self, percent, msg='', cancellable=True, log_level="info"):
        """
        Report progress of an ongoing operation identified by progress_code in context.
        :param percent: progress in percent
        :param msg: progress message
        :param cancellable: indicates whether the operation is cancellable
        :param log_level: log level to use when logging progress
        :return: None
        """
        code = self.env.context.get('progress_code')
        if not code:
            return
        web_progress_obj = self.env['web.progress']
        percent = max(min(percent, 100), 0)
        recur_depth = web_progress_obj._get_recur_depth(code)
        params = dict(code=code,
                      progress=percent,
                      done=percent,
                      total=100,
                      state=percent >= 100 and 'done' or 'ongoing',
                      msg=msg,
                      recur_depth=recur_depth,
                      cancellable=cancellable,
                      log_level=log_level)
        if percent >= 100:
            web_progress_obj._report_progress_done(params)
        else:
            web_progress_obj._report_progress_do_percent(params)

    @api.model
    def web_progress_iter(self, data, msg='', total=None, cancellable=True, log_level="info"):
        """
        Progress reporting generator of an ongoing operation identified by progress_code in context.
        :param data: collection / generator to iterate onto
        :param msg: msg to mass in progress report
        :param total: provide total directly to avoid calling len on data (which fails on generators)
        :param cancellable: indicates whether the operation is cancellable
        :param log_level: log level to use when logging progress
        :return: yields every element of data
        """
        if not self.env.context.get('progress_code'):
            return data
        if total is None:
            try:
                total = len(data)
            except:
                # impossible to get total, so no way to show progress
                return data
        return GeneratorWithLenIndexable(self.env['web.progress']._report_progress(data,
                                                                                   msg=msg,
                                                                                   total=total,
                                                                                   cancellable=cancellable,
                                                                                   log_level=log_level),
                                         total,
                                         data)

    def web_progress_cancel(self, code=None):
        """
        Cancel progress of current operation or, if code given by argument, an operation of a given progress code
        :param code:
        """
        if code is None:
            code = self._context.get('progress_code', None)
        if code is not None:
            self.env['web.progress'].cancel_progress(code)

    #
    # Add progress reporting to common time-consuming collections
    #

    def __iter__(self):
        """
        Add progress report to recordset iteration when progress_iter is in the context
        """
        if self._context.get('progress_iter'):
            self = self.with_context(progress_iter=False)
            return self.web_progress_iter(self, _("Iterating on model {}").format(self._description)).__iter__()
        else:
            return super(Base, self).__iter__()

    @api.model
    def _extract_records(self, fields_, data, log=lambda a: None, limit=float('inf')):
        """
        Add progress reporting to collection used in base_import.import
        It adds progress reporting to all standard imports and additionally makes them cancellable
        """
        extracted = super(Base, self)._extract_records(fields_, data, log=log, limit=limit)
        if 'progress_code' in self._context:
            total = min(limit, len(data) - len(self._context.get('skip_records', [])))
            return self.web_progress_iter(extracted, _("importing to {}").
                                          format(self._description.lower()), total=total, cancellable=True,
                                          log_level="info")
        else:
            return extracted

    def _export_rows(self, fields, *args, _is_toplevel_call=True):
        """
        Add progress reporting to base export (on batch-level)
        """
        if _is_toplevel_call and 'progress_code' in self._context:
            def splittor(rs):
                """ Splits the self recordset in batches of 1000 (to avoid
                entire-recordset-prefetch-effects) & removes the previous batch
                from the cache after it's been iterated in full
                """
                for idx in self.web_progress_iter(range(0, len(rs), 1000), _("exporting batches of 1000 lines") +
                                                                           " ({})".format(self._description)):
                    sub = rs[idx:idx + 1000]
                    yield sub
                    sub.invalidate_recordset()

            ret = []
            for sub in splittor(self):
                ret += super(Base, sub)._export_rows(fields, _is_toplevel_call=_is_toplevel_call)
            return ret
        return super(Base, self)._export_rows(fields, _is_toplevel_call=_is_toplevel_call)
