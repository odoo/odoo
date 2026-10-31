# Review of the equipment_booking PR (answer key)

Every seeded issue, by area. Generated from the task's issue catalogue.

## Module structure and file naming

- `addons/equipment_booking/models/booking.py`, line 227: models/booking.py holds two models, equipment.booking and equipment.booking.lines, and is not named after its model: one model per file, named after the model (equipment_booking.py, and a separate file for the lines). Flagging either half (two models in one file, or the file name) passes.
- `addons/equipment_booking/views/booking.xml`: The backend views file views/booking.xml lacks the _views suffix (equipment_booking_views.xml).
- `addons/equipment_booking/views/portal.xml`: The portal QWeb pages are in views/portal.xml instead of a *_templates.xml file (equipment_booking_portal_templates.xml or similar).
- `addons/equipment_booking/security/groups.xml`: The group is declared in security/groups.xml instead of security/equipment_booking_security.xml.
- `addons/equipment_booking/controllers/booking_portal.py`, line 14: The controller extending portal's CustomerPortal is controllers/booking_portal.py; a controller extending another module's controller is named after that module (controllers/portal.py).
- `addons/equipment_booking/report/booking_report.xml`, line 13: report/booking_report.xml holds both the report action and the QWeb template; a printable report splits the action (*_reports.xml) from the template (*_templates.xml).
- `addons/equipment_booking/data/mail-templates.xml`: data/mail-templates.xml has a hyphen in its name; file names are lowercase Python identifiers ([a-z0-9_]), and a data file takes the _data suffix (mail_template_data.xml).
- `addons/equipment_booking/wizard/wizard.py`, line 6: The wizard equipment.booking.extend is in wizard/wizard.py and wizard/wizard_views.xml; wizard files are named after the transient model (equipment_booking_extend.py, equipment_booking_extend_views.xml).

## Manifest

- `addons/equipment_booking/__manifest__.py`, line 12: The manifest's depends lists 'base', which is implied and should not be listed.
- `addons/equipment_booking/__manifest__.py`, line 12: depends lists 'sale', which the module never uses, while it uses product.product (the accessory lines, the wizard) without depending on 'product' directly. Flagging either half passes.
- `addons/equipment_booking/__manifest__.py`, line 22: demo/equipment_booking_demo.xml is listed under 'data', so its demo records (a projector, a location, a booking) are loaded on every database, production included; it belongs under 'demo'.
- `addons/equipment_booking/__manifest__.py`, line 2: The manifest sets no 'license' (it falls back to LGPL-3 with a warning); set it deliberately.
- `addons/equipment_booking/__manifest__.py`, line 29: auto_install is True on a feature module: it installs itself on every database with maintenance, portal and sale. auto_install is for link (bridge) modules only.
- `addons/equipment_booking/report/booking_report.py`, line 6: report/booking_report.py imports the third-party phonenumbers library, which the manifest does not declare in external_dependencies (python).

## Imports, naming and model layout, translations

