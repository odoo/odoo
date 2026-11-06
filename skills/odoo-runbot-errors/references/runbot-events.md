# Ruling out a runbot event

Read before writing code for a timeout, a stall, a slow test, a red hour, or a test whose CI is
green too easily. A fix for an event that was not a bug changes shared code for nothing, and the
error comes back with the next event.

## A frozen or overloaded host

Signs: the error has one or a few builds, all on the same host in the same minutes; in the
browser console of the build, the suites before and after the failing one run at their usual
speed, except during one window.

1. Read the neighbours of the failing suite in the same console log: every Hoot suite logs its
   duration, so one log tells whether only one suite was slow or the whole page.
2. Read the sibling builds on the same host at the same time: `search_read` `runbot.build` on
   `[["host", "=", <host>], ["build_start", "<=", <end>], ["build_end", ">=", <start>]]`. The
   failed ones have console logs too. Several unrelated suites that stall in the same minute are
   the host, not the test.
3. Compare with the normal duration of the suite: the median over the console logs of other
   failed builds of the same configuration. A suite that ran ten times its median while its
   neighbours kept theirs is a host hiccup, not a regression.
4. Before raising a timeout, compute the budget the failing build needed. A raise that would not
   have saved that build has no numbers behind it. A test under a throttled CPU models a
   sustained slowdown, never a freeze.

When a piece of evidence does not fit the story (the neighbours ran at normal speed, but the
story says "the host was slow"), resolve it before writing the story.

## A red hour, or many bundles

`ir.logging` holds the log lines of every build, pull requests included. Search the error
message on a few days, grouped by build and by hour:

- the same test red on many unrelated bundles in the same hours: the base or the
  infrastructure, not one branch;
- red at the same hour every day: a test that depends on the time of day. A rebuild at another
  hour passes, and a rebase changes nothing.

## A test the CI of pull requests skips

When `test_tags` is set on an error, runbot adds it as a negative `--test-tags` entry to the
builds of the versions between `tags_min_version_id` and `tags_max_version_id`. The test no
longer runs in the CI of pull requests, so:

- a green CI proves nothing on a PR that is not the `fixing_pr_id` of the error. Runbot drops
  the tags of an error in the bundle of its fixing PR: set the field, then rebuild, and the CI
  of the fix runs the test;
- the error keeps gaining builds from the triggers that ignore these tags, until the fix lands.

Check whether a build skipped the test: its post-install log names the test once, on the
`odoo-bin` command line, with a `-` in front.

## The browser process died

When the chrome process of a tour or a JS test is killed, its devtools websocket closes, and the
message depends on what the test was waiting for:

- during the tour (`_wait_code_ok`): `ChromeBrowserException("Unknown error")`;
- during the page load (`_wait_ready`): a raw `WebSocketConnectionClosedException` traceback;
- during a pending devtools request (the `Runtime.evaluate` that starts the tour): a bare
  `concurrent.futures.CancelledError`, ending in `raise CancelledError()`.

The last two often open a new error with a single build. Sign in the build log: `Asking for
screenshot` with no `Screenshot in: ...` line after it; the `Disconnecting N websockets` and
`Closing chrome headless` lines that follow are the teardown, not the cause. These hits come at
night, on many hosts, on every version, about once every few days: Odoo lifts the memory limit
of chrome, so the killer is an out-of-memory kill of the container or the kernel, and runbot
does not retry the test.

Do not change the test. Link the error to the known error of that family
(https://runbot.odoo.com/odoo/error/940457): set "Linked to" (`error_id`) of the contents of the
new error to it, as in "Two errors that are one" of `error-fields.md`. The "Merge build errors"
action would keep the new error and archive 940457.

## A build killed during the install

`Enterprise Tests` builds can be killed with `Install all time exceeded (1805s)` before any test
runs. Sign: the build has no test result, and unrelated builds, stagings included, were killed
the same way in the same hours (search `ir.logging` as in "A red hour" above). This is runbot
load: no change to the code. Run the tests of the change locally if they never ran, and rebuild
later. An error made only of such builds needs no fix.

## Network drops in website builder tours

Website builder tours can fail with `ConnectionLostError`, `Failed to fetch` or an
`AssetsLoadingError` on `website.assets_inside_builder_iframe`, while the other tours of the
same batch load their assets and pass. Sign: one of these errors on a change that does not touch
website. These are transient network drops: no change; find the runbot error of that test
(`search_read` on its name, closed errors included) and rebuild.
