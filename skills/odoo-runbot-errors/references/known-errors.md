# Messages whose cause is elsewhere

Read when the message of the error names a place that is not the cause: the cause is in the
previous test, in the browser shutdown, or outside the code.

## "Cannot translate string: translations have not been loaded" (Hoot)

`_t()` returns a lazy translated string that throws this error when it is turned into text after
the test environment is torn down. A getter that builds such a string, read late by an async
path of a previous test, throws once that test is over, and the error lands on the NEXT test of
the suite.

Sign: the error comes before the first assertion of a test that passes when run alone.

Find the late reader, not the test that shows it. For one run, make the error carry its stack:
in `addons/web/static/src/core/l10n/translation.js`, append `new Error().stack` to the message
of that `throw`. The runner prints the message, so the stack comes back with the failure. The
fix is in that reader: stop the late read, or keep the translated value instead of building it
again on each read.

## `TimeoutError: Browser.close()` after a tour that passed

"Error during browser shutdown" with `TimeoutError: Browser.close()`. Chrome can close the
devtools connection before it answers `Browser.close`; the reader thread of the test helper
(`odoo/tests/common.py`) released the pending requests on only one of its exits, so the close
waited its whole 10 s. The close reaches the thread as `WebSocketConnectionClosedException` or
as `OSError(9, 'Bad file descriptor')`.

Sign: the tour SUCCEEDED, then 10 s between `Closing chrome headless` and `Closing websocket
connection`, then the warning. This is not a dead browser (`runbot-events.md`): here chrome
closes because it was asked to.

The fix for 17.0 is the open PR https://github.com/odoo/odoo/pull/287887: the reader cancels
every pending request on any exit, and the shutdown accepts the cancellation. Check on the
version of the failing build whether the reader of `odoo/tests/common.py` already does it. If it
does, it is a new cause: start from the build log. If it does not, this is the known cause: set
`fixing_pr_id` to that PR when the field is empty, and leave the code alone.

## `Script timeout exceeded` on the WebSuite

Whatever silences the browser, the runner waits its whole timeout and reports this same line;
the mobile suite shares the runner and the message. The last console line before the silence
tells the cause:

- `TypeError: Failed to fetch` in the ORM of a test, right after the server logged `RuntimeError:
  can't start new thread`: Hoot fetched the dependencies of a batch of modules, the fetch
  failed, and the batch waited forever. Fixed from 18.0 by
  https://github.com/odoo/odoo/pull/284980: with it, the run stops at once on `Test run aborted:
  Error: could not fetch the dependencies of <addons>`. Check whether the build holds it.
- a heap close to its limit, a last line `"<file>" ended` and no memory line after it: the
  forced garbage collection between test files never returned. Memory, not the test.
- the page freezes in the middle of a test while other builds on the same host freeze in the
  same minutes: the host (`runbot-events.md`).

Sample several builds before picking a cause: only the first family is a bug of the code.
