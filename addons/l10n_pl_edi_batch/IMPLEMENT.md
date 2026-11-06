# KSeF Batch Download: implementation plan

What we're going to change in the code, step by step, to reach the design in
`DESIGN.md`. Each step is one or a few commits, the docs in their own, tested
with `ocli odoo test /l10n_pl_edi_batch` before the next one starts.

Questions still to decide are marked "Open:".


## Where the code was before step 1

- `models/batch_download.py`: the batch model. Stored `active`, `status` (a
  selection of the 7 known KSeF codes), `error`, `content`, `date_expiry`.
  Methods: `_request`, `check_status`, `unzip`, `import_attachments`,
  `_gc_batch_downloads`.
- `models/batch_part.py`: the part model, with `download()`.
- `models/account_move.py`: the `l10n_pl_edi_batch.enabled` check, and the
  override of the today cron, which only returns early for now.
- `tools/ksef_api_service.py`: the KSeF calls. `download_batch_status`
  returns `status`, `error` and `date_expiry` already extracted from the
  answer, plus the parts.
- `views/l10n_pl_edi_batch_views.xml`: debug views, with buttons Check
  Status, Unzip, Import Bills, Download. They filter and group on `status`.
- `data/ir_cron_data.xml` and `tests/test_l10n_pl_edi_batch.py`: empty.


## Step 1: fields

`models/batch_download.py`:

- `status`: computed from `content['status']['code']`, not stored, with a
  search method.
- `date_expiry`: computed from `content['packageExpirationDate']`, converted
  to UTC (the code that does it moves from the service to the model).
- `kind`: computed, `historic` when `date_to <= create_date - 24h`, otherwise
  `today`.
- `state`: computed, in this order: failed, requested, downloading,
  downloaded, done (see `DESIGN.md`).
- `retry_count`: new stored integer, default 0.
- `active`: dropped.
- Search methods for `status`, `kind` and `state`: read the company's
  batches, filter in Python, return `[('id', 'in', ids)]`.

`tools/ksef_api_service.py`: `download_batch_status` used to build a dict
with `content` (the whole KSeF answer), `status`, `error`, `date_expiry` and
the parts, and `check_status` wrote all of it on the batch. Since `status`,
`date_expiry` and `error` are computed from `content`, the dict keeps only
`content` and the parts, and `check_status` writes only those.

New `models/res_company.py`: `l10n_pl_edi_batch_historic_date`, a stored
datetime.

Views: filters and group-by on `state` instead of `status`, statusbar on
`state`, no more `active`. A default filter "In progress" (state not done or
failed) hides finished batches, as `active` did.

Decided: `status` stays a selection of the 7 known KSeF codes, for the
readable labels. The logic only checks 100 and 200; any other code is failed.
Superseded after slice 7: `status` was dropped, `state` is enough (see the
progress below).

Decided: right after the request, `content` is empty; the code then counts as
100 by default, so the batch is requested.

Decided: `error` is no longer stored. Our own errors (failed download,
corrupt ZIP) are written in `content['status']`, like KSeF's, with our code
999 "Odoo Error" (added to the selection) and the details, by
`_set_odoo_error`. The package info in `content` stays untouched. `error` is
computed from `content['status']`, whether the error came from KSeF or from
us.

Tests: in `tests/test_l10n_pl_edi_batch.py`, run with
`ocli odoo test /l10n_pl_edi_batch`.

### Step 1 progress

Done, one commit each, with tests:

1. `status` and `date_expiry` computed from `content` (d1db8dd).
2. `error` computed from `content`, our own status 999 (4b6b505).
3. `kind` computed from the dates, `retry_count` stored (504a661).
4. Parts hold their content in a binary field (919d7b4).
5. `state` computed (5e79920).
6. `active` dropped, views on `state` (c1ca5a3).
7. The company's historic date (80b9ecb).

Then, after reviewing the result:

8. `status` dropped: `state` already says what the KSeF code means, and the
   error text starts with the code. `state` and `error` read the code from
   `content` (`_get_ksef_status_code`); the codes are module constants
   (ce30f32).