- `addons/equipment_booking/models/booking.py`, line 6: The imports of models/booking.py are out of order: the odoo imports come before the stdlib ones (datetime, logging), and the third-party markupsafe comes last; the order is stdlib, third-party, odoo, odoo.addons, each sorted.
- `addons/equipment_booking/models/booking.py`, line 228: The model name equipment.booking.lines is plural; model names are singular (equipment.booking.line), and so is the class name.
- `addons/equipment_booking/models/res_partner.py`, line 35: In res.partner._get_upcoming_bookings, booking_obj holds a model; a variable holding a model is PascalCase (Booking).
- `addons/equipment_booking/controllers/booking_portal.py`, line 37: In portal_my_bookings, partner_id holds a res.partner record, not an id; the _id suffix is for ids (name it partner).
- `addons/equipment_booking/models/booking.py`, line 66: The compute method of duration is named _get_duration instead of _compute_duration.
- `addons/equipment_booking/models/booking.py`, line 93: The @api.constrains method is named _validate_no_overlap instead of _check_<name> (_check_no_overlap).
- `addons/equipment_booking/models/booking.py`, line 151: action_open_equipment reads self.equipment.id without self.ensure_one(); an action_* method acts on one record and starts with ensure_one().
- `addons/equipment_booking/models/equipment_booking_location.py`, line 14: In equipment.booking.location, the create override sits above the field declarations; the model body order is private attributes, fields, constraints, computes, ..., CRUD overrides, actions.
- `addons/equipment_booking/models/booking.py`, line 108: In _validate_no_overlap, the message is %-formatted inside self.env._("Booking %s overlaps ..." % booking.name), so the formatted string matches no exported term and is never translated; pass the value as an argument of _().
- `addons/equipment_booking/models/booking.py`, line 145: In action_cancel, the message is formatted after the lookup: self.env._("... %s ...") % booking.name; pass the value as an argument of _() so placeholders are validated per translation.
- `addons/equipment_booking/models/booking.py`, line 189: In _check_missing_accessories, the names are joined by hand (", ".join) before being passed to _(); pass the list itself, which _() formats per language.
- `addons/equipment_booking/models/booking.py`, line 12: DEFAULT_BOOKING_NAME = _("New Booking") calls _() at module level, at import time with no language: it is never translated (use LazyTranslate, or translate inside the method).
- `addons/equipment_booking/models/booking.py`, line 224: _get_late_labels uses the bare _ inside a list comprehension, where it cannot find the environment and returns the untranslated string; use self.env._.

## Plain ASCII punctuation

- `addons/equipment_booking/models/booking.py`, line 205: The comment in _cron_send_reminders uses an em dash (—); comments use ASCII punctuation.
- `addons/equipment_booking/models/booking.py`, line 167: The UserError in checkin uses curly quotes (“confirmed”) in a user-facing string; use ASCII quotes.
- `addons/equipment_booking/models/booking.py`, line 50: The help of the note field ends with the ellipsis character (…); write three dots.

## Recordsets, computes, methods, transactions

- `addons/equipment_booking/models/booking.py`, line 136: action_return builds equipment_ids with a for loop and append where self.equipment (or mapped) reads better.
- `addons/equipment_booking/models/booking.py`, line 212: _cron_send_reminders tests if len(bookings) > 0: instead of if bookings:.
- `addons/equipment_booking/models/booking.py`, line 192: _send_reminder reads self.partner_id.email on the whole recordset, while _cron_send_reminders calls it on every due booking: with bookings of two holders it raises 'Expected singleton', and the email check is not per booking. Iterate, or check per record.
- `addons/equipment_booking/models/booking.py`, line 217: _cron_archive_past_bookings hand-builds a '|' prefix-notation domain; combine domains with odoo.fields.Domain (Domain(...) | Domain(...)).
- `addons/equipment_booking/wizard/wizard.py`, line 19: The custom context key skip_overlap_check (set by the extend wizard, read by _validate_no_overlap) is not prefixed by the module; module-specific context keys are prefixed (equipment_booking_...) so they do not leak or collide. Flagging the key itself passes; flagging only that the wizard can bypass the overlap check does not.
- `addons/equipment_booking/models/equipment_booking_location.py`, line 10: equipment.booking.location uses delegation inheritance (_inherits res.partner); it inherits fields but not methods and should be avoided where a plain Many2one to the address does the job.
- `addons/equipment_booking/models/booking.py`, line 237: equipment.booking.lines overrides create(self, vals) with @api.model and a single vals; create takes a list of values with @api.model_create_multi (create(self, vals_list)).
- `addons/equipment_booking/models/booking.py`, line 79: _compute_is_late reads state but @api.depends lists only end_datetime; every field read must be listed.
- `addons/equipment_booking/models/booking.py`, line 90: The stored compute _compute_return_datetime posts a chatter message (and reads the clock): a stored compute must have no side effects; it can run again on recompute, and posting belongs in action_return.
- `addons/equipment_booking/models/booking.py`, line 111: That the end comes after the start is only enforced in _onchange_dates: RPC, the portal route, imports and the wizard can still store a booking ending before it starts. Enforce it with @api.constrains or a models.Constraint.
- `addons/equipment_booking/models/equipment_booking_location.py`, line 28: equipment.booking.location declares _sql_constraints, which master ignores (with a warning): the unique constraint is never created; use models.Constraint.
- `addons/equipment_booking/models/booking.py`, line 173: compute_price_for_period is a public method nothing calls from outside: it is exposed over RPC for no reason; make it private (_compute_price_for_period). (Reporting it only as unused code does not pass.)
- `addons/equipment_booking/models/booking.py`, line 178: _get_reminder_delay returns a constant, has one caller and no override: an extension point split off before anyone needs it.
- `addons/equipment_booking/models/booking.py`, line 161: action_share_link uses odoo.http.request in a model method; request is absent in crons, RPC, tests and the shell. Use self.get_base_url() (or pass the value in from the controller).
- `addons/equipment_booking/models/booking.py`, line 220: _cron_archive_past_bookings calls self.env.cr.commit() in its loop, with no comment justifying it; the framework owns the transaction.
- `addons/equipment_booking/models/booking.py`, line 200: _send_reminder wraps the whole send in except Exception: pass, which silently swallows every error (template missing, mail failure, code bugs); catch specific exceptions over the smallest block, and log them.

