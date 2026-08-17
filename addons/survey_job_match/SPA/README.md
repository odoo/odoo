# Job Matcher SPA

A single-page version of the job-matching survey that runs entirely in the
browser, deployed by pasting one block of HTML into the Website builder. No
Python, no module install, no server restart — which is what makes it usable on
a trial database where we only have the web UI and Studio.

The Python module in the parent directory is the reference implementation. It
stays as-is for now; this folder is where the port lives, and it is intended to
become the delivery path once feature parity is reached.

---

## 1. Why this exists

The Python module needs a module install to reach a database. A trial database
gives us the web UI and Studio, nothing else. Everything below is therefore
expressed as: static markup, static JS, and writes through a public HTTP
endpoint that already exists in stock Odoo.

The trade-off is deliberate and worth stating plainly: **scoring happens on the
client**, so a determined visitor can read the weights and see how answers map
to profiles. For a job-fair game that is acceptable. It would not be acceptable
for anything where the outcome must be tamper-proof.

---

## 2. Business logic being ported

This is the behaviour currently implemented in the Python module, described
without reference to its implementation.

### 2.1 Domain objects

| Concept | What it is |
| --- | --- |
| **Job profile** | A possible outcome of the game — a role. Has a display name, an ordering, an image, a short description, and a link to the real job posting. Can be archived. |
| **Question** | Asked one per screen. Either a choice question (single or multiple) that feeds scoring, or a plain text question that only captures contact details. |
| **Answer** | One option of a choice question. May carry its own closing message (see 2.4). |
| **Answer weight** | The link between one answer and one profile: a number of points, or a flag marking the answer as *eliminating* for that profile. At most one weight per answer/profile pair. |
| **Submission** | One visitor's run: the answers given, the resulting best profile, and whether every profile was eliminated. |

### 2.2 Scoring

Given the answers a visitor picked:

1. Only profiles that are weighted somewhere in the questionnaire take part. If
   no weights exist at all, there is no result to show.
2. **Elimination is absolute.** If any picked answer is marked eliminating for a
   profile, that profile is removed from the results regardless of how many
   points it accumulated. This models hard requirements — a language the role
   needs, or "I want an internship" ruling out the full-time roles.
3. **Points accumulate.** Every picked answer adds its points to each profile it
   weights. Points may be negative. Weights flagged as eliminating contribute no
   points.
4. **The percentage is relative to what was achievable**, not to other
   candidates. For each question, the best possible contribution toward a
   profile is computed: for a multiple-choice question the sum of all its
   positive weights for that profile (you could tick them all), for a
   single-choice question only the single best positive weight. Those per
   question maxima are summed into the profile's ceiling.
5. The match percentage is the profile's score over its ceiling, rounded, and
   clamped into 0–100. A profile with a ceiling of zero scores 0%.
6. Results are ranked by score first, then by percentage.

Two consequences worth remembering, both inherited from the reference
implementation: a profile with a score of zero is still a valid result and will
be shown if nothing eliminated it; and eliminating weights are excluded from the
ceiling, so marking an answer as eliminating never inflates the percentages.

### 2.3 Result screen

- The top-ranked profile is presented as the best match: image, name, match
  percentage, a meter reflecting that percentage, the description, and a button
  to the job posting.
- Below it, the next two profiles are listed with their own percentages and
  smaller meters, as roles the visitor would also fit.

### 2.4 The two special endings

- **Per-answer closing message.** Any answer may carry its own message. If the
  visitor picked such an answer, that message is appended below the
  recommendations — it does not replace them. The case it exists for: someone
  looking for a student job, who should be pointed at internships and a
  recruitment mailbox while still seeing the roles they'd fit.
- **No-match screen.** When every profile has been eliminated and no picked
  answer carries a message of its own, a questionnaire-level message is shown
  instead of results, with a call-to-action to the jobs site. This is the
  "nothing in our Belgian offices right now, look at the international ones"
  ending.

If several picked answers carry messages, the reference implementation shows
only the first.

### 2.5 What gets captured

Email and phone are asked as ordinary optional text questions, carrying a GDPR
notice in their description; the email answer is what identifies the submission.
The recorded submission keeps the answers, the winning profile, and the
all-eliminated flag so unmatched visitors can be reported on.

---

## 3. How deployment works

### 3.1 The delivery vehicle

The build produces one self-contained block: markup, a `<style>`, and a
`<script>`. It goes into a Website page through **Edit → drag the "Embed Code"
snippet → Edit Code → paste → Save**.

The snippet stores its payload twice — once in a `<template>` the editor
restores from, once in the live container that renders. The editor strips
scripts while you are editing and reinstates them on the published page, so
**the app is inert in edit mode and only runs on the published page.** Test on
the published URL, never in the editor.

Because the payload lands in a `<template>` as well as in the live DOM, the app
must be safe against being present twice in the document. Template content is
inert and not reachable by `querySelector`, so in practice only the live copy
initialises, but the boot code still guards with a marker attribute.

### 3.2 Writing to the database

Records are created by POSTing form-encoded data to `/website/form/<model>`, a
public endpoint in the `website` module. It creates the record as superuser, so
an anonymous visitor can write without any portal account.

