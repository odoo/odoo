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
  recruitment mailbox while still seeing the roles they'd fit. It *does* replace
  the no-match screen, so a visitor who is told to email recruitment is not also
  told that nothing fits.
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

Two pieces of configuration are required per target model, and both are
per-database:

1. On the model: tick **Allowed to use in forms** (Settings › Technical ›
   Models › the model › Website Forms tab) **and fill "Label for form action"**.
   Without the tick the endpoint answers *"The form's specified model does not
   exist"*. Both are plain UI edits.

   The label looks cosmetic and is not. The form builder's Action dropdown
   prints it raw, so a model with no label is listed as the literal word
   `false` — enable two such models and the dropdown shows two entries both
   reading `false`, with the selected one also reading `false`. It looks exactly
   like the action failing to save. It isn't: the selection stores the model id
   and works fine. Give every model you enable a label and the confusion goes
   away.
2. Every field written has to be un-blacklisted. Fields are blacklisted by
   default — it is a whitelist, not a blacklist.

**Step 2 is the awkward one, and the checkbox is a trap.** The field form does
show a *Blacklisted in web forms* checkbox, but saving it on a stock field fails
with *"Properties of base fields cannot be altered in this manner!"*: the ORM
refuses any write to a field whose state is not `manual`. Core sidesteps its own
guard with raw SQL. So:

- **Studio-created fields** are `manual`, so for those the checkbox works.
- **Stock fields** (`name`, `email`, `phone`, `comment`, …) cannot be whitelisted
  from that form at all. Two ways round it:
  - *With database access:* one UPDATE on `ir_model_fields`, which is what
    `build.py --deploy` targets and what core's own `formbuilder_whitelist`
    does.
  - *UI only, e.g. a trial:* let the form builder do it. Drop a **Form** block on
    a scratch page, clear the fields it came with, point its action at the
    target model, add one row per field you need, and **save the page** —
    saving calls `formbuilder_whitelist` for every non-custom field in the form.
    Then delete the scratch page; the whitelist stays.

    Two traps in that sequence. **`+ Field` creates a *custom* field**, and the
    whitelist call explicitly skips custom fields, so a form full of them
    whitelists nothing: each row has to be linked to the model by opening its
    **Type** dropdown and choosing from the **"Existing fields"** section at the
    bottom (labels, not technical names — `comment` is listed as *Notes*). And
    **a leftover field from the block's previous model aborts the whole save**,
    because `formbuilder_whitelist` validates every name first and raises
    `Unable to whitelist field(s) …`, which reads in the UI as the action
    refusing to stick.

Skipping step 2 fails quietly in a specific way: the record is still created,
but the unrecognised values are dumped into the record's chatter instead of the
fields, leaving e.g. a nameless contact. If a submission "works" but the fields
are empty, this is why.

The endpoint always answers HTTP 200 with a small JSON body: the new record's id
on success, or an error payload. Client code must branch on the body, not the
status code.

This app writes `name`, `email`, `phone` and `comment` on `res.partner`; the
generated snippet's banner lists them, so it always matches what the build
actually sends.

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

The endpoint is captcha-gated, but the gate is inert unless a reCAPTCHA secret is
configured on the database — with no secret the check returns early and passes.

If a target database *does* have one, every submission fails with *"The reCaptcha
token is invalid."* The app does not send a token. It surfaces the message
verbatim on the result screen, so the failure is at least legible. The escape
hatch without code is the `enable_recaptcha` system parameter, which turns the
check off; otherwise the app has to be extended to fetch a token.

