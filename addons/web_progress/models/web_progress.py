# Part of web_progress. See LICENSE file for full copyright and licensing details.
from odoo import models, api, registry, fields, _, SUPERUSER_ID
from odoo.exceptions import UserError
from threading import RLock
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import contextmanager
import html
import odoo
import json
import logging

_logger = logging.getLogger(__name__)
lock = RLock()
# track time between progress reports
last_report_time = {}
# track time from the beginnig
first_report_time = {}
# store recursion depth for every operation
recur_depths = {}
# progress reports data
progress_data = defaultdict(dict)
# user name
user_name = {}


def json_dump(v):
    return json.dumps(v, separators=(',', ':'))


class CancelledProgress(models.UserError):
    # exception used to cancel the execution
    pass


class RestoreEnvToComputeToWrite(Exception):
    """
    Used to restore the towrite and to compute of an old env
    """

class WebProgress(models.TransientModel):
    _name = 'web.progress'
    _description = "Operation Progress"
    _transient_max_hours = 0.5
    # time between progress reports (in seconds)
    _progress_period_secs = 5

    msg = fields.Char("Message")
    code = fields.Char("Code", required=True, index=True)
    recur_depth = fields.Integer("Recursion depth", index=True, default=0)
    progress = fields.Integer("Progress")
    progress_total = fields.Float("Progress Total")
    done = fields.Integer("Done")
    total = fields.Integer("Total")
    time_left = fields.Char("Time Left")
    time_total = fields.Char("Time Total")
    time_elapsed = fields.Char("Elapsed Time")
    state = fields.Selection([('ongoing', "Ongoing"),
                              ('done', "Done"),
                              ('cancel', "Cancelled"),
                              ], "State")
    cancellable = fields.Boolean("Cancellable")

    #
    # Called by web client
    #

    @api.model
    def cancel_progress(self, code=None):
        """
        Register cancelled operation
        :param code: web progress code
        """
        vals = {
            'code': code,
            'state': 'cancel',
        }
        _logger.info('Cancelling progress {}'.format(code))
        self._create_progress([vals], notify=False)

    @api.model
    def get_user_name(self, code):
        """
        Cache user name to avoid SELECT queries touching potentially locked tables
        res_users and res_partner on progress reporting.
        :param user_id: (int) ID of res.users record
        :return: (str) User Name
        """
        with lock:
            # use cached user name
            return user_name.get(code, '')

    @api.model
    def get_progress_rpc(self, code=None):
        """
        External call to get progress for given code
        :param code: web progress code
        """
        with registry(self.env.cr.dbname).cursor() as new_cr:
            # Create a new environment with new cursor database
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            # with_env replace original env for this method
            progress_obj = self.with_env(new_env)
            return progress_obj.get_progress(code)

    @api.model
    def get_progress(self, code=None, recur_depth=None):
        """
        Get progress for given code
        :param code: web progress code
        :param recur_depth: recursion depth
        """
        result = []
        domain = []
        if recur_depth is not None:
            domain.append(('recur_depth', '=', recur_depth))
        if code:
            domain.append(('code', '=', code))
        if domain:
            progress_id = self.search(domain, order='create_date DESC,recur_depth DESC', limit=1)
        else:
            progress_id = self.env[self._name]
        # check progress of parent operations
        if recur_depth is None and progress_id.recur_depth:
            for parent_depth in range(progress_id.recur_depth):
                result += self.get_progress(code, recur_depth=parent_depth)
        progress_vals = {
            'msg': html.escape(progress_id.msg or ''),
            'code': progress_id.code,
            'progress': progress_id.progress,
            'progress_total': progress_id.progress_total,
            'done': progress_id.done,
            'total': progress_id.total,
            'time_left': progress_id.time_left,
            'time_total': progress_id.time_total,
            'time_elapsed': progress_id.time_elapsed,
            'state': progress_id.state,
            'cancellable': progress_id.cancellable,
            'uid': progress_id.create_uid.id,
            'user': self.get_user_name(code) or progress_id.create_uid.name,
        }
        # register this operation progress
        result.append(progress_vals)

        return result

    @api.model
    def is_progress_admin(self, user_id=None):
        """
        Check if the current user (or a user given by parameter)
        has progress admin credentials.
        :return:
        """
        if not user_id:
            user_id = self.env.user
        # superuser and users being in group system are progress admins
        return user_id._is_superuser() or user_id._is_system()

    @api.model
    def get_all_progress(self, recency=_progress_period_secs * 2):
        """
        Get progress information for all ongoing operations
        :param recency: (int) seconds back
        :return list of progress codes
        """
        query = """
        SELECT code, array_agg(state) FROM web_progress
        WHERE create_date > timezone('utc', now()) - INTERVAL '%s SECOND'
              AND recur_depth = 0 {user_id}
        GROUP BY code
        """.format(
            recency=recency or 0,
            user_id=not self.is_progress_admin() and "AND create_uid = {user_id}"
                .format(
                user_id=self.env.user.id,
            ) or '')
        # superuser has right to see (and cancel) progress of everybody
        self.env.cr.execute(query, (recency, ))
        result = self.env.cr.fetchall()
        ret = [{
            'code': r[0],
        } for r in result if r[0] and 'cancel' not in r[1] and 'done' not in r[1]]
        return ret

    #
    # Protected members called by backend
    # Do not call them directly
    #

    @api.model
    def _report_progress(self, data, msg='', total=None, cancellable=True, log_level="info"):
        """
        Progress reporting generator
        :param data: collection / generator to iterate onto
        :param msg: msg to mass in progress report
        :param total: provide total directly to avoid calling len on data (which fails on generators)
        :param cancellable: indicates whether the operation is cancellable
        :param log_level: log level to use when logging progress
        :return: yields every element of iteration
        """
        global recur_depths
        # web progress_code typically comes from web client in call context
        code = self.env.context.get('progress_code')
        if total is None:
            total = len(data)
        if not code or total <= 1:
            # no progress reporting when no code and for singletons
            for elem in data:
                yield elem
            return
        with lock:
            recur_depth = self._get_recur_depth(code)
            if recur_depth:
                recur_depths[code] += 1
            else:
                recur_depths[code] = 1
            # cache user name at the beginning of the base-level progress
                user_name[code] = self.env.user.name
        params = dict(done=0, progress=0.0, state='ongoing', code=code, total=total, msg=msg, recur_depth=recur_depth,
                          cancellable=cancellable, log_level=log_level)
        precise_code = self._get_precise_code(params)
        with lock:
            progress_data[precise_code] = dict(params)
        try:
            for done, rec in zip(range(total), data):
                params['done'] = done
                params['progress'] = round(100 * done / total, 2)
                params['state'] = done >= total and 'done' or 'ongoing'
                self._report_progress_do_percent(params)
                yield rec
        finally:
            # finally record progress as finished
            self._report_progress_done(params)
            with lock:
                recur_depths[code] -= 1
                if not recur_depths[code]:
                    del recur_depths[code]
                    # destroy user name only at the end of the base-level progress
                    if code in user_name:
                        del user_name[code]

    @api.model
    def _get_recur_depth(self, code):
        """
        Get current recursion depth
        :param code: web progress code
        :return: current recursion depth
        """
        global recur_depths
        with lock:
            recur_depth = recur_depths.get(code, 0)
        return recur_depth

    @api.model
    def _create_progress(self, vals_list, notify=True):
        """
        Create a web progress record
        Creation uses a fresh cursor, i.e. outside the current transaction scope
        :param vals: list of creation vals
        :return: None
        """
        if not vals_list:
            return
        code = vals_list[0].get('code')
        try:
            with registry(self.env.cr.dbname).cursor() as new_cr:
                # Create a new environment with a new cursor
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                # clear whatever is to be computed or written
                # it will be restored later on
                new_env.clear()
                # with_env replaces the original env for this method
                progress_obj = self.with_env(new_env)
                progress_obj.create(vals_list)
                # notify bus
                if notify:
                    progress_notif = progress_obj.get_progress(code)
                    new_env['bus.bus']._sendone('web_progress', 'web_progress', progress_notif)
                # isolated transaction to commit
                new_env.cr.commit()
                # restore main transaction's data
                raise RestoreEnvToComputeToWrite
        except RestoreEnvToComputeToWrite:
            pass

    @api.model
    def _check_cancelled(self, params):
        """
        Check if operation was not cancelled by the user or progress admin.
        The check is executed using a fresh cursor, i.e., it looks outside the current transaction scope
        :param code: web progress code
        :return: (recordset) res.users of the user that cancelled the operation
        """
        code = params.get('code')
        with registry(self.env.cr.dbname).cursor() as new_cr:
            # use new cursor to check for cancel
            query = """
            SELECT create_uid FROM web_progress
            WHERE code = %s AND state = 'cancel' AND recur_depth = 0
                
            """
            new_cr.execute(query, (code, ))
            result = new_cr.fetchall()
            if result:
                user_id = self.create_uid.browse(result[0])
                if self.env.user == user_id or self.is_progress_admin(user_id):
                    return user_id
        return False

    def _get_parent_codes(self, params):
        """
        Get list of precise codes of all parents
        """
        code = params.get('code')
        return [code + '##' + str(d) for d in range(params.get('recur_depth'))]

    def _get_precise_code(self, params):
        """
        Get precise code, i.e. progress code + recurency depth level
        """
        return params.get('code') + '##' + str(params.get('recur_depth'))

    def _format_time(self, seconds):
        """
        Format seconds in h:mm:ss format
        :param seconds: number of seconds
        :return: (str) time left in h:mm:ss format
        """
        ts_min, ts_sec = divmod(int(seconds), 60)
        ts_hour, ts_min = divmod(ts_min, 60)
        ret = "{}:{:0>2d}:{:0>2d}".format(ts_hour, ts_min, ts_sec)
        return ret

    def _get_time_left(self, params, time_now, first_ts):
        """
        Compute est. time left and total
        :param params: params of progress
        :param time_now: datetime of now
        :param first_ts: datetime of first progress report
        :return: (pair of str) time left in h:mm:ss format and time total of operation
        """
        time_left = ''
        time_total = ''
        time_elapsed = ''
        if first_ts:
            pogress_total = params.get('progress_total', 0)
            if pogress_total > 0:
                time_per_percent = (time_now - first_ts) / pogress_total
                progress_left = 100.0 - pogress_total
                time_left = self._format_time(progress_left * time_per_percent.total_seconds())
                time_total = self._format_time(100.0 * time_per_percent.total_seconds())
                time_elapsed = self._format_time((time_now - first_ts).total_seconds())
        return time_left, time_total, time_elapsed

    def _get_progress_total(self, params):
        """
        Get total progress taking into account all progress recur depths
        :return: (float) real progress
        """
        global progress_data
        codes = self._get_parent_codes(params)
        codes.append(self._get_precise_code(params))
        progress_total = 0.0
        progress_depth = 100.0
        for precise_code in codes:
            with lock:
                params_prec = progress_data.get(precise_code)
            if not params_prec or 'done' not in params_prec or 'total' not in params_prec or params_prec['total'] == 0:
                continue
            progress_total += float(params_prec['progress']) * progress_depth / 100
            progress_depth /= params_prec['total']
        return progress_total

    def _set_attrib_for_all(self, params, attrib, value):
        """
        Set value of an attrbute to params in all recur depth levels
        :param params: params to identify code and depth
        :param attrib: name of attribute to change
        :param value: value of attribute to change
        """
        global progress_data
        codes = self._get_parent_codes(params)
        codes.append(self._get_precise_code(params))
        with lock:
            params[attrib] = value
            with lock:
                for precise_code in codes:
                    progress_data[precise_code][attrib] = value

    def _report_progress_do_percent(self, params):
        """
        Progress reporting function
        At the moment this only logs the progress.
        :param params: dict with parameters:
            done: how much items processed
            total: total of items to process
            msg: message for progress report
            recur_depth: recursion depth
            cancellable: indicates whether the operation is cancellable
        :return: None
        """
        # check the time from last progress report
        global last_report_time, first_report_time, progress_data
        code = params.get('code')
        precise_code = self._get_precise_code(params)
        time_now = datetime.now()
        with lock:
            first_ts = first_report_time.get(code)
            if not first_ts:
                first_report_time[code] = time_now
            last_ts = last_report_time.get(code)
            if not last_ts:
                last_ts = (time_now - timedelta(seconds=self._progress_period_secs + 1))
            progress_data[precise_code] = dict(params)
            progress_total = self._get_progress_total(params)
            self._set_attrib_for_all(params, 'progress_total', progress_total)
        period_sec = (time_now - last_ts).total_seconds()
        # report progress every time period
        if period_sec >= self._progress_period_secs:
            if params.get('cancellable', True):
                user_id = self._check_cancelled(params)
                if user_id:
                    raise CancelledProgress(_("Operation has been cancelled by") + " " + user_id.sudo().name)
            time_left, time_total, time_elapsed = self._get_time_left(params, time_now, first_ts)
            if time_left:
                self._set_attrib_for_all(params, 'time_left', time_left)
            if time_total:
                self._set_attrib_for_all(params, 'time_total', time_total)
            if time_elapsed:
                self._set_attrib_for_all(params, 'time_elapsed', time_elapsed)
            self._report_progress_store(params)
            with lock:
                last_report_time[code] = time_now

    def _report_progress_done(self, params):
        """
        Report progress as done.
        :param code: progress operation code
        :param total: total units
        :param msg: logging message
        :param recur_depth: recursion depth
        :param cancellable: indicates whether the operation is cancellable
        :return:
        """
        global progress_data
        precise_code = self._get_precise_code(params)
        params['progress'] = 100
        params['done'] = params['total']
        params['state'] = 'done'
        code = params.get('code')
        if params.get('recur_depth'):
            # done sub-level progress, lazy report
            ret = self._report_progress_do_percent(params)
        else:
            # done main-level progress, report immediately
            progress_data[precise_code] = dict(params)
            ret = self._report_progress_store(params)
            with lock:
                # remove last report time for this code
                if code in last_report_time:
                    del last_report_time[code]
                if code in first_report_time:
                    del first_report_time[code]
        # remove data for this precise code code
        with lock:
            if precise_code in progress_data:
                del progress_data[precise_code]
        return ret

    def _report_progress_prepare_vals(self, params):
        """
        Filter out all params that are not web.progress fields
        """
        vals = {k: v for k, v in params.items() if k in self._fields}
        return vals

    def _report_progress_store(self, params):
        """
        Progress storing function. Stores progress in log and in db.
        :param code: progress operation code
        :param percent: done percent
        :param done: done units
        :param total: total units
        :param msg: logging message
        :param recur_depth: recursion depth
        :param cancellable: indicates whether the operation is cancellable
        :param state: state of progress: ongoing or done
        """
        global progress_data
        codes = self._get_parent_codes(params)
        codes.append(self._get_precise_code(params))
        vals_list = []
        first_line = True
        for precise_code in codes:
            with lock:
                my_progress_data = progress_data.get(precise_code)
            if not my_progress_data:
                continue
            log_message = "Progress {code} {level} {progress}% ({done}/{total}) {msg}".format(
                level=(">" * (my_progress_data.get('recur_depth') + 1)),
                **my_progress_data)
            log_level = my_progress_data.get('log_level')
            if hasattr(_logger, log_level):
                logger_cmd = getattr(_logger, log_level)
            else:
                logger_cmd = _logger.info
            if first_line and "progress_total" in my_progress_data:
                log_message_pre = \
                    "Progress {code} total {progress_total:.02f}%".format(**my_progress_data)
                if "time_left" in my_progress_data:
                    log_message_pre += ", est. time left {}".format(my_progress_data.get('time_left'))
                if "time_total" in my_progress_data:
                    log_message_pre += ", est. time total {}".format(my_progress_data.get('time_total'))
                if "time_elapsed" in my_progress_data:
                    log_message_pre += ", elapsed time {}".format(my_progress_data.get('time_elapsed'))
                logger_cmd(log_message_pre)
            logger_cmd(log_message)
            vals_list.append(self._report_progress_prepare_vals(my_progress_data))
            first_line = False
        self._create_progress(vals_list)
