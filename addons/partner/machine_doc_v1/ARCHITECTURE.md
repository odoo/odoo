# `partner` — architecture

`partner` is the Contacts **application shell**. It is the module named for the record it
fronts (`res.partner`), and it decides three things: which views the address book offers,
which menus exist, and how contacts are classified into birth-year cohorts.

It does **not** own the address book. `res.partner` — the model, its fields, its form, list,
kanban and search views — is declared in `base`. Read that first when changing behaviour;
change `partner` only when changing what the *application* exposes.

| Concern | Lives in |
|---|---|
| `res.partner` model and views | `base` (`models/res_partner.py`, `views/res_partner_views.xml`) |
| Which views the Contacts app offers | this module, `views/res_partner_views.xml` |
| The Private Information page on the contact form | this module, `views/res_partner_views.xml` |
| The Contacts menu tree | this module, `views/ir_ui_menu_views.xml` |
| Birth-year cohorts | this module, `models/res_partner_age_range.py` |
| Birthday filters and the birthday index | this module, `models/res_partner.py` and `views/res_partner_views.xml` |
| Phone-number search | `phone_validation` (it owns `phone_mobile_search`) |
| Map view of contacts | `partner_enterprise` (enterprise checkout) |

## What this module adds to `res.partner`

Two fields, an index and a redeclaration, all in `models/res_partner.py`:

- `age` — non-stored, recomputed on read from `birthdate`, so it never goes stale. Not
  stored is not the same as not queryable: `_search_age` maps a comparison onto `birthdate`,
  so `[('age', '>', 18)]` is answerable in SQL. The mapping **inverts**, because an older
  contact was born earlier, and the strict forms shift a year — "older than 30" is "has
  completed 31". A contact with no birthdate has no age and so matches no comparison,
  negation included; NULL semantics give that for free. It declares `aggregator=None`, which is neither the
  Integer default (`sum`, meaningless for ages) nor the meaningful operation (`avg`):
  the web client asks the server for `<field>:<aggregator>` for every aggregatable field
  a view holds, and this one is not stored, so any answer but None turns a grouped list
  containing it into a 500.
- `age_range_id` — **stored**, and keyed on the birth *year*, not on the age. That is the
  reason it can be stored at all: a cohort membership does not change as time passes, where a
  stored `age` would silently rot. It is the group-by the search view offers, and it carries
  a `btree_not_null` index: most contacts carry no cohort, so a partial index is the shape
  that group-by actually needs. It carries `group_expand="_read_group_expand_full"`, so a
  cohort with no members is still drawn as an empty column rather than vanishing from the
  one view built to show the distribution. The framework gates that on the
  `read_group_expand` context key, which `web/static/src/model/relational_model` sets on
  every grouped view — so it fires in the client and **not** in a bare
  `formatted_read_group`.

`birthdate` is redeclared, adding nothing but `index="btree_not_null"`. `base` owns the
field; this module is what makes it *queryable*, through `age`, through the cohort sweep and
through the birthday filters, so the index belongs with the queries rather than with the
declaration.

### Birthdays

`birthdate.month_number` and `birthdate.day_of_month` are resolved by the ORM into
`date_part()` in SQL (`odoo/orm/fields/temporal.py`, `READ_GROUP_NUMBER_GRANULARITY`), so
*Birthday Today*, *Birthday This Month* and the *Birthday Month* group-by are three search
view entries and **no new field**: nothing stored, nothing to recompute, nothing that can go
stale. `date_part()` is not a column, so no index on `birthdate` can serve them; the model
declares `_birthday`, a partial expression index over `(month, day)`, for that.

The view validator used to refuse these paths, reading `birthdate.month_number` as a hop to
a comodel — while `formatted_read_group` was already handing the client that same shape back
as `__extra_domain`. Fixed in `odoo/addons/base/models/ir_ui_view.py`
(`_check_field_paths`), pinned by `test_domain_date_part_is_a_property_not_a_hop`.

Plus one override, `_get_backend_root_menu_ids`, so a `res.partner` record opened from a
notification lands under the Contacts app rather than under Settings.

## Where a birthdate is entered

`birthdate` is `base`'s field, and until this module offered a **Private Information** page
no view in this repository showed it. The classifier, the stored cohort, the group-by, the
configuration menu, the ACL and the demo cohorts all stood behind an input the user could
not reach; the only door in the workspace was `agromarin/marin`, a customer module.

The page hangs before Notes on `base.view_partner_form`, is `invisible="is_company"` and is
gated on `base.group_partner_manager` — personal data, and that is the group this app
already trusts with contact records. `age` and `age_range_id` sit beside it,
`invisible="not birthdate"`: `age` is an Integer, so with no birthdate it would read `0`
rather than empty.

