# KSeF Batch Download: implementation plan

What we're going to change in the code, step by step, to reach the design in
`DESIGN.md`. Each step is one commit, tested by hand from the Odoo shell
before the next one starts.

Questions still to decide are marked "Open:".


## Where the code is today

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

- `tools/ksef_api_service.py`, `download_batch_request`: `dateType`
  `PermanentStorage` instead of `Invoicing`.
- `models/account_move.py`: `KSEF_WINDOW` = 7.
- `_request` stops writing `status` and `active`.

Test from the shell: request a small window, check the batch is created and
reaches 200.


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


## Step 4: cleanup

`_gc_batch_downloads`: delete the batches whose `state` is done or failed and
whose `write_date` is more than 30 days old. Nothing else.

Test from the shell: backdate a done batch with SQL, run the method, check
it's gone and a recent one isn't.


## Step 5: today and historic crons

The request logic moves to the batch model, so that the crons live there:

- `_is_enabled()`: the `l10n_pl_edi_batch.enabled` check, moved from
  `account.move`.
- `_cron_request_today()`: per company, the window from `DESIGN.md`, skip if
  a today batch is still requested, `_request`, commit. At the end, trigger
  the status cron.
- `_cron_request_historic()`: per company, the historic date rules from
  `DESIGN.md`. At the end, trigger the status cron.
- On `KSeFRateLimitError`: stop, and trigger the same cron after
  `retry_after` seconds.

`models/account_move.py`: the override of `_cron_l10n_pl_edi_download_bills`
calls `_cron_request_today()` when enabled, `super()` otherwise. The
commented-out block and `_l10n_pl_edi_trigger` go away.

`data/ir_cron_data.xml` (and the manifest): the historic cron, daily.

Test from the shell: run each method, check the windows and the batches
created; run them again, check they skip.


## Step 6: status, download and unzip+import crons

On the batch model, three methods, one per cron, all starting with
`_is_enabled()`:

- `_cron_check_status()`: due requested batches (`write_date + 10 * 2 **
  retry_count` past), today first. Lock, `check_status`, commit. Still 100:
  `retry_count += 1`, trigger itself at the next due time. 200: reset
  `retry_count`, trigger the download cron.
- `_cron_download()`: one missing part of one due downloading batch, today
  first. Lock, download, commit, `_notify_progress`. On failure:
  `retry_count += 1`, trigger itself at the next due time. All parts in:
  trigger the unzip+import cron.
- `_cron_unzip_import()`: one downloaded batch, today first. Lock, `unzip`,
  `import_attachments`, `_notify_progress`. Historic batch done: trigger the
  historic cron.

Locking: `res.company._with_locked_records(batch, allow_raising=False)`;
skip the batch if it's locked. The point is that nobody modifies a batch while
a cron works on it: the user's change waits until the cron commits.

`part.download()`: on failure, bump `retry_count`; after the 9th retry,
write status 999 with the details in `content`. Today it just logs and
continues.

`data/ir_cron_data.xml`: the three crons.

Decided: besides being triggered, the status, download and unzip+import crons
run at least once a day, as a safety net in case a trigger is lost.

Decided: the list view of batches gets buttons that trigger the crons (e.g.
"Check status", "Download", "Import"), instead of doing the work right away.

Decided: the buttons that do the work directly are removed: Download on the
parts, and Check Status, Unzip, Import Bills on the batch form. The work only
happens in the crons; the list buttons just trigger them.

Test from the shell: request a batch, then run the three methods by hand in
order, and check the state after each.


## Step 7: tests

`tests/test_l10n_pl_edi_batch.py`, with the KSeF service mocked and time
frozen:

- the computed fields and their searches;
- the today and historic windows, and the skip rules;
- retries and failures (still 100, failed download, corrupt ZIP, expiry);
- the import skipping bills already imported;
- the cleanup.