Two pieces of configuration are required per target model, both clickable in the
web UI with developer mode on, and both are per-database:

1. On the model: tick **Allowed to use in forms** (Settings › Technical ›
   Models › the model › Website Forms tab). Without it the endpoint answers
   *"The form's specified model does not exist"*.
2. On every field written: untick **Blacklisted in web forms**. Fields are
   blacklisted by default — it is a whitelist, not a blacklist. Studio-created
   fields are no exception and need the same untick.

Skipping step 2 fails quietly in a specific way: the record is still created,
but the unrecognised values are dumped into the record's chatter instead of the
fields, leaving e.g. a nameless contact. If a submission "works" but the fields
are empty, this is why.

The endpoint always answers HTTP 200 with a small JSON body: the new record's id
on success, or an error payload. Client code must branch on the body, not the
status code.

### 3.3 CSRF

CSRF is only enforced when the request carries an authenticated session. An
anonymous visitor needs nothing. But *you*, previewing while logged in, are
authenticated — so the request must include the token that every frontend page
exposes as a JS global, or your own testing fails with "Session expired
(invalid CSRF token)" while real visitors are fine. The app always sends it.

### 3.4 Making the page show only the app

A page is wrapped in the website layout, so it comes with a header and footer.
Both can be switched off per page from the builder: select the header →
**Header Position → Hidden**; select the footer → untick **Page Visibility**.
This sets flags on the page record; the layout then hides them with a CSS class
rather than removing them, so the frontend asset bundles still load. That is
fine for a survey. A genuinely bare page — no Odoo CSS or JS at all — would
require a custom controller, i.e. Python, which defeats the purpose.

These are per-page settings: every page you create needs them set again.

### 3.5 The captcha gate

The endpoint is captcha-gated, but the gate is inert unless a reCAPTCHA secret
is configured on the database. If a target database has one, submissions will
need a token and the app will have to be extended.

### 3.6 The XML constraint (important)

A page's markup is stored as XML in the view record. Inside a `<script>` or
`<style>`, a bare `&` or `<` is an XML parse error, which breaks saving or
rendering the page.

- **Hand-written JS and CSS may not contain `&` or `<`.** No `&&` (use nested
  ifs or `||`), no `i < n` loops (flip the comparison, or use `forEach`), no
  bitwise `&`. The build refuses to emit output that violates this.
- **Data files are exempt.** The compiler escapes them when inlining, so
  question text, descriptions and job posting URLs with query strings are all
  safe. This matters: the reference demo data is full of posting URLs with `&`
  in their query string.
- **No `--` inside an HTML comment.** XML forbids a double hyphen in a comment,
  and the page is rejected on save with a parse error. Comments inside `<script>`
  are unaffected — this applies only to real `<!-- -->` comments, so watch it in
  `screens/*.html`.

---

## 4. Build system

### 4.1 Layout

```
SPA/
  build.py          the compiler; no dependencies beyond the standard library
  build.json        build and deploy settings (never shipped into the app)
  data/*.json       content and app config, inlined as JM.data[<filename>]
  lib/*.js          framework: namespace, DOM helpers, flow, transport
  screens/*.html    one markup fragment per screen
  screens/*.js      one behaviour file per screen
  styles/*.css      stylesheets
  dist/             generated output, not committed
```

Files are concatenated in **filename order**, which is why they are numbered in
hundreds — the same convention Odoo uses for snippet assets. `lib/` is emitted
before `screens/`. To insert a file between two others, pick a number in
between; there is no manifest to update.

Everything is wrapped in one IIFE, so the shared `JM` namespace never touches
`window` — except in a dev build, where it is exposed for console poking. Source
files use `JM` directly and must not redeclare it.

Adding a screen is two files: `screens/NNN_name.html` with the markup, and
`screens/NNN_name.js` registering behaviour under the same screen name.

### 4.2 Commands

```
python3 build.py                     build dist/spa.html and dist/dev.html
python3 build.py --deploy            build, publish, and open the page
python3 build.py --deploy other_db    publish to another database instead
```

`--deploy` takes no argument in normal use: the target database, the host and
the page URL all come from `build.json`, and the page is opened in a browser
when the deploy succeeds.

`dist/spa.html` is what you paste into the Embed Code snippet.

`dist/dev.html` opens directly in a browser with no Odoo running. The transport
is stubbed, so submitting reports a fake record id instead of writing anything.
This is the fast loop for content and styling work.

`--deploy` publishes to a local database through `odoo shell`, creating the page
on first run and updating it in place afterwards, with header and footer hidden.
It rewrites the page's markup wholesale, so any edit made to that page in the
builder is overwritten on the next deploy. Treat deployed pages as build output.

---

## 5. Status

Ported and verified end to end (anonymous visitor in a real browser, contact
created with the answer recorded): the screen flow, a name entry screen, a
single choice question driven by the data files, and submission to a contact.

Not yet ported: everything in section 2 beyond a single question — profiles,
weights, elimination, scoring and percentages, the result screen with meters and
runners-up, the two special endings, and email/phone capture.
