import unittest
from unittest import mock

from odoo.tools.assets import esm_lexer


class TestClosingTheWorkerUndoesTheDisable(unittest.TestCase):
    def setUp(self):
        self.worker = esm_lexer._LexerWorker()

    def test_a_disabled_worker_answers_nothing(self):
        self.worker._disable()
        self.assertIsNone(self.worker.request("export const a = 1;"))

    def test_close_clears_the_disable(self):
        self.worker._disable()
        self.worker._consec_failures = 9
        self.worker.close()
        self.assertFalse(self.worker._disabled())
        self.assertEqual(self.worker._consec_failures, 0)

    def test_close_still_kills_the_process(self):
        proc = mock.Mock()
        proc.poll.return_value = None
        self.worker._proc = proc
        self.worker.close()
        proc.kill.assert_called_once()
        self.assertIsNone(self.worker._proc)

    def test_a_reopened_worker_tries_to_spawn_again(self):
        self.worker._disable()
        self.worker.close()
        with (
            mock.patch.object(
                self.worker, "_spawn", return_value=(None, "no_node")
            ) as spawn,
            mock.patch.object(esm_lexer.os, "name", "posix"),
        ):
            self.assertIsNone(self.worker.request("export const a = 1;"))
        spawn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
