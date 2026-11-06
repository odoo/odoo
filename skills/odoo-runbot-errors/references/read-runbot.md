# Reading runbot

Every read below is a `call_kw` on `https://runbot.odoo.com/web/dataset/call_kw/<model>/<method>`
with your session cookie (see `SKILL.md`). `search_read` with a domain, `fields`, `limit` and
`order` covers almost everything. An answer "Odoo Session Expired" (code 100) needs a new
session: it does not mean "no result".

## The records

| Model | Holds |
| --- | --- |
| `runbot.build.error` | the bucket: `name`, `random`, `test_tags`, `build_count`, `first_seen_date`, `last_seen_date`, `first_seen_batch_ids`, `version_ids`, `team_id`, `responsible`, `fixing_pr_id`, `breaking_pr_id`, `previous_error_id`, `error_content_ids` |
| `runbot.build.error.content` | one fingerprint of the bucket: `content` (the traceback), `module_name`, `file_path`, `function` |
| `runbot.build.error.link` | one failed build of a content: `build_id`, `log_date`, `host`, `dest`, `version_id`, `trigger_id`, `description` |
| `runbot.build` | a build: `host`, `dest`, `description`, `local_result`, `global_result`, `parent_id`, `children_ids`, `params_id`, `build_start`, `build_end` |
| `runbot.build.params` | what the build ran: `config_data`, `commit_link_ids` |
| `runbot.batch` | one push of a bundle: `bundle_id`, `category_id` (nightly or not), `commit_link_ids`, `slot_ids` |
| `runbot.commit.link` | a commit of a batch or build: `commit_id`, `match_type`, `merge_base_commit_id` |
| `ir.logging` | the timeline of a build: one row per log line, `build_id`, `level`, `path`, `func`, `message` |

- Every build of an error: `search_read` `runbot.build.error.link` on
  `[["error_content_id", "in", <error_content_ids>]]`, ordered by `log_date`. Counted per day,
  it is the graph of the error page.
- The red children of a build (a pull request CI build, a nightly): `search_read`
  `runbot.build` on `[["id", "child_of", [<build id>]], ["local_result", "not in", ["ok",
  "warn"]]]`.
- Closed records: put `["active", "in", [true, false]]` in the domain.

## Build logs and files

A build's files are served by its worker host, as a plain GET with no session:
`https://<host>/runbot/static/build/<dest>/logs/` is an index of its log files, and
`tests/<db>/screenshots/` and `tests/<db>/chrome_logs/` hold the screenshot and the browser
console of a failed tour or JS test. `host` and `dest` come from `runbot.build`.

- A full log is several MB. To count something over many builds (a test duration, a passed
  count), `search_read` `ir.logging` with a `message ilike` filter returns a few KB per build.
- `ir.logging` holds the lines of every build, pull requests included, while an error only
  counts the builds of the base bundles. Filter it on `path` and on a few days: an unbounded
  search times out.
- Old builds lose their logs: a build a few months old has no timeline left.

## Nightlies and configurations

- A nightly batch holds one build per configuration, and only some of them run with demo data
  (`config_data` of `runbot.build.params`). Dating a demo-only failure from a build without
  demo gives a false green.
- The last green nightly and the first red one bound the window of a regression: their
  `commit_link_ids` give the odoo and enterprise commits each one ran. Walk back with
  `runbot.batch` `search_read` on the bundle and the nightly category, one batch per night.
- The all-modules nightly splits the tests by module range; the `config_data` of the failing
  build holds the module filter a local reproduction needs.
- A batch of a pull request compares its commits with the base: `match_type` and
  `merge_base_commit_id` of its commit links tell which base each repository ran on. An odoo
  branch with no enterprise branch of the same name runs against the enterprise of its base.

## Reading a red build

- **Read the first error, not the most frequent one.** One early failure can break everything
  after it: a field that fails to register can abort every later insert, and the run then shows
  thousands of warnings and hundreds of failed tests with different messages. Sign: many
  failures with unrelated messages in one run. Read the first error of the run, or of the first
  failing test, before counting anything.
- **One error can hold several bugs.** Runbot groups failures by the scrubbed text of their
  message, so a generic message (`Found 0 instead of 1 ...`, `Script timeout exceeded`) collects
  unrelated causes. Sign: a fix that should cover the error is in the build, and builds keep
  coming; or the failing test or the last log lines differ from one build to the next. Sample
  several builds (`runbot.build.error.link` on the `error_content_ids`), group them by test and
  by the last console line before the failure, and only then pick a cause. Fix one mechanism per
  PR, and say which builds it explains and which it does not.
