# KSeF Batch Download

Downloads the vendor bills received in KSeF in batches, instead of one by one.

Module: `l10n_pl_edi_batch`

KSeF lets a company download at most 64 invoices per hour. To get more, a
company asks KSeF for a batch: one ZIP with all the invoices of a timeframe,
from `date_from` to `date_to`.

It's opt-in. The module is auto-installed with `l10n_pl_edi`, but nothing
changes until the system parameter `l10n_pl_edi_batch.enabled` is set. Until
then, `l10n_pl_edi` (unchanged from 18.0) keeps downloading bills one by one,
as before. How to switch existing databases over is still to be discussed.

A batch is harder to handle than a single invoice:

- It isn't ready right away. KSeF builds the ZIP in the background, and we
  have to poll the status API until it's done.
- It can fail. The request can be rejected, or the ZIP can expire before we
  download it.
- It comes in parts. The ZIP is split into parts of up to 50 MB, each
  encrypted with a symmetric key (AES-256) that we generate for each request
  and send to KSeF with it. We keep the key on the batch, download and decrypt
  each part with it, then join the parts back together.
- It has a size limit. A batch holds at most 10,000 invoices, so we have to
  keep the timeframes small.
- It takes time. Polling the status until the ZIP is ready, downloading the
  parts, merging them and importing the bills takes much longer, all together,
  than an Odoo cron is allowed to run.

So the work is split into five crons. Each one does one kind of work, so the
steps move independently: a long import never blocks polling or downloads.

- today (every 3h): requests a batch of the last two days.
- historic (daily): requests a batch of an older week, back to KSeF's start.
- status: checks each waiting batch (100); once ready (200), starts download.
- download: downloads one batch part, decrypting it on the fly, then retriggers.
- unzip + import: merges the parts, unzips, turns each XML into a vendor bill.

It recovers on its own: waits and downloads are retried, the today cron
covers again the timeframe of a failed batch, bills already imported are
skipped, and old batches are cleaned up. Each batch is a record you can open,
inspect and fix by hand.

The sections below explain each part, and why it works this way. Anything
marked (planned) is designed, but not coded yet.

## KSeF facts we rely on

Straight from the KSeF 2.0 (`https://api.ksef.mf.gov.pl/docs/v2/openapi.json`).

### Export status codes

An export is at 100 while KSeF builds it, and at 200 once it's ready to
download. Any other code is an error: see `InvoiceExportStatusResponse` in the
spec for the full list.

The status of an export stays around for 7 days. Once ready, the package has
its own expiration date (`packageExpirationDate`). After that, its parts can't
be downloaded anymore.

### Limits

- Rate limits per company: single invoice download 8/s, 16/min, 64/hour;
  invoice metadata query 8/s, 16/min, 20/hour; export requests 8/s, 16/min,
  20/hour; status checks 10/s, 60/min, 600/hour.
- At most 10 exports running at once per company.
- One export holds at most 10,000 invoices or 1 GB (compressed). Beyond that,
  the package is truncated (`isTruncated = true`), and KSeF tells us the date
  from which to request the next export.
- A package comes in parts of at most 50 MB each.
- One export covers at most 100 days.
- When we're rate-limited, KSeF answers HTTP 429 with a `Retry-After` delay.

### Date types

The spec recommends using the `PermanentStorage` date for incremental downloads.
An invoice accepted at 10:00 may not be stored yet at 10:05: filtering by
the storage date means a window only holds invoices that are really there.

Decision: the batch export filters by `PermanentStorage` (planned).


## The batch export API, step by step

1. Request (`POST /invoices/exports`): we send the date window, the date type
   and the encryption data: a random AES-256 symmetric key and IV, plus the
   key encrypted with the KSeF public key. KSeF answers right away with a
   reference number.
2. Status (`GET /invoices/exports/{referenceNumber}`): we keep asking until
   the status isn't 100 anymore. At 200, the answer describes the package:
   invoice count, size, truncation flag, expiration date, and the list of
   parts, each with its ordinal number and download URL.
