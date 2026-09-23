# http_routing — Traps

Behaviours here that look wrong and are right, look like duplication and are
not, or look safe and are not. Each entry says what it costs to get wrong and
names the test that pins it, so a future refactor fails loudly instead of
quietly.

## 1. The two "is this URL local?" guards are NOT duplicates

`_url_lang` tests scheme/netloc via `urlparse`; `_url_localized` tests the
leading slashes. Same shape, **different question**:

```python
_url_for("#top", "fr_FR")  # -> "/fr/current/page#top"
_url_localized("#top", "fr_FR")  # -> "#top"
```

`_url_lang` asks *"is this relative"*, so `urljoin` can root it against the
current page — with a language forced it deliberately accepts a bare fragment,
which is exactly what a language switcher needs to keep the anchor.
`_url_localized` asks *"is this already a path I can match against the routing
table"*, and `#top` is not one.

Unifying them removes anchor-preserving language switching.
→ `TestUrlLang.test_bare_fragment_is_rooted_when_a_language_is_forced`

## 2. `_url_for` is not idempotent, on purpose

In a French context `_url_for("/en/shop")` → `/shop` → `/fr/shop`. The first step
strips an explicitly-default-language prefix (the server 303s it away anyway,
case /6), the second inserts the context language. Both are correct in
isolation; composed, they are not stable.

This matters if page content that has *already been through* `url_for` is
re-rendered — website-editor-saved DOM is the realistic case. Not changed here
because canonical-URL generation depends on the first step. Measured: 16
non-idempotent shapes, all `/<default-lang>/…`.

## 3. Id `0` had to be rejected in the converter, not later

`_check_access` does `browse(id_ for id_ in self._ids if id_)` — a **falsy id is
filtered out**, so `/<model>/0` got neither `MissingError` nor `AccessError`, and
then died in `_pre_dispatch` where `_slug` refuses to *produce* a 0-id slug:
an unauthenticated **500** on every frontend `<model(…)>` route, reachable by any
crawler. The grammar accepts more spellings than the obvious one — `-0`, `00`,
`my-post-0`: 61 of 2085 short segments fuzz to id 0.

`ValidationError` is werkzeug's "this rule does not match", so the URL falls
through to the remaining rules and then to a clean 404.
→ `TestModelConverter.test_id_zero_does_not_match`

**Scope note:** `_get_converters` is registry-wide, so this also applies to the
handful of non-`website` routes using `<model(…)>`. For an anonymous caller those
went `303` (login redirect) → `404`, because the converter now rejects before
authentication.

## 4. A missing record often 404s *only* because of the slug rebuild

`check_access` runs the `ir.access` domain against the id without ever checking that it
exists. On a model with no record rules, nothing detects a missing record —
except `_pre_dispatch`'s canonical-URL rebuild, which reads `display_name` and
raises `MissingError`.

Verified by ablation: disable that block and `/<model>/99999` answers **200** for
a rule-free model, while `/shop/999999` and `/blog/999999` still 404.

So the `except` around `rule.build` **must not** catch `MissingError` /
`AccessError`. A blanket `except Exception` there serves a 200 for a record that
does not exist.
→ `TestModelConverter.test_canonical_redirect_still_reports_a_vanished_record`

## 5. `rule.build()` returns a bare `None`, not `(_, None)`

So `_, path = rule.build(args)` raises `TypeError` before any `if path is None`
check can run. And the errors that actually occur — `ValueError` from `_slug` or
from `<any(…)>` — are not werkzeug `ValidationError`, so werkzeug never swallows
them into that `None` either. Both facts have to hold at once for the guard to
be right.
→ `TestModelConverter.test_canonical_redirect_survives_an_unbuildable_url`

## 6. `_slug` on a multi-record set used to link to the wrong page

`BaseModel.id` answers `_ids[0]`, so slugging a recordset silently produced a URL
for whichever record came first. `website`'s override reads `seo_name` and *does*
raise `Expected singleton` — the same mistake was loud or silent depending on
which addons were installed. Now `check_singleton()` on both.
→ `TestSlug.test_slug_rejects_a_multi_record_set`

## 7. Emitting a trailing slash costs the visitor a redirect

Every slashed frontend URL 301s to its bare form. `_url_lang` normalizes the path
once, before the branches, so all four spellings of a link agree; only the
"insert a prefix" branch used to, which gave one link three different answers.
→ `TestUrlLang.test_trailing_slash_dropped_by_every_branch`

`/` is the homepage, not `""` with a stray slash — normalizing it away emits an
empty href, which resolves against the current page.
→ `TestUrlLang.test_root_is_not_mistaken_for_a_trailing_slash`

## 8. `MockRequest` must stay faithful, or assertions test the mock

`Mock` autovivifies any attribute, so a missing one does not fail — it silently
takes a branch. Four found this way:

| Attribute | What the mock did instead |
|---|---|
| `httprequest.method` | a truthy object equal to nothing → every `_REDIRECTABLE_METHODS` branch took its "unsafe method" side |
| `httprequest.args` | a plain `list` → `keep_query().getlist()` and `redirect_query` were never exercised |
| `httprequest.user_agent` | a `Mock` → `is_a_bot()` raises `TypeError`, so ladder case /3 was unreachable from a unit test |
| `redirect` | bound to the *model* method `ir.http._redirect`, which takes no `local=` — it could not be called the way production calls it |

When adding an attribute to `MockRequest`, prefer binding the real
`odoo.http.Request` method (`prepare_response`, `redirect`, `redirect_query` are
self-contained) over inventing a stub.

## 9. `_url_localized` must never re-enter `ir.http._match`

`_match` is the dispatch entry point: it stamps `is_frontend`/`lang`, and case /9
calls `request.reroute()` — on the request being served. A URL-*generation*
helper that goes through it steers the live request. It matches the routing map
directly instead.
→ `TestUrlLocalized.test_does_not_steer_the_live_request`

## 10. Log-flood shapes

`_is_multilang_url` swallows any routing-probe failure with a `warning(...,
exc_info=True)`. It runs **once per generated link**, so a broken routing map
means one full traceback per href on the page. Left as-is (the condition is
genuinely exceptional and diagnosability wins), but it is the reason
`_pre_dispatch`'s equivalent guard logs a one-line message with the exception
instead of a traceback.