9. The `*_b64` key fields and the comments on the model fields dropped
   (ea57642).
10. `_get_ksef_status_code` inlined (only `state` needs the 100 default), the
    unique constraint and index on `name` dropped (nothing searches by it),
    parts ordered by `batch_id` and no longer created with `batch_name`.

Step 1 is done.

### Slice 4: parts hold their content in a binary field

Today a part *is* an attachment (`_inherits = {'ir.attachment': ...}`): it
gets an empty attachment as soon as it's created, and "downloaded" means
`file_size > 0`. The download also needs `sudo()`, because a plain user
can't write an attachment that isn't linked to a record.

Instead, like the other EDI binaries (e.g. `l10n_pl_edi_attachment_file` on
the bill), the part gets its own binary field:

- `models/batch_part.py`: drop `_inherits`, `attachment_id` and the `unlink`
  override. Add `decrypted_file = fields.Binary(attachment=True)`: the
  decrypted slice of the ZIP. Odoo stores it as an attachment linked to the
  part and the field, protected by the part's own access rights, and deletes
  it with the part.
- No attachment exists until the download: "downloaded" means
  `decrypted_file` is set. To check it without loading the content, read it
  with `bin_size=True`.
- `download()`: writes `decrypted_file`, without `sudo()`.
- `unzip()`: reads the parts' `decrypted_file` instead of `raw`.
- `tools/ksef_api_service.py`: the parts are created without `name` (an
  attachment field); `part_name` already comes from the URL.
- Views: the parts show `decrypted_file` (with `part_name` as file name)
  instead of the attachment fields, and their Download buttons go away (as
  decided).
- The batch keeps its `unlink` override that deletes the parts through the
  ORM, so their files are deleted too.

Lost: the attachment's own fields on the part (`mimetype`, `file_size`,
`checksum`...), and parts showing up as normal attachments. We use neither.
Existing parts in dev databases are dropped with the old model.

Tests: a part without `decrypted_file` counts as missing, with it as
downloaded; deleting a batch deletes its parts' files.

### Slice 5: the computed `state`

`state` is a non-stored selection, computed in this order, the first match
wins:

```
failed        status is neither 100 nor 200 (including our 999)
              or retry_count above 9
              or the package expired while parts are still missing
requested     status 100
downloading   status 200, and some parts not downloaded yet
downloaded    status 200, and all parts downloaded, or XMLs on the batch
done          status 200, no parts and no XMLs left
```

Details:

- "Retries used up" is `retry_count > 9`: 9 retries are allowed, the 10th
  failure fails the batch. The limit is a module constant, `MAX_RETRIES = 9`,
  used by the crons later too.
- A part is downloaded when its `decrypted_file` is set (slice 4).
- Expiry only fails a batch while parts are missing: once everything is
  downloaded, the package expiring doesn't matter any more.
- A batch with 0 invoices: status 200, no parts, no XMLs, so done.
- `@api.depends('content', 'retry_count', 'part_ids.file',
  'attachment_ids')`. Expiry depends on the current time, which is fine for a
  non-stored field: it's computed on every read.
- Search method: same as `status` and `kind`, filter in Python.

Tests, one case per state:

- requested: no content;
- failed: status 415; status 999; status 100 with `retry_count` 10; status
  200, expired, with a part not downloaded;
- downloading: status 200, one part downloaded and one not;
- downloaded: status 200, all parts downloaded; and status 200, expired, all
  parts downloaded (expiry no longer matters);
- downloaded: no parts, one XML on the batch;
- done: status 200, no parts, no XMLs (also the 0-invoice case);
- the search: `search([('state', '=', 'failed')])` returns exactly the failed
  ones.

### Slice 6: drop `active`, views on `state`

`active` only meant "not done or failed yet", which `state` now says.

`models/batch_download.py`:

- Remove the `active` field.
- `_request` no longer writes `active: True`.
- `import_attachments` no longer sets `active = False`: the batch is done
  by itself once no XMLs are left on it.
- `_gc_batch_downloads`: until step 4, it deletes the done and failed
  batches instead of the inactive ones (no `active_test` any more). Step 4
  adds the 30 days.