## Fields

- `addons/equipment_booking/models/booking.py`, line 22: The Many2one equipment lacks the _id suffix (equipment_id).
- `addons/equipment_booking/models/booking.py`, line 39: The One2many lines lacks the _ids suffix (line_ids).
- `addons/equipment_booking/models/booking.py`, line 44: reminder_sent is a boolean with index=True: an index on a low-cardinality field is wasted space and slows every write.
- `addons/equipment_booking/models/booking.py`, line 41: price is an amount stored as a plain Float, with no currency; an amount is a Monetary field with its currency companion (currency_id).
- `addons/equipment_booking/models/booking.py`, line 25: The holder partner_id has ondelete='cascade': deleting (or merging away) a partner silently deletes their bookings and their history; restrict (or set null) is the sensible choice.
- `addons/equipment_booking/models/booking.py`, line 43: is_archived is a custom archiving boolean; the reserved active field gives archiving for free (action_archive, the default filter) instead of the action's hand-written domain.
- `addons/equipment_booking/models/equipment_booking_location.py`, line 20: The location tree has parent_id but no _parent_store and parent_path (indexed), while _get_bookings_in_subtree searches with child_of.
- `addons/equipment_booking/models/booking.py`, line 26: equipment.booking has a company_id but no company consistency: no _check_company_auto and no check_company on equipment and location_id, so a booking can link records of another company.
- `addons/equipment_booking/models/booking.py`, line 164: The field checkin and the method checkin() share a name: the method, defined later in the class, replaces the field, which silently disappears from the model.
- `addons/equipment_booking/models/booking.py`, line 40: accessory_name is related through the One2many lines (lines.product_id.name): the ORM silently keeps the first line only.
- `addons/equipment_booking/models/booking.py`, line 30: start_date and end_date share one inverse, _inverse_dates: while it runs, both fields are protected and the sibling reads wrong values. Give each field its own inverse.
- `addons/equipment_booking/models/maintenance_equipment.py`, line 16: checkin_code is a selective code that /booking/checkin searches on, without an index.

## Controllers

- `addons/equipment_booking/controllers/booking_portal.py`, line 24: BookingPortal.home overrides the portal /my route without re-decorating it with @route() (the framework auto-decorates it with a warning).
- `addons/equipment_booking/controllers/booking_portal.py`, line 89: /booking/availability uses type='json', a deprecated alias; use type='jsonrpc'.

## Views, actions, data records, view inheritance

