# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Transaction commit-related utilities.

In general, in Odoo code commit() should never be called.
There are some exceptions, like ir.cron runs where you want to commit during
the run. It may be error prone, this module standardises this.
In other cases, you may use `cr.savepoint()` instead.
"""

import datetime
import logging
import threading

from odoo.exceptions import ValidationError
from odoo.models import Model
from odoo.osv import expression

from .misc import split_every

LOG_FREQUENCY = datetime.timedelta(seconds=5)
MAX_SEARCH_RECORDS = 1000


def auto_commit(env):
    """Returns either commit() or flush_all() depending on the context"""
    should_commit = bool(
        env.context.get('auto_commit', True)
        # not env.registry.in_test_mode()  # not needed, since test mode handles commits
        and not getattr(threading.current_thread(), 'testing', False)
    )
    return env.cr.commit if should_commit else env.flush_all


def make_limit_checker(limit, visited=None):
    """Create a function that will check if we should stop running the loop

    :param limit: The limit can be an integer, len(visited) < limit;
                  A timedelta or a datetime until when the condition is true;
                  A callable is returned as-is.
    """
    if callable(limit):
        return limit
    # check the limit of visited items
    if isinstance(limit, int) and visited is not None and limit > 0:
        return lambda: len(visited) < limit
    # time-based limit
    if isinstance(limit, datetime.timedelta):
        limit = datetime.datetime.now() + limit
    if isinstance(limit, datetime.datetime):
        return lambda: datetime.datetime.now() < limit
    # no-limit
    return lambda: True


def generic_commit_loop(
    method,
    domain,
    order=None,
    *,
    additional_domain=[],
    limit=None,
    lock="lock",
    log=None,
    values=None,
    values_err=None,
):
    """Process records in a commit loop using a method

    At each loop, we search one record to process that we haven't processed
    yet. We call the method for that record.
    If successful, we write values. If not, we either raise the error or
    write values_err.
    Finally, we auto commit.
    The next loop will re-execute the search, additionnally ignoring
    already-processed ids when no values are given.

    :param method: The method to call for a recordset
    :param domain: Search domain checked before starting
    :param order: The order for the search
    :param additional_domain: Additional domain for the search (default: [])
    :param limit: (int | timedelta | callable | None) Limiter for the loop
    :param lock: Whether to lock records before processing (default: "lock")
                 Can by "try" to skip locked records. Or empty to skip locking.
    :param log: Logger
    :param values: (dict | (rec, result) -> dict) Values to write after the method is called
    :param values_err: (dict | (rec, e) -> dict) Values to write if an exception occurred
    """
    try:
        model = method.__self__.browse()
        method = method.__func__
    except AttributeError:
        raise ValueError("The passed method must be a method bound to a model")
    loop_name = f"{model._name}.{method.__name__}"
    if log is None:
        log = logging.getLogger(__name__)
    search_domain = expression.AND([domain, additional_domain])
    visited = []
    can_continue = make_limit_checker(limit, visited)
    commit = auto_commit(model.env)
    commit()  # make sure we start a new transaction already here

    def record_fetching_checked():
        int_limit = limit if isinstance(limit, int) else None
        failed_lock = []
        while all_records := model.search(
            [('id', 'not in', visited + failed_lock), *search_domain],
            limit=min(int_limit, MAX_SEARCH_RECORDS) if int_limit else MAX_SEARCH_RECORDS,
            order=order,
        ):
            for record in all_records:
                if lock == 'try':
                    # try locking the record, otherwise skip it
                    record = (try_record := record).exists_lock(try_lock=True)
                    if not record:
                        failed_lock.append(try_record.id)
                        continue
                elif lock:
                    # check and lock the record
                    record = record.exists_lock()
                else:
                    # browse to avoid pre-fetching other records
                    record = record.browse(record.id)
                # re-check the domain at each loop
                record = record.filtered_domain(domain)
                if not record:
                    continue
                elif int_limit is not None:
                    int_limit -= 1
                yield record
            # check limit
            if int_limit is not None and int_limit <= 0:
                break

    log.debug("%s: start, domain %s", loop_name, search_domain)
    record_gen = record_fetching_checked()
    error_count = 0
    now = datetime.datetime.now
    log_at = now() + LOG_FREQUENCY
    for record in record_gen:
        info = {
            'start': now(),
            'log': log,
        }
        record = record.ensure_one().with_context(generic_loop_info=info)
        try:
            with record.env.cr.savepoint():
                log.debug("%s: process %s", loop_name, record)
                result = method(record)
                info['end'] = now()
                if result is not None:
                    log.debug("%s: result %s", loop_name, result)
                if values:
                    if callable(values):
                        write_values = values(record, result)
                    else:
                        write_values = values
                    record.write(write_values)
        except Exception as e:  # noqa: BLE001
            error_count += 1
            info['end'] = now()
            if not values_err or record.env.cr._closed:
                # no error handler or the cursor is closed
                raise
            if callable(values_err):
                write_values = values_err(record, e)
                if not isinstance(write_values, dict):
                    if write_values is not None:
                        log.warning(
                            "%s: error expecting a dict, not values %s",
                            loop_name,
                            write_values,
                        )
                    raise
                if write_values:
                    record.write(write_values)
            else:
                log.error(e, exc_info=e)
                record.write(values_err)
        commit()
        visited.append(record.id)
        if not can_continue():
            log.info("%s: processed %d records (stop)", loop_name, len(visited))
            return False
        if now() >= log_at:
            log_at = now() + LOG_FREQUENCY
            log.info("%s: processed %d records", loop_name, len(visited))
            if error_count:
                log.warning("%s: %d errors", loop_name, error_count)
    log.debug("%s: done", loop_name)
    return len(visited)


def generic_commit_loop_batch(
    method,
    domain,
    batch_size=MAX_SEARCH_RECORDS,
    order=None,
    *,
    additional_domain=[],
    each=False,
    exception_handler=None,
    limit=True,
    lock="lock",
    log=None,
    values=None,
):
    """Process records in a batch loop using a method

    At each loop, we search records to processed limited by the batch size.
    We call the method for the records and write values afterwards.
    Finally, we commit.
    The next loop will re-execute the search, additionnally ignoring
    already-processed ids when no values are given.

    :param method: The method to call for a recordset
    :param domain: Search domain or recordset
    :param batch_size: (int) The limit for the search, commit every X
    :param order: The order for the search
    :param additional_domain: Additional domain for the search (default: [])
    :param each: (bool) Whether to call the method record by record (default: False)
    :param exception_handler: ((rec, e) -> bool) Return True to ignore error
    :param limit: (int | timedelta | callable | None) Limiter for the loop
    :param lock: Whether to lock records before processing (default: "lock")
                 Can by "try" to skip locked records. Or empty to skip locking.
    :param log: Logger
    :param values: Values to write after the method is called
    """
    try:
        model = method.__self__.browse()
        method = method.__func__
    except AttributeError:
        raise ValueError("The passed method must be a method bound to a model")
    loop_name = f"{model._name}.{method.__name__}"
    if log is None:
        log = logging.getLogger(__name__)
    if isinstance(domain, Model):
        recordset = domain
        if recordset._name != model._name:
            raise ValueError("The recordset is not the same model as the method")
        domain = []
        search_domain = additional_domain
        if not recordset:
            return 0
    else:
        recordset = None
        search_domain = expression.AND([domain, additional_domain])
    assert batch_size > 0, "Batch size must be positive"
    visited = set()
    can_continue = make_limit_checker(limit, visited)
    commit = auto_commit(model.env)
    commit()  # make sure we start a new transaction already here

    def record_fetching_domain():
        log.debug("%s: domain %s", loop_name, search_domain)
        loop_domain = search_domain
        while records := model.search(loop_domain, limit=batch_size, order=order):
            if values and (visited_twice := (set(records.ids) & visited)):
                raise ValidationError("%s: some records were already visited: %s" % (loop_name, visited_twice))
            yield records
            if not values:
                loop_domain = [('id', 'not in', list(visited)), *search_domain]

    def record_fetching_recordset():
        yield from split_every(batch_size, recordset, records.browse)

    def record_fetching_checked(records_gen):
        for records in records_gen:
            if lock:
                records.exists_lock()  # just lock them, they should exist
            records = records.filtered_domain(domain)
            if records:
                yield records

    log.debug("%s: start (batch_size: %d)", loop_name, batch_size)
    records_gen = record_fetching_checked(
        record_fetching_recordset() if recordset else record_fetching_domain()
    )
    for records in records_gen:
        try:
            with records.env.cr.savepoint():
                if each:
                    log.debug("%s: process %s - one by one", loop_name, records)
                    for record in records:
                        method(record)
                else:
                    log.debug("%s: process %s", loop_name, records)
                    method(records)
                if values:
                    records.write(values)
        except Exception as e:  # noqa: BLE001
            if callable(exception_handler) and exception_handler(records, e) is not True:
                raise
            log.debug('%s: ignoring error using %s', loop_name, exception_handler, exc_info=e)
        commit()
        visited.update(records.ids)
        log.info("%s: processed %d records", loop_name, len(visited))
        if not can_continue():
            log.info("%s: stop processing", loop_name)
            return False
    log.debug("%s: done", loop_name)
    return len(visited)