Views:

- List: colors from `state` (red failed, green done, blue requested and
  downloading), and a `state` badge column next to `status`.
- Form: statusbar on `state` instead of `status`. The header buttons stay
  for now (step 6 removes them), with their visibility based on `state`.
- Search: one filter per state, plus "In progress" (state neither done nor
  failed), on by default in the menu action, as `active` used to hide the
  finished batches.
- No group-by on `state`: Odoo can't group by a non-stored field.

Tests: the `active: True` lines go away from the test batches.

### Slice 7: the company's historic date

New `models/res_company.py`: `l10n_pl_edi_batch_historic_date`, a stored
datetime, empty by default: the end of the next historic window. No view:
it's read and moved by the historic cron (step 5), and fixed by hand from
the debug views if needed.

Tests: none here; the historic cron's tests in step 5 cover it.

## Step 2: request

- `tools/ksef_api_service.py`: the export filters by `PermanentStorage`
  instead of `Invoicing`. The single-invoice query of `l10n_pl_edi` keeps
  `Invoicing`.
- `KSEF_WINDOW` = 7 days; it and `KSEF_FIRST_DAY` move to
  `models/batch_download.py`, where the historic cron will use them.
- `_request` reads `referenceNumber` strictly: a missing one fails right away.

Tests: both requests are well formed, the batch one with `PermanentStorage`,
the `l10n_pl_edi` one with `Invoicing`.

Step 2 is done.


## Step 3: import

The XMLs are no longer kept on the batch: they're read from the ZIP and
imported in the same run, and the parts stay until the import is over. If
the run stops, the next one starts again from the parts.

`models/batch_download.py`:

