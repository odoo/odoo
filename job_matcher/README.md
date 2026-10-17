# Job Matcher SPA

## What

A job-fair game: "Which Odoo job fits you?". A visitor answers ten questions on
their phone — name, email, phone, which activity they joined, then six about
what they are looking for, which languages they work in and how they like to
work — and lands on a result screen naming the role that fits them best, with a
match percentage, up to two runner-up roles and a link to each real job posting.
Fifteen roles compete; answers both add points and eliminate roles outright, so
"I want an internship" or a missing language rules roles out whatever else was
scored.

Every run writes a contact (`res.partner`) carrying the name, email and phone
given, with the full transcript and the ranking in its notes, so the day leaves
behind a lead list.

The whole app is one block of HTML — markup, styles and script in a single
generated file — pasted into a Website page. Scoring runs in the browser; the
only server call is the one that saves the contact.

## Why

Fun way for visitors to get link to the best matched role for them and a 
way for Odoo to keep interesting information about prospects (eg. language)
to help with hiring in future if no immediate match.

## How

### Setting up a database (to do once, but recording for completeness)

**Step 1 — allow the model.** Settings › Technical › Models › `res.partner` →
**Website Forms** tab → tick **Allowed to use in forms**, fill **Label for form
action** (e.g. "Create a Prospect"), save.

**Step 2 — whitelist every field the app writes**: `comment`, `email`, `name`,
`phone`. Fields are blacklisted by default — it is a whitelist, not a blacklist —
and a stock field cannot be whitelisted from its own form: the *Blacklisted in
web forms* checkbox is there, but saving it fails with *"Properties of base
fields cannot be altered in this manner!"*, because the ORM refuses any write to
a field whose state is not `manual`. Core sidesteps its own guard with raw SQL.
Studio-created fields are `manual`, so for those the checkbox does work.

With database access, that is one UPDATE on `ir_model_fields`. Through the UI
only, which is the case on a trial, it means building a contact form and then
deleting it. Kind of weird, but trust the magic: saving the form is what
whitelists the fields, and the whitelist outlives the form.

1. Website → Edit → Blocks → **Contact and Form** → pick one with inputs
   (e.g. "Let's connect").
2. Delete every input the block came with. Fine if some cannot be deleted. This
   matters: saving with a field that does not exist on `res.partner` raises
   *"Unable to whitelist field(s) …"* and silently reverts the block's action to
   `false`, which reads in the UI as the action refusing to stick.
3. Set the block's action to create a `res.partner` record: **Style → Form →
   Action →** the label from step 1.
4. For each field name above, add a row **and link it to the model**: click
   **+ Field**, then open that field's **Type** dropdown and pick the entry
   under the **"Existing fields"** heading at the bottom of the list. Watch out:
   a field added with **+ Field** alone is a *custom* field (it reads "Custom
   Text"), and custom fields are deliberately skipped by the whitelist call, so
   they achieve nothing here. That list shows labels, not technical names:
   `comment` is listed as *Notes*.
5. **Save the page.** Saving is the step that actually calls
   `formbuilder_whitelist`.
6. Edit the page again and delete the Form block.

**Step 3 — hide the header and footer**, so only the app shows. In the editor:
click the header, set **Header Position → Hidden** in the right panel; click the
footer, untick **Page Visibility**; save. Both are per page, so every new page
needs them again. They hide the chrome with a CSS class rather than removing it,
so the site's assets still load — fine here. A genuinely bare page would need a
custom controller, i.e. Python, which defeats the purpose. `build.py --deploy`
sets both for you.

**Step 4 — deploy.** Website → Edit → drag the **Embed Code** snippet onto a
page → **Edit Code** → paste all of `dist/spa.html` → Save → Publish. The app is
inert in edit mode, so test on the published page.

### How it scores

1. Only roles weighted somewhere in the questionnaire take part.
2. **Elimination is absolute.** One picked answer marked eliminating for a role
   removes it, whatever it scored.
3. **Points accumulate**, and may be negative. Eliminating weights carry no
   points.
4. **The percentage is relative to what was achievable**, not to other visitors:
   each question contributes its best possible weight for that role (for a
   multiple-choice question, the sum of its positive weights) to a ceiling, and
   the percentage is score over ceiling, rounded, clamped to 0–100.
5. Results rank by score, then percentage. A role that scored zero is still a
   valid result if nothing eliminated it.

The result screen shows the top role with its percentage and meter, then up to
two runners-up — one scoring under `runners_min_percentage` is dropped rather
than printed as a weak suggestion — then one closing line. Two endings replace
part of it: any answer may carry a **closing message**, appended below the
recommendations (the case it exists for is the student-job seeker, pointed at
internships and a recruitment mailbox while still seeing their fit), and it
replaces the **no-match screen**, which otherwise appears when every role was
eliminated. One answer — "None of the options above" on the languages
question — eliminates all fifteen on its own, so that screen is not optional
polish.

The six scoring questions are mandatory. The four capture questions are optional
except "Which activity did you join?", which describes the event rather than the
person. A blank name falls back to `anonymous_name` from `data/config.json`,
because a nameless partner fails a model constraint and loses the submission.

### Building it

```
job_matcher/
  build.py          the compiler; standard library only
  build.json        build and deploy settings, never shipped into the app
  data/*.json       content and app config, inlined as JM.data[<filename>]
  lib/*.js          namespace, DOM helpers, flow, transport, scoring, chrome
  screens/*.html    one markup fragment per screen
  screens/*.js      one behaviour file per screen
  chrome/*.html     persistent UI around the card (toolbar, brand badge)
  styles/*.css      stylesheets
  dist/             generated output, not committed
```

```
python3 build.py                    build dist/spa.html and dist/dev.html
python3 build.py --deploy           build, publish, and open the page
python3 build.py --deploy other_db  publish to another database instead
```

Files are concatenated in **filename order**, which is why they are numbered in
hundreds, the same convention Odoo uses for snippet assets; `lib/` comes before
`screens/`, and inserting a file between two others is a matter of picking a
number in between. There is no manifest. Everything is wrapped in one IIFE, so
the shared `JM` namespace never touches `window` except in a dev build, where it
is exposed for console poking. Adding a screen is two files:
`screens/NNN_name.html` and `screens/NNN_name.js` registering behaviour under
the same screen name.

`dist/spa.html` is what you paste into the snippet. `dist/dev.html` opens
directly in a browser with no Odoo running, with the transport stubbed so
submitting reports a fake record id — the fast loop for content and styling.
`--deploy` publishes to a local database through `odoo shell`, creating the page
on first run and updating it in place afterwards, header and footer hidden. It
rewrites the page's markup wholesale, so treat deployed pages as build output:
anything edited in the builder is overwritten on the next deploy.

The look and the keyboard behaviour are copied from Survey's fill-form
experience rather than invented. `Enter` and `→` trigger the primary action, `←`
goes back, and a letter picks the answer carrying that badge — except while a
field has focus, where everything belongs to the field and only `Ctrl+Enter`
moves on, so a stray Enter cannot submit half-typed input. Nothing navigates on
its own: picking an answer only selects it. Colours come from Bootstrap custom
properties when they exist, so an embedded page adopts the website theme, and
fall back to Odoo's purple in the standalone preview.