3. Download: each part is downloaded from its URL and decrypted on the fly
   (AES-256-CBC with PKCS#7 padding, using our symmetric key and IV).
4. Merge: the decrypted parts are slices of one single ZIP file, so we glue
   them together in ordinal order.
5. Unzip: the ZIP holds one XML per invoice, named `{ksefNumber}.xml`, plus a
   `_metadata.json` file that we ignore.
6. Import: each XML becomes a vendor bill in Odoo, through the standard
   attachment import.


## Models

### `l10n_pl_edi_batch.download`

One record per export request.

Stored fields:

```
name                      KSeF reference number of the export (unique)
company_id                Company the export belongs to
content                   Last full status answer from KSeF (JSON)
date_from                 Start of the export window (UTC)
date_to                   End of the export window (UTC)
retry_count               Retries of the current step: polls at 100, then
                          failed part downloads
part_ids                  The parts of the package
raw_symmetric_key         Encryption data (system group only)
encrypted_symmetric_key   ...
raw_iv                    ...
```

Computed fields (not stored, searchable): we only store what can't be
derived from the rest.

```
state                     Where the batch is, see below
error                     The error, from the saved answer: the code, then
                          the description and the details
date_expiry               Package expiration date, from `content`
is_expired                date_expiry is in the past
kind                      historic when date_to <= create_date - 24h,
                          otherwise today
```

`content` is a `fields.Json`, so in Python it's already a dict. The KSeF
status code is `content['status']['code']`, read by `_get_ksef_status_code`:
100 while no answer is saved yet. `date_expiry` is the ISO date in
`content['packageExpirationDate']`, converted to UTC.

There's no `status` field: `state` already says what the code means (100
requested, 200 ready, anything else failed), and the error text starts with
the code, e.g. "415: <KSeF's description>". The codes are module constants:
`KSEF_IN_PROGRESS` (100), `KSEF_READY` (200) and `ODOO_ERROR` (999).

Our own errors (a part download still failing after 9 retries, a corrupt ZIP)
go in the same place: `_set_odoo_error` writes `content['status']` with our
code 999 "Odoo Error" and the details, like KSeF does for its errors. No
separate error field is needed.

The search methods don't need SQL on the JSON column. There are at most about
300 batches per company (8 today batches a day, kept 30 days, plus about 40
historic ones), so they read the batches, filter them in Python on the
computed value, and return `[('id', 'in', ids)]`.

The states, computed in this order:

```
failed        code other than 100/200 (including 999), or retry_count above
              9 (MAX_RETRIES), or expired while parts are still missing
requested     code 100
downloading   code 200, some parts have no file yet
downloaded    code 200, every part has its file
done          code 200, no parts left
```

The parts are deleted only once the import is over, so "no parts left" means
done. A batch with 0 invoices has no parts at all, so it's done right away.

These computed fields replace what was first spread over the KSeF status, the
`active` flag, the dates and the parts' file sizes: the logic, the searches
and the views all get simpler. Done and failed batches play the role the
inactive batches had.

The model has debug-mode views, so a batch can be inspected and fixed by hand
if something goes wrong. The work itself only happens in the crons: the list
view has buttons that trigger them (planned), and no button does the work
directly.

### `l10n_pl_edi_batch.part`

One record per part of a package.

```
batch_id           The batch the part belongs to
part_number        KSeF ordinal number, used to merge the parts in order
download_url       Where to download it
download_method    HTTP method to download it
decrypted_file     The decrypted slice of the ZIP; empty until downloaded
```

`decrypted_file` is a binary field stored as an attachment, linked to the
part and protected by the part's access rights, like the other EDI binaries.
No attachment exists until the download.

The parts are deleted once all their invoices are imported (planned): they
can be up to 50 MB each. Until then, they're the only copy we need: the XMLs
are never kept on the batch.

### `res.company`

```
l10n_pl_edi_batch_historic_date   End of the next historic window
```

A stored company field, rather than one system parameter per company. It
can't be computed from the historic batches: the cleanup deletes them after 30
days, and the date would jump back to yesterday, downloading the whole history
again.


## The crons

Five crons, one per kind of work. Odoo runs different crons in parallel, but
never the same cron twice at once: with one cron per step, each step moves
independently, and a long import doesn't hold back the polling or the
downloads of other batches. They all check `l10n_pl_edi_batch.enabled` first.

The today and historic crons are the only ones requesting batches from KSeF.
The cleanup never calls KSeF.

### Common rules

- Progress: the status, download and unzip+import crons use the cron progress
  API, `ir.cron._notify_progress(done=..., remaining=...)`, like the invoice
  sending cron in `account` and `l10n_my_edi`. When a cron reports work left,
  Odoo runs it again right away (up to 10 times in a row, then reschedules it
  as soon as possible). No need to retrigger it by hand.
