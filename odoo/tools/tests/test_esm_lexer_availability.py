import logging
import shutil
import subprocess
import tempfile
import threading
import time
import typing
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from odoo.tools.assets import esm_lexer

ANSWER = {
    "ok": True,
    "imports": [],
    "names": ["a"],
    "starFrom": [],
    "hasDefault": False,
}


class TestAnOutageIsNotAnAnswer(unittest.TestCase):
    def setUp(self):
        esm_lexer.clear_lex_cache()
        self.addCleanup(esm_lexer.clear_lex_cache)

    def test_a_source_lexed_during_an_outage_is_lexed_again_after_it(self):
        with mock.patch.object(
            esm_lexer._worker, "request", side_effect=[None, ANSWER]
        ) as request:
            self.assertIsNone(esm_lexer.lex_module("export const a = 1;"))
            self.assertEqual(esm_lexer.lex_module("export const a = 1;"), ANSWER)
        self.assertEqual(request.call_count, 2)

    def test_a_refused_source_is_remembered_as_refused(self):
        refusal = {"ok": False, "error": "bad syntax"}
        with mock.patch.object(
            esm_lexer._worker, "request", return_value=refusal
        ) as request:
            self.assertIsNone(esm_lexer.lex_module("not javascript {"))
            self.assertIsNone(esm_lexer.lex_module("not javascript {"))
        request.assert_called_once()

    def test_the_cache_holds_digests_not_sources(self):
        source = "export const a = 1;" + " " * 4096
        with mock.patch.object(esm_lexer._worker, "request", return_value=ANSWER):
            esm_lexer.lex_module(source)
        self.assertEqual(len(esm_lexer._lex_cache), 1)
        key = next(iter(esm_lexer._lex_cache))
        self.assertIsInstance(key, bytes)
        self.assertLess(len(key), 64)


class TestAFailingWorkerIsRetriedLater(unittest.TestCase):
    def setUp(self):
        self.worker = esm_lexer._LexerWorker()
        self.now = 1000.0
        clock = mock.patch.object(esm_lexer.time, "monotonic", lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.alive = SimpleNamespace(poll=lambda: None)

    def _ask(self, read_line):
        with (
            mock.patch.object(esm_lexer.os, "name", "posix"),
            mock.patch.object(
                esm_lexer._LexerWorker, "_spawn", return_value=(self.alive, "")
            ) as spawn,
            mock.patch.object(esm_lexer._LexerWorker, "_write_all"),
            mock.patch.object(esm_lexer._LexerWorker, "_kill"),
            mock.patch.object(esm_lexer._LexerWorker, "_read_line", read_line),
        ):
            return self.worker.request("export const a = 1;"), spawn

    def test_two_slow_replies_pause_the_worker_rather_than_retire_it(self):
        def slow(_self, _proc, _deadline):
            raise TimeoutError("one slow reply under load")

        response, _spawn = self._ask(slow)
        self.assertIsNone(response)
        self.assertTrue(self.worker._disabled())

        def answer(_self, _proc, _deadline):
            return esm_lexer.json.dumps({"id": self.worker._counter, **ANSWER})

        self.now += esm_lexer._DISABLE_COOLDOWN_S - 1
        response, spawn = self._ask(answer)
        self.assertIsNone(response, "still inside the cooldown")
        spawn.assert_not_called()

        self.now += 2
        response, spawn = self._ask(answer)
        self.assertEqual(response["names"], ["a"])
        self.assertFalse(self.worker._disabled())


class _PausedByAnotherCaller:
    def __init__(self, worker):
        self.worker = worker
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        self.worker._disable()
        return self

    def __exit__(self, *exc_info):
        self.lock.release()


class TestACallerQueuedDuringAPauseWaitsItOut(unittest.TestCase):
    def setUp(self):
        self.worker = esm_lexer._LexerWorker()
        self.spawns = 0

        def spawn(_self):
            self.spawns += 1
            return SimpleNamespace(poll=lambda: None), ""

        def silent(_self, _proc, _deadline):
            time.sleep(0.05)
            raise TimeoutError("a worker that never answers")

        for patcher in (
            mock.patch.object(esm_lexer.os, "name", "posix"),
            mock.patch.object(esm_lexer._LexerWorker, "_spawn", spawn),
            mock.patch.object(esm_lexer._LexerWorker, "_write_all"),
            mock.patch.object(
                esm_lexer._LexerWorker,
                "_kill",
                lambda worker: setattr(worker, "_proc", None),
            ),
            mock.patch.object(esm_lexer._LexerWorker, "_read_line", silent),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_pause_is_read_again_once_the_lock_is_held(self):
        self.worker._lock = typing.cast(
            "typing.Any", _PausedByAnotherCaller(self.worker)
        )
        self.assertIsNone(self.worker.request("export const a = 1;"))
        self.assertEqual(self.spawns, 0)

    def test_queued_callers_spend_no_attempts_of_their_own(self):
        callers = 6
        barrier = threading.Barrier(callers)

        def ask():
            barrier.wait()
            self.worker.request("export const a = 1;")

        threads = [threading.Thread(target=ask) for _ in range(callers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(self.spawns, esm_lexer._MAX_CONSECUTIVE_FAILURES)
        self.assertTrue(self.worker._disabled())


@unittest.skipUnless(shutil.which("node"), "needs node")
class TestAWorkerThatCannotStartIsUnavailable(unittest.TestCase):
    def setUp(self):
        scripts = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scripts, True)
        script = scripts / "worker.mjs"
        script.write_text('import { init } from "es-module-lexer-not-installed";\n')
        for patcher in (
            mock.patch.object(esm_lexer, "_WORKER_SCRIPT", script),
            mock.patch.object(esm_lexer.os, "name", "posix"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.worker = esm_lexer._LexerWorker()
        self.addCleanup(self.worker.close)

    def _ask(self):
        with mock.patch.object(
            esm_lexer.subprocess, "Popen", wraps=subprocess.Popen
        ) as popen:
            self.assertIsNone(self.worker.request("export const a = 1;"))
        return popen.call_count

    def test_the_package_missing_is_a_spawn_failure_noticed_once(self):
        with self.assertLogs(esm_lexer._lexer_log, logging.DEBUG) as logs:
            self.assertEqual(self._ask(), 1)
            self.assertGreaterEqual(
                self.worker._disabled_until - time.monotonic(),
                esm_lexer._UNAVAILABLE_COOLDOWN_S - 5,
            )
            self.worker._disabled_until = 0.0
            self.assertEqual(self._ask(), 1)
        levels = [
            record.levelno
            for record in logs.records
            if "worker_unavailable" in record.getMessage()
        ]
        self.assertEqual(levels, [logging.INFO, logging.DEBUG])
        self.assertFalse(
            [record for record in logs.records if record.levelno >= logging.WARNING]
        )


class TestAForkedChildLeavesTheParentsWorkerAlone(unittest.TestCase):
    def test_the_child_drops_the_worker_without_signalling_it(self):
        worker = esm_lexer._LexerWorker()
        proc = mock.Mock()
        worker._proc = proc
        worker._inbuf = b"half a reply"
        held = worker._lock
        held.acquire()
        self.addCleanup(held.release)
        with mock.patch.object(esm_lexer, "_worker", worker):
            esm_lexer._reset_after_fork()
        proc.kill.assert_not_called()
        proc.stdin.close.assert_called_once()
        proc.stdout.close.assert_called_once()
        self.assertIsNone(worker._proc)
        self.assertEqual(worker._inbuf, b"")
        self.assertFalse(worker._lock.locked())


if __name__ == "__main__":
    unittest.main()
