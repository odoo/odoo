import threading

from odoo.db import db_connect

from ._bench import StatementCounter


def test_counter_includes_execute_executemany_and_both_copy_apis(base_db):
    with db_connect(base_db).cursor() as cr:
        cr.execute("CREATE TEMP TABLE perf_counter (value integer)")
        counter = StatementCounter()
        with counter.on():
            cr.execute("INSERT INTO perf_counter VALUES (1)")
            cr.executemany("INSERT INTO perf_counter VALUES (%s)", [(2,), (3,)])
            with cr.copy("COPY perf_counter FROM STDIN") as copy:
                copy.write_row((4,))
            cr.copy_from("perf_counter", ["value"], [(5,)])
            assert counter.seconds > 0
        assert counter.count == 4

        cr.execute("SELECT value FROM perf_counter ORDER BY value")
        assert cr.fetchall() == [(1,), (2,), (3,), (4,), (5,)]


def test_counter_preserves_an_existing_query_observer_on_error(base_db):
    thread = threading.current_thread()
    previous = getattr(thread, "query_hooks", None)
    observed = []
    thread.query_hooks = [lambda *args: observed.append(args)]
    try:
        with db_connect(base_db).cursor() as cr:
            try:
                with StatementCounter().on():
                    cr.execute("SELECT 1")
                    raise ValueError("stop measuring")
            except ValueError:
                pass
            cr.execute("SELECT 2")
        assert len(observed) == 2
        assert len(thread.query_hooks) == 1
    finally:
        if previous is None:
            del thread.query_hooks
        else:
            thread.query_hooks = previous


def test_counter_accounts_for_pipeline_wait_without_an_extra_statement(base_db):
    with db_connect(base_db).cursor() as cr:
        counter = StatementCounter()
        with counter.on():
            counter.reset()
            with cr.pipeline():
                cr.execute("SELECT pg_sleep(0.03)")
            assert counter.count == 1
            assert counter.seconds >= 0.03