- Handing over: a cron triggers the next one with `ir.cron._trigger()` when
  it leaves work for it. Several triggers are harmless: one run consumes them
  all.
- Waiting: a batch that must wait is due again when
  `write_date + 10 * 2 ** retry_count` is past (each retry writes
  `retry_count`, which updates `write_date`). Each retry triggers the cron at
  that time, with `ir.cron._trigger(at=...)`, so every waiting batch has its
  own trigger. The cron only handles the batches that are due.
- Commits: crons that loop over companies commit after each company, the
  status and download crons after each batch or part, the unzip+import cron
  after each bill. A failure then only loses the current unit of work. Commits
  go through `_can_commit()`, so they're skipped in tests.
- Locking: the batch being processed is locked with
  `res.company._with_locked_records` (`SELECT ... FOR UPDATE SKIP LOCKED`), so
  nobody modifies it while a cron works on it: a change waits until the cron
  commits. A manual trigger of a cron that's already running just waits for
  the next run, since Odoo never runs the same cron twice at once.
- Rate limit: on HTTP 429, the cron stops and triggers itself again after the
  `Retry-After` delay. The limit applies to the whole company anyway.
- Retries: a batch still at 100, or a part download that failed, is retried
  after `10 * 2 ** retry_count` seconds, at most 9 times (10 s, 20 s, ...
  2560 s, about 85 minutes in total, well within the 3 hours of the today
  cron). `retry_count` is reset to 0 when the status reaches 200.
- Priority: the status, download and unzip+import crons handle today batches
  before historic ones, so the history never delays current invoices.
- Small batches: we don't handle truncated packages, and we don't pre-check
  the size with the metadata API. Instead, the windows stay small: about 2 days
  for the today cron, 7 days for the historic cron. The today cron must always
  keep working. The historic cron can fail: it's old data, it can be requested
  again, and batches can be fixed by hand.

### Failures

A batch that fails goes to `failed`, the error is logged, and we move on: its
timeframe isn't requested again automatically. A batch fails when:

- KSeF answers a status other than 100 or 200;
- it's still at 100 after 9 retries;
- a part download still fails after 9 retries;
- the ZIP is corrupt;
- the package expired before it was downloaded.

For the today cron this costs nothing: its next run starts from the latest
today batch that didn't fail, so it covers the failed timeframe again (as long
as it's not older than yesterday). For the historic cron, the timeframe is
skipped, and its invoices have to be requested by hand. When a historic batch
fails, the historic cron is triggered, so it moves on to the next week right
away.

The failed batches stay visible for 30 days, which makes problems easy to
spot.

### 1. Today cron: fresh invoices

The existing cron, every 3 hours:
`l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills`. The batch module overrides
its method: when batches are disabled, it calls the original single-invoice
download.

For each company:

- Skip the company if one of its today batches is still requested, to save
  KSeF requests.
- Otherwise request a batch for the window from

  ```
  max(yesterday 00:00 UTC,
      date_to of the company's latest today batch not failed) - 1 hour
  ```

  to now. The 1-hour overlap covers the delay before KSeF stores an invoice;
  invoices downloaded twice are skipped at import.
- Save the batch with empty content (so code 100, requested), and commit.

At the end, trigger the status cron if a batch was requested. The first
status check is the status cron's job.

### 2. Historic cron: past invoices

A new cron, scheduled daily, and also triggered when a historic batch is done
or failed. It walks backwards in time, from yesterday to the day KSeF 2.0
went live (`KSEF_FIRST_DAY`, 2026-01-31), one 7-day window at a time.

For each company:

- `res.company.l10n_pl_edi_batch_historic_date` holds the end of the next
  window. It starts at yesterday 00:00 UTC.
- The window is `[max(historic date - 7 days, KSEF_FIRST_DAY), historic
  date)`, with `KSEF_WINDOW` = 7 days, a constant.
- Skip the company if its latest historic batch isn't done or failed yet.
- Latest historic batch done: move the historic date back to its `date_from`,
  and request the next window.
- Latest historic batch failed: log it, move the historic date back to its
  `date_from` anyway, and request the next window.
- When the historic date reaches `KSEF_FIRST_DAY`, there's nothing left to do.
  The cron does nothing, but stays active. To download the history again, set
  the historic date to a later date.
