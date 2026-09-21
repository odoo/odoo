import threading

import pytest

from odoo.libs.worker_thread import (
    REQUEST_SCOPED_ATTRIBUTES,
    WorkerThread,
    as_worker_thread,
    forget_request,
    working_on_database,
)


@pytest.fixture(autouse=True)
def _no_marker():
    thread = as_worker_thread(threading.current_thread())
    previous = getattr(thread, "dbname", None)
    if previous is not None:
        del thread.dbname
    yield
    if previous is not None:
        thread.dbname = previous
    elif hasattr(thread, "dbname"):
        del thread.dbname


def test_the_marker_is_set_inside_and_gone_after():
    thread = as_worker_thread(threading.current_thread())
    with working_on_database("db_a"):
        assert thread.dbname == "db_a"
    assert not hasattr(thread, "dbname"), (
        "a worker that polls several databases in turn must leave the thread as "
        "it found it; absent is not the same as None, and the log formatter "
        "reads the attribute"
    )


def test_a_previous_marker_is_restored_not_cleared():
    thread = as_worker_thread(threading.current_thread())
    thread.dbname = "outer"
    with working_on_database("inner"):
        assert thread.dbname == "inner"
    assert thread.dbname == "outer"


def test_nesting_unwinds_in_order():
    thread = as_worker_thread(threading.current_thread())
    with working_on_database("one"):
        with working_on_database("two"):
            assert thread.dbname == "two"
        assert thread.dbname == "one"
    assert not hasattr(thread, "dbname")


def test_the_marker_survives_long_enough_for_the_handler_to_log():
    thread = as_worker_thread(threading.current_thread())
    seen = []
    with pytest.raises(ValueError):
        with working_on_database("db_b"):
            try:
                raise ValueError("boom")
            except ValueError:
                seen.append(thread.dbname)
                raise
    assert seen == ["db_b"], (
        "every except branch in _process_jobs names the database in its message; "
        "the log prefix has to agree with it"
    )
    assert not hasattr(thread, "dbname")


def test_an_escaping_exception_still_restores():
    thread = as_worker_thread(threading.current_thread())
    thread.dbname = "outer"
    with pytest.raises(RuntimeError):
        with working_on_database("inner"):
            raise RuntimeError("boom")
    assert thread.dbname == "outer"


class TestForgettingARequest:
    """Two places answer "that request is over" and each kept its own list.

    The transport's was the shorter one, and it runs on the path where a
    malformed head means no application will ever run -- so the 400 it then
    logged carried the *previous* request's database and user.
    """

    def _thread_mid_request(self):
        thread = as_worker_thread(threading.current_thread())
        for attr in REQUEST_SCOPED_ATTRIBUTES:
            setattr(thread, attr, "from the last request")
        thread.rpc_model_method = "res.partner.read"
        return thread

    def test_nothing_of_the_request_survives_it(self):
        thread = self._thread_mid_request()
        try:
            forget_request()
            left = [a for a in REQUEST_SCOPED_ATTRIBUTES if hasattr(thread, a)]
            assert left == [], f"{left} would describe the next request wrongly"
            assert thread.rpc_model_method == ""
        finally:
            for attr in REQUEST_SCOPED_ATTRIBUTES:
                if hasattr(thread, attr):
                    delattr(thread, attr)

    def test_the_gate_attribute_goes_with_the_ones_it_gates(self):
        """The readers ask for `query_count` and then read three more.

        `logutils`'s perf filter and the pool's query accumulator both test
        `hasattr(worker, "query_count")` and go on to read `query_time`,
        `perf_t0` and `cursor_mode` unguarded. Dropping the gate while
        leaving those is harmless; dropping those while leaving the gate is
        an AttributeError inside a log filter.
        """
        gated = {"query_time", "perf_t0", "cursor_mode"}
        assert "query_count" in REQUEST_SCOPED_ATTRIBUTES
        assert gated <= set(REQUEST_SCOPED_ATTRIBUTES), (
            "what the gate promises is present must be dropped with it"
        )

    def test_forgetting_twice_is_not_an_error(self):
        forget_request()
        forget_request()

    def test_every_declared_attribute_is_accounted_for(self):
        """A new request attribute has to be forgotten or declared to outlive one.

        `WorkerThread` is where the attributes are written down, and the two
        ends of a request are elsewhere. Adding one there and not to the list
        is how the previous request's database came to be logged against the
        next one's error.
        """
        declared = set(WorkerThread.__annotations__)
        outlives_a_request = {"type", "start_time", "exec_context"}
        reset_not_dropped = {"rpc_model_method"}
        assert declared - outlives_a_request - reset_not_dropped == set(
            REQUEST_SCOPED_ATTRIBUTES
        ), (
            "every attribute a request thread declares is either dropped when "
            "the request ends, reset, or one of the three that describe the "
            "thread itself"
        )