- Remove `attachment_ids`.
- `state`: downloaded = every part has its file; done = code 200 and no
  parts left (a 0-invoice batch has no parts, so it's done right away).
- `unzip` and `import_attachments` become one method, `import_bills`:
  1. join the parts in ordinal order into a temporary file, open it as a ZIP;
     a corrupt ZIP sets our 999 error (`_set_odoo_error`) and stops;
  2. for each XML (not `_metadata.json`): skip it if a vendor bill with the
     same KSeF number (the file name without `.xml`) exists in the company;
     otherwise create the bill, attach the XML to it, import it by posting
     it, set the KSeF number, and commit;
  3. delete the parts: the batch is done.
- No commit right after creating the bill any more; one commit per bill,
  through `account.move._can_commit()`.
- An error that the standard import doesn't catch is left to raise: the
  unzip+import cron (step 6) bumps `retry_count` and, after 9 retries, sets
  our 999 error.

Views: the form's Unzip button goes away, Import Bills calls `import_bills`
(until step 6 removes it); the form's XML tab goes away.

Tests: a batch with two real ZIP slices holding two XMLs, one of which
already has a bill. `import_bills` creates one bill with its KSeF number,
skips the other, deletes the parts, and the batch is done. A second call
does nothing. A corrupt ZIP sets the 999 error and fails the batch.

Superseded in step 6c: no retries for the import, since the standard import
catches the errors of each XML; and a corrupt ZIP downloads the parts again
before failing the batch.

Step 3 is done.


## Step 4: cleanup

`_gc_batch_downloads`: delete the batches whose `state` is done or failed and
whose `write_date` is more than 30 days old. Nothing else.

Tests: `write_date` backdated with SQL; done and failed batches 31 days old
are deleted with their parts, a done one 29 days old and a requested one 31
days old are kept.

Step 4 is done.


## Step 5: today and historic crons

Two commits: 5a the today cron, 5b the historic cron.

The request logic moves to the batch model, so that the crons live there.

Decided: the status cron only comes in step 6, so the trigger at the end of
both request crons comes with it. Until then, `check_status()` is run by
hand.

Decided: the historic date moves back when the next window is requested, not
when the previous batch is done or failed: no lookup of the latest batch, and
the same result (at most one historic batch in progress, a failed window
skipped).

Decided: on a KSeF error other than the rate limit, the request crons log it,
roll back the company and go on with the next one.

### 5a: today cron

- `_is_enabled()`: the `l10n_pl_edi_batch.enabled` check, moved from
  `account.move`.
- `_cron_request_today()`: for each company with a KSeF access token, skip it
  if a today batch is still requested; otherwise `_request` the window from
  `max(yesterday 00:00 UTC, date_to of the latest today batch not failed) -
  1h` to now, and commit (`_can_commit()`).
- On `KSeFRateLimitError`: stop, and trigger the same cron after
  `retry_after` seconds (60 when KSeF doesn't say).
- `models/account_move.py`: the override of `_cron_l10n_pl_edi_download_bills`
  calls `_cron_request_today()` when enabled, `super()` otherwise. The
  commented-out block, `_l10n_pl_edi_trigger` and the unused imports go away.

Tests, KSeF mocked and time frozen: the first window from yesterday; the next
one chained on the previous `date_to` - 1h; a failed batch not chained on; the
skip while a batch is requested; the retrigger on 429; a KSeF error on one
company not blocking the next; `super()` when disabled.

5a is done.

### 5b: historic cron

- `_cron_request_historic()`: for each company with a KSeF access token, the
  historic date (empty: yesterday 00:00 UTC); nothing to do once it reaches
  `KSEF_FIRST_DAY`; skip while a historic batch is requested, downloading or
  downloaded; otherwise `_request` `[max(date - KSEF_WINDOW, KSEF_FIRST_DAY),
  date)`, move the date to its start, commit. Same rate limit and error
  handling as the today cron.
- `data/ir_cron_data.xml` (added to the manifest): the historic cron, daily,
  on the batch model.
- The trigger when a historic batch is done or failed comes with the import
  cron (step 6).

Tests, KSeF mocked and time frozen: the first window from yesterday; the date
moving back; the last window cut at `KSEF_FIRST_DAY`; nothing requested past
it; the skip while a batch is in progress; a failed batch not blocking the
next window; a failed request not moving the date.

5b is done.


## Step 6: status, download and import crons

Four commits: 6a the status cron, 6b the download cron, 6c the import cron,
6d the views. Each cron is a method of the batch model, decorated with
`ksef_cron` (the enabled check and the rate limit), and has its own record
in `data/ir_cron_data.xml`, run daily as a safety net in case a trigger is
lost.

All three take today batches before historic ones, and only the batches that
are due: `write_date + 10 * 2 ** retry_count` is past. A batch is locked with
`res.company._with_locked_records(batch, allow_raising=False)` while a cron
works on it, and skipped if it's already locked. Commits go through
`_can_commit()`.

### 6a: status cron

- `_cron_check_status()`: for each due requested batch, `check_status` and
  commit. Still 100: `retry_count += 1`, and trigger itself when the batch is
  due again. 200: reset `retry_count`, and trigger the download cron. Any
  other code: the batch is failed by itself.
- `_request` schedules the status cron for when the new batch is due (10 s
  later), so both request crons get it (left out of step 5).
- A KSeF error on the status counts a retry too; the rate limit stops the run
  and triggers the cron again after KSeF's delay.
- The trigger of the download cron at 200 comes with that cron (6b).

Tests: a new batch schedules its first check; a batch not due yet is left
alone; still 100 counts a retry and schedules the next check; 200 creates the
parts and resets the count; the 10th retry fails the batch and schedules
nothing more.

6a is done.

### 6b: download cron

- `_cron_download()`: one missing part of one due downloading batch per run,
  then commit and `_notify_progress` with the parts left. All parts in:
  trigger the import cron.
- `part.download()` raises its error instead of logging and going on, and
  loses its `commit` argument: the cron commits.
- On a failed download: `retry_count += 1`, and trigger itself when the
  batch is due again. After the 9th retry, the last download error is
  written as our 999 error, so the batch shows why it failed.

Decided: the 999 error after the last retry, though the state is already
failed by `retry_count`: otherwise the error stays empty.

- The status cron triggers the download cron once a batch reaches 200. The
  trigger of the import cron, once all parts are in, comes with that cron
  (6c).
- After writing a part, `download()` invalidates its file: the reads with
  `bin_size` (is the part downloaded?) have their own cache, which the write
  doesn't refresh, so the state stayed downloading in the same transaction.

Tests: the status cron triggers the download cron; one part per run; a
failed download counts a retry and schedules the next try; the 10th failure
writes the 999 error.

6b is done.

### 6c: import cron

- `_cron_import()`: one downloaded batch per run, `import_bills`, then
  `_notify_progress` with the batches left. A historic batch done or failed:
  trigger the historic cron.
- The download cron triggers the import cron once all the parts are in.

Decided: no retries for the import. It's deterministic, and the standard
import already catches every error of an XML: `_decode_edi_xml` for an XML
that can't be read, `_extend_with_attachments` for a decoder error, posted in
the bill's chatter. The bill stays empty with its XML, and the next XML is
imported (see `DESIGN.md`).

Tests: the download cron triggers the import cron; one batch per run, today
first; a historic batch done triggers the historic cron, a today one
doesn't; an unreadable XML and a failing decoder each leave an empty bill
with its XML, and the next XML is still imported.

Decided after 6c: a corrupt ZIP downloads the parts again instead of failing
the batch: `import_bills` empties their files and counts a retry, with
`_count_retry`, shared with a failed download. Tests: the parts are emptied
and the download cron scheduled; after the last retry, the batch fails.

6c is done.

### 6d: views

Decided: the buttons that do the work directly go away (Check Status and
Import Bills on the batch form). The list view gets buttons that only trigger
the crons (Check Status, Download, Import).

- `action_trigger_check_status`, `action_trigger_download` and
  `action_trigger_import`: trigger their cron through `sudo`, since plain
  users can't access the crons. In the list header, always shown.

Tests: a plain internal user's click on each button triggers its cron.

6d is done. Step 6 is done.

### After step 6: truncated historic batches

Decided: KSeF stops a package at 10,000 invoices, and the rest of the window
was lost. For a historic batch only, the status cron moves `date_to` to
`lastPermanentStorageDate` and requests the rest of the window right away
(`_request_rest_if_truncated`). Today batches span hours: not handled.

Tests: a truncated historic batch ends at `lastPermanentStorageDate`, and a
new requested historic batch covers the rest of its window.


## Step 7: tests

Most of the tests came with steps 1 to 6, KSeF mocked and time frozen: the
computed fields and their searches, both request payloads, the today and
historic windows and their skip rules, the status, download and import
crons with their retries and failures (still 100, failed download, corrupt
ZIP), the import skipping known bills and bad XMLs, the cleanup, and the
list buttons.

Then one run of all the crons in a row: a today batch is requested, checked,
downloaded and imported, each cron triggering the next one, up to the bill.

Step 7 is done.

### After step 7: switching a database over

Decided: on a database that used the single-invoice download, the historic
walk ends at the first window that holds a `fetched` bill
(`_holds_fetched_bill`, the day of a bill read from its KSeF number with
`_get_ksef_number_date`). It's checked when the window is requested, before
any batch bill is imported into it; the last window is requested, then the
historic date goes to `KSEF_FIRST_DAY`. Nothing stored, and the half-fetched
bills aren't looked at. Tests: the walk ends at the first window holding a
fetched bill.

Decided: the first today batch of the day starts at yesterday 00:00, where
the historic windows end; the next ones of the day chain on the latest today
batch of the day that didn't fail, minus 1 hour, never before yesterday
00:00. Tests: the first window of the day, the chained ones, a failed batch
not chained on, and the first window of the next day.

Decided: the import keeps skipping a half-fetched bill (its KSeF number
exists). With batches enabled, the "Import from KSeF" action only fills the
half-fetched bills, with `l10n_pl_edi`'s `_fetch_bills_data`, by KSeF
number; disabled, it's unchanged. The batch import marks its bills
`fetched`. Tests: the action fills `fetch_ready` and `fetch_failed` bills
without a metadata query, and runs the single-invoice download when
disabled; an imported bill is `fetched`.

Decided: a "KSeF batch download" checkbox in the Accounting settings, under
the KSeF registration, sets `l10n_pl_edi_batch.enabled`. Test: the setting
turns the parameter on and off.