- Like the today cron: save the batch as requested, commit per company, and
  trigger the status cron.

With 278 days of history (on 2026-11-05) and 7-day windows, that's 40 windows
per company. Since the next window is requested as soon as the previous one is
done, they follow each other within hours, not once a day. It also means at
most one historic batch in progress per company, which keeps the load on the
instance low.

### 3. Status cron

For each requested batch that is due (see Waiting), today batches first:
lock it, ask KSeF for the status, save the answer in `content`, and commit.
The state follows by itself (it's computed):

- Still 100: bump `retry_count`, and trigger the cron again after
  `10 * 2 ** retry_count` seconds. After 9 retries, the batch is failed.
- 200 with invoices: reset `retry_count`, create the parts (the batch is now
  downloading), and trigger the download cron.
- 200 with 0 invoices: nothing to download, the batch is done.
- Any other code: the batch is failed.

### 4. Download cron

Each run downloads one missing part of a downloading batch (today batches
first), decrypting it on the fly into the part's own attachment, commits, and
reports the parts left with `_notify_progress`, so Odoo runs it again.

When all the parts of a batch are in, the batch is downloaded, and the
unzip+import cron is triggered. A failed download is retried after
`10 * 2 ** retry_count` seconds, at most 9 times per batch; after that, the
batch failed (see Failures).

### 5. Unzip+import cron

Each run takes one downloaded batch (today batches first), and:

1. Joins the parts in ordinal order into a temporary ZIP, and opens it. The
   XMLs are read from the ZIP one by one; nothing is saved on the batch.
2. For each XML, skips it if its KSeF number already has a vendor bill in the
   company (the `UNIQUE(l10n_pl_edi_number, company_id, move_type)` constraint
   forbids a second one anyway). Otherwise creates the bill with the XML
   attached to it, imports it, sets its KSeF number, and commits: one commit
   per bill, so an interrupted run never leaves a bill without its KSeF
   number.
3. Once every XML is handled, deletes the parts: the batch is done. For a
   historic batch with older history left (`date_from > KSEF_FIRST_DAY`),
   triggers the historic cron.
4. Reports the batches left with `_notify_progress`.

If a run is interrupted (time limit, crash), the parts are still there and
the batch stays downloaded: the next run joins and opens the ZIP again, and
skips the bills already created. Both are fast.

If an error happens before the standard import can catch it (e.g. an XML that
can't even be read), every run would stop at the same XML. So such an error
bumps `retry_count`, and after 9 retries the batch gets our 999 error and
fails.

An XML that can't be imported doesn't fail the batch. The standard import
(`account.move._extend_with_attachments`) catches the decoder error, posts it
in the bill's chatter, and moves on to the next file. A corrupt ZIP does fail
it (see Failures).


## Cleanup

Done by the daily autovacuum, `_gc_batch_downloads` (planned: today it still
deletes all done and failed batches right away). It never calls KSeF.

- Batches done or failed more than 30 days ago are deleted, with their
  parts. They're kept for a while because the today cron starts from the
  latest today batch, and because they're useful for debugging.
- Batches whose package expired before they were downloaded need nothing:
  their computed state is already failed (see Failures).


## Where we are

Done:

- the models and views;
- the request, status, download, unzip and import methods, tested by hand from
  the Odoo shell against the KSeF test environment;
- the `l10n_pl_edi_batch.enabled` parameter;
- the cleanup of the old attachment-based code.

Next up, in this order. Each step is one commit, tested by hand from the Odoo
shell before the next one:

1. Fields (done): `error`, `date_expiry`, `kind` and `state` computed,
   `retry_count` added, `status` and `active` dropped, parts holding a
   `decrypted_file`, the historic date on `res.company`; the views follow.
2. Request: the `PermanentStorage` date type, and `KSEF_WINDOW` = 7 days.
3. Import: one method that joins the parts, reads the XMLs from the ZIP,
   skips the bills already imported, creates and imports the others with one
   commit per bill (through `_can_commit()`), and deletes the parts at the
   end. No XMLs kept on the batch.
4. Cleanup: delete only the batches done or failed more than 30 days ago.
5. The today and historic crons.
6. The status, download and unzip+import crons.
7. Tests, with frozen time so that they don't depend on how fast they run.

Questions, ideas, a better name for the historic cron?
Ping us, we'd love to hear from you.