- `addons/equipment_booking/views/booking.xml`, line 4: The form view record is written <record model=... id=...>: id comes before model.
- `addons/equipment_booking/views/booking.xml`: views/booking.xml interleaves records of different models (views, actions, views again, the equipment view, menus) instead of grouping them by model.
- `addons/equipment_booking/views/booking.xml`, line 201: The menu equipment_booking_menu is a raw <record model="ir.ui.menu"> instead of a <menuitem>.
- `addons/equipment_booking/data/mail-templates.xml`, line 3: data/mail-templates.xml wraps its whole content in <data noupdate="1">; for a fully noupdate file, set noupdate="1" on <odoo> and drop <data>.
- `addons/equipment_booking/views/booking.xml`, line 74: The list view's xml id view_booking_list does not follow <model>_view_<type> (equipment_booking_view_list).
- `addons/equipment_booking/views/booking.xml`, line 64: The action's xml id action_bookings does not follow <model>_action (equipment_booking_action).
- `addons/equipment_booking/security/groups.xml`, line 3: The group's xml id group_booking_manager does not follow <module>_group_<name> (equipment_booking_group_manager).
- `addons/equipment_booking/views/portal.xml`, line 25: The portal template's CSS class o_booking_status is not prefixed by the module (o_equipment_booking_...); o_ alone is reserved for the web client.
- `addons/equipment_booking/views/booking.xml`, line 172: The equipment form extension anchors on position (//sheet/group/group[2]/field[2]) instead of a name (<field name="technician_user_id" position="after">); it breaks or lands elsewhere when maintenance or another module changes the form.
- `addons/equipment_booking/views/booking.xml`, line 168: The inheriting view's name maintenance.equipment.form.booking lacks the .inherit. suffix (maintenance.equipment.form.inherit.equipment_booking).
- `addons/equipment_booking/views/booking.xml`, line 179: The equipment form extension adds serial_number again in its Bookings page, while the parent form already shows it.
- `addons/equipment_booking/views/booking.xml`, line 108: equipment_booking_view_form_quick is meant as a variant of the booking form (the Quick Booking action) but inherits it without mode="primary": it extends the main form, hiding the Accessories page for everyone.

## QWeb PDF reports

- `addons/equipment_booking/report/booking_report.py`, line 17: _get_report_values returns no docs (nor doc_ids, doc_model) while the template loops over docs; a custom _get_report_values must add them itself.
- `addons/equipment_booking/report/booking_report.xml`, line 17: t-lang is set on a <div>, not on a node carrying t-call: QWeb raises a SyntaxError when the report is rendered. Move the translated part into its own template called with t-call and t-lang.
- `addons/equipment_booking/report/booking_report.py`, line 20: The report re-browses every booking in the holder's language (localized) while the template reads no translatable field from it (name, dates): a needless cost.

## Access rights

- `addons/equipment_booking/security/ir.access.csv`: The extend wizard equipment.booking.extend has no ir.access row: with default deny, users other than the superuser cannot use it.
- `addons/equipment_booking/security/ir.access.csv`, line 4: base.group_portal is granted crud on equipment.booking, with no domain: every portal user can read, create, edit and delete every booking through RPC.
- `addons/equipment_booking/security/ir.access.csv`: equipment.booking has a company_id but no group-less company restriction row ([('company_id', 'in', company_ids)]).
- `addons/equipment_booking/security/ir.access.csv`, line 6: The restriction row on equipment.booking.lines covers only r, while base.group_user is granted crud: a user can still write and delete lines of other users' bookings they cannot read (and the read restriction applies to managers too). Cover every operation that needs restricting.

## Performance

- `addons/equipment_booking/models/res_partner.py`, line 20: _compute_booking_count runs one search_count per partner; use one _read_group over all partners.
- `addons/equipment_booking/wizard/wizard.py`, line 22: action_extend creates one accessory line per product in a loop; build the vals list and create once.
- `addons/equipment_booking/models/res_partner.py`, line 46: _get_equipment_in_use browses the equipment one id at a time, defeating prefetch; browse(equipment_ids) once.
- `addons/equipment_booking/models/res_partner.py`, line 36: _get_upcoming_bookings filters state in Python after the search; put the condition in the domain.
- `addons/equipment_booking/models/booking.py`, line 101: _validate_no_overlap loads every non-cancelled booking of the equipment, history included, and compares each checked booking with all of them in a nested loop; restrict the search to overlapping periods (or group by equipment) instead of an O(n*m) scan.

## Tests

- `addons/equipment_booking/tests/test_portal.py`: tests/test_portal.py is not imported in tests/__init__.py, so its test never runs.
- `addons/equipment_booking/tests/booking_tests.py`: tests/booking_tests.py is not named test_*.py, so it is skipped although __init__.py imports it.
- `addons/equipment_booking/tests/test_booking.py`, line 11: TestEquipmentBooking is tagged both post_install and at_install, so it runs twice; set exactly one.
- `addons/equipment_booking/tests/booking_tests.py`, line 6: TestBookingLocation opts into at_install with no comment justifying it.
- `addons/equipment_booking/tests/test_booking.py`, line 38: test_price wraps business assertions in assertQueryCount(60), a loose budget in a business test; query counts belong in dedicated performance tests, with exact budgets.
- `addons/equipment_booking/tests/test_booking.py`, line 43: test_reminder_without_email triggers the expected 'holder has no email' warning without mute_logger, so it reaches the runbot log.
- `addons/equipment_booking/tests/test_booking.py`, line 61: TestEquipmentBookingManager defines no test of its own; inherited test_* methods are not collected without allow_inherited_tests_method = True, so the manager variant runs nothing.
- `addons/equipment_booking/tests/test_booking.py`, line 17: The tests rely on the demo partner base.res_partner_2 from a plain TransactionCase; demo data is not guaranteed. Create the records (or start from BaseCommon).
- `addons/equipment_booking/tests/test_booking.py`, line 52: test_reminder_sent patches the private _send_reminder and asserts it is called, testing implementation rather than behavior (a mail queued, reminder_sent set).

## JavaScript: file layout, getters, patching

- `addons/equipment_booking/static/src/components/booking_board.js`: static/src/ is organized by type (components/, hooks/, patches/, scss/, vendor/), so the booking board's component, template, hook and styles are spread over type folders. Code is organized by feature: one folder for the board holding all its files (static/src/booking_board/).
- `addons/equipment_booking/static/src/components/booking_board.js`, line 21: BookingBoard.title is a getter: it hides that code runs and only saves a pair of parentheses. Use a plain method (or a plain value).
- `addons/equipment_booking/static/src/components/booking_board.js`, line 25: BookingBoard.lateCount is a getter computing derived state (the late bookings among the loaded ones), re-run on every read. Use an Owl computed, which recomputes only when the bookings change, or at least a plain method.
- `addons/equipment_booking/static/src/patches/form_controller_patch.js`, line 5: The module patches FormController.prototype.onRecordSaved, which runs for every form view, to notify after saving a booking. Patching is strongly discouraged inside Odoo: use an extension point, such as a booking form view with a js_class whose controller extends FormController.

## SCSS formatting, class and variable naming

- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 3: The SCSS variable $bookingCardColor does not follow $o-[root]-[element]-[property]-[modifier] (e.g. $o-equipment-booking-card-color): camelCase, no o- prefix.
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 5: The mixin cardShadow is not named o-[imperative verb] (e.g. o-add-card-shadow), and its argument $size is not in scoped form ($-size). Flagging either half passes.
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 9: The CSS variable --booking-accent is defined on :root. CSS variables are for contextual DOM adaptation, not global design: use an SCSS variable, or define it on the board's own element.
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 13: #booking_board_header is an id selector; avoid id selectors, use a class (o_equipment_booking_board_header).
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 18: The CSS variable --columnGap does not follow the BEM convention --[root]__[element]-[property]--[modifier] (e.g. --BookingBoard__column-gap).
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 28: The properties of .o_equipment_booking_board_column are not ordered from the outside in: color and font-size come first, width and position last. Start with position, then layout and box (width, padding), and end with decorative ones (color, font).
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 38: o_equipment_booking_board_column_card_header_title is a hyper-specific class name that spells out the DOM nesting; use the flat grandchild approach (o_equipment_booking_board_title).
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 42: The class o-booking-card uses hyphens (and drops the module name): classes use underscores and the o_<module> prefix (o_equipment_booking_board_card); hyphens are for SCSS variables, mixins and functions.
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 51: The class booking_late has no o_<module> prefix (o_equipment_booking_board_late).
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 58: The scoped variable $-badge-radius is declared mid-rule, after declarations; scoped SCSS and CSS variables go at the top of the rule, separated by a blank line.
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 62: The rule .o_equipment_booking_board_note is written on one line with three declarations: one declaration per line, closing brace on its own line.
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 64: The rule .o_equipment_booking_board_empty is indented with tabs; SCSS is indented with 4 spaces.

## Assets: resources shipped in the codebase, libraries

- `addons/equipment_booking/static/src/components/booking_board.xml`, line 6: The board's header icon is loaded from a CDN (cdn.jsdelivr.net). Every resource a page needs ships in the codebase: copy the image into the addon (or use the icon font).
- `addons/equipment_booking/static/src/scss/booking_board.scss`, line 1: booking_board.scss imports the Inter font from Google Fonts by URL. Fonts ship in the codebase (or use the webclient's fonts).
- `addons/equipment_booking/static/src/vendor/reltime.min.js`: The third-party reltime library is vendored minified (reltime.min.js) in static/src/vendor/. Third-party libraries go in static/lib/, unminified, so they can be read and diffed.

## Security

- `addons/equipment_booking/controllers/booking_portal.py`, line 100: /booking/calendar/<id> is auth='public' and searches bookings with sudo: anonymous visitors see holder names and booking notes of any equipment.
- `addons/equipment_booking/controllers/booking_portal.py`, line 95: /booking/availability interpolates the request parameter day into the SQL with an f-string: SQL injection. Pass it as a query parameter.
- `addons/equipment_booking/models/res_partner.py`, line 39: _get_equipment_in_use reads equipment_booking with raw SQL where an ORM search does it, bypassing access rules and the ORM (flush, active).
- `addons/equipment_booking/controllers/booking_portal.py`, line 40: portal_my_bookings prepends the request's filter_domain to the ownership domain and searches with sudo: a filter starting with '|' turns it into 'anything or mine', exposing every booking. Combine with Domain (AND) and validate the user domain.
- `addons/equipment_booking/models/booking.py`, line 170: set_booking_state is public, so callable over RPC on any ids, and writes the given state with sudo: any user can set any booking to any state.
- `addons/equipment_booking/controllers/booking_portal.py`, line 73: /my/bookings/<id>/cancel cancels a booking on a GET request: a link or an image tag on another site cancels the victim's booking (CSRF). Use POST with the CSRF token.
- `addons/equipment_booking/controllers/booking_portal.py`, line 67: /my/bookings/<id>/update is an http POST route with csrf=False: any site can submit it as the logged-in user.
- `addons/equipment_booking/views/portal.xml`, line 40: The portal booking page's update form posts without the csrf_token hidden input (the reason the route disables CSRF).
- `addons/equipment_booking/models/booking.py`, line 149: action_cancel builds Markup(f"<p>Cancelled: {reason}</p>"): the f-string defeats escaping, so the reason is posted to the chatter as raw HTML (XSS). Use Markup("<p>Cancelled: %s</p>") % reason, or .format.
- `addons/equipment_booking/report/booking_report.xml`, line 22: The report uses t-esc, which server QWeb ignores (it renders nothing), so the holder's phone never shows; use t-out.
- `addons/equipment_booking/models/res_partner.py`, line 15: res.partner.booking_feed_token is a secret (it authenticates the calendar feed) with no groups: any internal user can read every partner's token with search_read. Restrict it (base.group_system or fields.NO_ACCESS).
- `addons/equipment_booking/models/booking.py`, line 47: feed_token is a related field (computed with sudo by default) reaching the partner's feed token through the user-writable partner_id: point a booking at any partner and read their token. Set related_sudo=False or drop the field.
- `addons/equipment_booking/models/booking.py`, line 49: manual_file is a sudo-computed related field onto ir.attachment through the user-writable manual_attachment_id: set it to any attachment id and read any file. Use a plain Binary or the attachment's own access checks.
- `addons/equipment_booking/controllers/booking_portal.py`, line 70: portal_booking_update writes the raw request parameters with sudo (booking_sudo.write(post)): the holder can set any field (state, partner_id, price, company_id, line commands). Whitelist the keys (note).
- `addons/equipment_booking/controllers/booking_portal.py`, line 59: portal_booking_create switches to with_user(int(post['user_id'])): the request picks the user the booking is created as, any user included.
- `addons/equipment_booking/report/booking_report.py`, line 38: _get_equipment_picture opens a path built from the equipment's serial number with the builtin open(): a serial number like ../../.. reads arbitrary files. Use file_open, or store the picture as an attachment.
- `addons/equipment_booking/models/equipment_booking_location.py`, line 44: _accepts_booking runs safe_eval on booking_condition, which any internal user can write (cru on locations): evaluating an expression is only for trusted, privileged users.
- `addons/equipment_booking/models/res_partner.py`, line 32: _get_booking_preferences unpickles a stored field: pickle runs arbitrary code on load; store JSON.
- `addons/equipment_booking/controllers/booking_portal.py`, line 42: portal_my_bookings sorts with getattr(booking, sortby), sortby coming from the request, on sudo records: the user picks any attribute (private methods, any field). Whitelist sort keys and use record[name].
- `addons/equipment_booking/controllers/booking_portal.py`, line 114: booking_feed compares the feed token with != instead of a constant-time comparison (consteq).
- `addons/equipment_booking/models/booking.py`, line 181: _prepare_reminder_values has a mutable default (extra_values={}) that it updates: the dict is shared across calls and carries the previous booking's reply_to.
- `addons/equipment_booking/models/maintenance_equipment.py`, line 37: get_label_signer is a public method returning an hmac object keyed with database.secret: reachable from safe_eval'd code (server actions) and RPC, it lets anyone sign check-in codes or walk the object. Make it private, or a module-level function.
- `addons/equipment_booking/static/src/components/booking_board.js`, line 42: The booking board renders booking.note through markup(), which marks it as safe HTML. Portal users write the note (/my/bookings/<id>/update), so their HTML and scripts run in the backend of every user who opens the board (stored XSS). Render the note as plain text.

## Code the diff never shows

- `addons/maintenance/models/maintenance.py`, line 174: _compute_owner now calls _get_owner_methods_by_equipment_assign_to(date=...), but the overrides in hr_maintenance and fleet_maintenance take no date argument: computing the owner raises a TypeError wherever one of them is installed. Naming one of those overrides (or the existing overrides in general, found by searching for them) passes.
- `addons/maintenance/models/maintenance.py`, line 142: The rename of maintenance.equipment.serial_no to serial_number is not carried to its consumers: stock_maintenance (a @depends and a view), fleet_maintenance and hr_maintenance (views) still use serial_no and fail to install or load. Naming one of those modules passes.

## Merits pass, no guideline

- `addons/equipment_booking/models/booking.py`, line 105: The overlap check compares with <= and >=, so a booking starting exactly when another ends is rejected as overlapping; back-to-back bookings need strict comparisons.
- `addons/equipment_booking/models/booking.py`, line 206: _cron_send_reminders compares start_datetime with a date (fields.Date.today() + 1 day, midnight UTC): a booking starting tomorrow at 9:00 is not due until the next day, so the reminder comes on the day itself, not the day before; timezones are ignored as well.
- `addons/equipment_booking/models/booking.py`, line 77: _compute_price rounds with round(..., 2) instead of the currency's rounding.
- `addons/equipment_booking/tests/test_booking.py`, line 58: test_cancel asserts that state is truthy, which it always is: the test passes whether or not the booking was cancelled.
- the commit message: The commit message says cancelling a booking notifies the equipment's technician; action_cancel notifies no one (it only posts the reason on the booking).