`gender` is on the page for the same reason `birthdate` is: `base` declares both, one
beside the other, and neither had a placement. It had two — `agromarin/marin` and
`partner_relationship` each xpath'd their own copy onto the form, so a database
carrying both rendered the field twice. **Placing a `base` field is this module's job**, and
that is what stops a third module adding a third copy; both siblings now drop theirs and
read the value where they need it.

## `res.partner.age.range`

A cohort of birth years, built on the `mixin.band` abstract model in `base`, which supplies
`min_value` / `max_value` / `active` and the overlap and ordering constraints.

- Bounds are **years**, half-open: `[min_value, max_value)`. `max_value = 0` means no upper
  limit, which the newest cohort should use so a newborn still classifies.
- The oldest cohort stays closed on its lower side, so a birth year before it belongs to no
  cohort rather than to the oldest one.
- Editing a cohort's bounds re-triggers classification for every affected contact through
  `_add_partners_to_compute`, so the stored `age_range_id` cannot drift out of step with the
  cohorts that produced it. That sweep runs `active_test=False`: an archived contact still
  carries a stored cohort, and skipping it leaves a classification no bound supports.
- A new cohort defaults its `min_value` to the highest **closed** upper bound on the scale.
  Chaining onto the newest cohort instead is wrong on exactly the scales that are built
  correctly: that cohort is the one meant to stay open-ended, its `max_value` is `0` meaning
  *no upper limit*, and `0` as a lower bound means *no lower limit* — the opposite reading.
- `mixin.band._check_band` rejects overlapping active bands. Seeding a second set of cohorts
  on top of the demo ones therefore raises rather than silently double-classifying.
- **It says nothing about the space *between* two bands.** A scale can therefore be
  internally valid and still drop a decade, and a contact born in that decade classifies
  into nothing with no sign anywhere. `gap_before` computes the uncovered years below each
  cohort and the list view decorates them; nothing below the *oldest* cohort counts, because
  that is the intended open edge rather than a hole.
- `partner_count` answers the other question a scale raises -- is this cohort reaching
  anyone -- and `action_open_partners` opens the contacts behind the number.
- `display_name` names the years the cohort actually contains: `Generation X (1965-1980)`
  for `min_value` 1965 / `max_value` 1981. The bounds are half-open and that is this
  module's oldest trap, so the record answers the question it raises.

Configuration lives at **Contacts > Configuration > Age Ranges**
(`res_partner_age_range_menu` -> `res_partner_age_range_action`), with
`res_partner_age_range_view_tree`, `res_partner_age_range_view_form` and
`res_partner_age_range_view_search`. Demo cohorts ship in
`demo/res_partner_age_range_demo.xml`.

## The action

`action_partner` opens `res.partner` at path `contacts` with
`view_mode` `list,kanban,form,activity`, the search view
`base.view_res_partner_filter` and context `{'default_is_company': True}` — new contacts
default to being a company. Each mode is pinned by its own `ir.actions.act_window.view`
record (`action_partner_view_tree`, `action_partner_view_kanban`,
`action_partner_view_form`) rather than relying on `view_mode` ordering alone.

`view_mode` is not the whole list of modes the app offers: `_compute_views` starts from the
`act_window.view` records and only then appends modes named in `view_mode` that none of them
covers. That is how `partner_enterprise` adds a map view without editing this module.

## Menu tree

```
partner_menu_root                        Contacts (the app)
├── res_partner_menu                     Contacts        -> action_partner       seq 10
└── res_partner_menu_config              Configuration   (base.group_partner_manager)  seq 100
    ├── menu_partner_tag_form       Contact Tags
    ├── res_partner_age_range_menu       Age Ranges      -> res_partner_age_range_action
    ├── res_partner_identifier_type_menu Identifier Types    (base.group_system)
    ├── res_partner_industry_menu        Industries          (base.group_system)
    ├── menu_localisation                Localization
    │   ├── menu_country_partner         Countries
    │   ├── menu_country_state_partner   States
    │   └── menu_country_group           Country Group
    └── menu_config_bank_accounts        Bank Accounts
        ├── menu_action_res_bank_form    Banks
        └── menu_action_res_partner_bank_form   Bank Accounts
```

**The branch is gated on the group the ACL empowers, not on the administrator.**
`security/ir.access.csv` grants `base.group_partner_manager` create/write/unlink on
the cohorts, and `base`'s own ACL grants that same group write on tags, states, country
groups and banks. While Configuration was `base.group_system` every one of those rights
reached no screen. The two entries a manager may only *read* — Industries and Identifier
Types, both `group_system`-write in `base` — carry the narrower group themselves, so
widening the parent did not hand out screens the ACL still refuses to save. The two sibling
sequences were both `2`, which left their order to `ir.ui.menu._order`'s `id` tiebreak.

Everything under Configuration except Age Ranges points at an action `base` declares; this
module contributes the placement, not the screens. Identifier Types is one of those: the
identifier kernel (`res.partner.identifier.type` and `res.partner.identifier`) lives in `base`
beside `vat`, and `partner` only gives it a way in.