Check before deploying: Settings › Technical › System Parameters, search
`recaptcha`.

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
                    questions.json and profiles.json were generated from the
                    module's demo/demo_job_match.xml, so they carry the real
                    questions, profiles and weights. One edit was made on top:
                    the job posting links dropped the demo's /nl_NL/ segment,
                    because odoo.com serves English at the unprefixed URL and
                    redirects /en_US/ to it. Query filters survive that
                    redirect, but the extra hop is pointless.
  lib/*.js          framework: namespace, DOM helpers, flow, transport, chrome
  screens/*.html    one markup fragment per screen
  screens/*.js      one behaviour file per screen
  chrome/*.html     persistent UI around the card (toolbar, brand badge)
  styles/*.css      stylesheets
  dist/             generated output, not committed
```

The built markup is one `#jm_app` wrapper holding a `.jm_card` with the screens
in it, then the chrome. Chrome is outside the card on purpose: it is pinned to
the viewport, and the card clips its own content to keep its rounded corners.

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

### 4.3 Look and interactions

Both are copied from the Survey app's fill-form experience rather than invented,
so the game feels like the product it came from:

- A welcome screen opens with the title, the pitch and a single Start button. It
  is not a step you answer, so it stays out of the progress count.
- Answer rows are barely tinted, darken on hover, and turn primary-subtle once
  selected, with a letter badge on the trailing edge.
- The card's actions bar carries only the primary button and the keyboard hint,
  separated from the question by a rule. The primary button reads Submit instead
  of Continue on the last step.
- Progress and navigation live in a toolbar pinned to the bottom-right: the
  readout, a rule, then the two arrows. Progress counts what is behind you, so
  the first question reads 0%, and it is hidden on screens that do not count.
  `progression_mode` in `data/config.json` switches the readout between a
  percentage and "N of M answered", as Survey's own setting does.
- A brand badge sits at the bottom-left, with the name in the primary colour.
- Validation alerts slide in instead of reserving empty space.
- `Enter` and `→` trigger the primary action, `←` goes back, and a letter picks
  the answer carrying that badge. The arrows disable themselves when there is
  nowhere to go.
- **While a field has the focus, everything belongs to the field and only
  `Ctrl+Enter` moves on** (`Cmd` on a Mac), so a stray Enter cannot submit
  half-typed input. Screens with a field say so in their hint. On a choice
  question, where nothing is focused, plain `Enter` is the shortcut.
- Nothing navigates on its own. Picking an answer only selects it; the visitor
  moves on with Continue or the keyboard, so they can always change their mind
  first. Survey does auto-advance off a single-choice question, and this is a
  deliberate departure from it.

On narrow screens, at Survey's own 768px breakpoint: the brand badge goes, the
toolbar stays but drops the bar and keeps the readout so the arrows are never
squeezed off, the keyboard hint goes, the card runs edge to edge, and the app
reserves bottom padding so the toolbar cannot cover the primary button. The
letter badges hide themselves on touch pointers, where they mean nothing.

The palette is not hardcoded: colours come from Bootstrap custom properties
(`--bs-primary` and friends) when they exist, so an embedded page adopts the
website theme, and fall back to Odoo's purple in the standalone dev preview,
which has no Bootstrap.

Two things worth knowing if you extend this. The keyboard listener is on the
document, as Survey's is, so those keys are claimed for the whole page — fine on
a page whose only content is the app. And hiding a screen does not blur a field
inside it, so the flow explicitly drops focus when switching screens; without
that, a focused text field swallows the letter shortcuts.

## 5. Status

Ported and verified end to end, in the standalone preview and as an anonymous
visitor on a deployed page: the welcome screen, all nine questions from the demo
data (name, email with validation, phone, six choice questions), the Survey look
and every interaction in 4.3, the toolbar and brand chrome, the mobile layout,
the scoring of 2.2, the result screen of 2.3, and the write to a contact with
email and phone filled and the transcript plus ranking in its note.

All of section 2 is implemented: the domain, the scoring rules including
elimination, the result screen, and both special endings.

**The scoring is checked against the reference implementation, not just
believed.** Six answer sets — a job seeker, an intern seeker, a Nordic speaker,
an English-only speaker, someone who speaks none of the listed languages, and a
student-job seeker — were run through the Python module's
`_get_job_match_results` on a database with the demo data, and through the SPA.
All six agree exactly: same survivors, same order, same scores, same
percentages, including the case where nothing survives.

The one known difference is how ties are broken. The SPA breaks them by the
profile's configured sequence, which is deterministic; the reference leaves them
to recordset order. Ties only matter if they reach first place.

Elimination makes `q1` and `q2` matter, which is worth knowing because they
barely did before: `q1` has no point weights at all and `q2` has three against
forty-seven eliminating ones. Both work almost entirely by ruling profiles out.
One answer — "None of the options above" on the language question — rules out
all fourteen on its own, which is why the no-match screen is not optional
polish: without it that answer would end on a blank card.

The two endings of 2.4 were checked the same way, against the reference's own
template conditions, over the four combinations that matter — an answer with a
message and survivors, with a message and nothing left, without a message and
nothing left, without a message and survivors. The SPA makes the same call in
all four: recommendations and message together, message alone, no-match alone,
recommendations alone.

### Not implemented yet

- **Multiple-choice questions.** Described in the data format and handled by the
  ceiling rule, but no question in the demo data uses one and the choice screen
  renders single choice only.
- **Profile images.** The reference shows one next to the best match; the demo
  data sets none, so the SPA has no image support.
