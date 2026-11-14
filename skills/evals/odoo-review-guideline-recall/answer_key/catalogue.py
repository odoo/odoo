"""The seeded issues of the equipment_booking PR, one entry per spot.

Each entry: (id, file, anchor, issue). The anchor is a substring of the line
the issue sits on; the generator turns it into a line number and fails when it
no longer matches. Areas map to the guideline files and skills.
"""

M = 'addons/equipment_booking/'
WEB = M + 'static/src/'
SCSS = WEB + 'scss/booking_board.scss'

AREAS = {
    'structure': ("Module structure and file naming", "odoo-guidelines guidelines/module_structure.md"),
    'manifest': ("Manifest", "odoo-guidelines guidelines/manifest.md"),
    'python': ("Imports, naming and model layout, translations", "odoo-guidelines guidelines/python.md"),
    'comments': ("Plain ASCII punctuation", "odoo-guidelines guidelines/comments.md"),
    'orm': ("Recordsets, computes, methods, transactions", "odoo-guidelines guidelines/orm.md"),
    'fields': ("Fields", "odoo-guidelines guidelines/fields.md"),
    'controllers': ("Controllers", "odoo-guidelines guidelines/controllers.md"),
    'xml': ("Views, actions, data records, view inheritance", "odoo-guidelines guidelines/xml.md"),
    'reports': ("QWeb PDF reports", "odoo-guidelines guidelines/reports.md"),
    'access': ("Access rights", "odoo-guidelines guidelines/security.md"),
    'performance': ("Performance", "odoo-guidelines guidelines/performance.md"),
    'tests': ("Tests", "odoo-guidelines guidelines/tests.md"),
    'javascript': ("JavaScript: file layout, getters, patching", "odoo-web-guidelines guidelines/javascript.md"),
    'scss': ("SCSS formatting, class and variable naming", "odoo-web-guidelines guidelines/scss.md"),
    'assets': ("Assets: resources shipped in the codebase, libraries", "odoo-web-guidelines guidelines/assets.md"),
    'security': ("Security", "odoo-security skill"),
    'consumers': ("Code the diff never shows", "odoo-review skill, Code the diff never shows"),
    'merits': ("Merits pass, no guideline", "odoo-review skill, Merits pass"),
}

ISSUES = {
    'structure': [
        ('st1_one_model_per_file', M + 'models/booking.py', 'class EquipmentBookingLines',
         "models/booking.py holds two models, equipment.booking and equipment.booking.lines, and is not named "
         "after its model: one model per file, named after the model (equipment_booking.py, and a separate file "
         "for the lines). Flagging either half (two models in one file, or the file name) passes."),
        ('st2_views_file_suffix', M + 'views/booking.xml', None,
         "The backend views file views/booking.xml lacks the _views suffix (equipment_booking_views.xml)."),
        ('st3_templates_file_suffix', M + 'views/portal.xml', None,
         "The portal QWeb pages are in views/portal.xml instead of a *_templates.xml file "
         "(equipment_booking_portal_templates.xml or similar)."),
        ('st4_security_file_name', M + 'security/groups.xml', None,
         "The group is declared in security/groups.xml instead of security/equipment_booking_security.xml."),
        ('st5_controller_file_name', M + 'controllers/booking_portal.py', 'class BookingPortal',
         "The controller extending portal's CustomerPortal is controllers/booking_portal.py; a controller extending "
         "another module's controller is named after that module (controllers/portal.py)."),
        ('st6_report_files_split', M + 'report/booking_report.xml', '<template id="report_booking_label">',
         "report/booking_report.xml holds both the report action and the QWeb template; a printable report splits "
         "the action (*_reports.xml) from the template (*_templates.xml)."),
        ('st7_file_name_identifier', M + 'data/mail-templates.xml', None,
         "data/mail-templates.xml has a hyphen in its name; file names are lowercase Python identifiers "
         "([a-z0-9_]), and a data file takes the _data suffix (mail_template_data.xml)."),
        ('st8_wizard_file_names', M + 'wizard/wizard.py', 'class EquipmentBookingExtend',
         "The wizard equipment.booking.extend is in wizard/wizard.py and wizard/wizard_views.xml; wizard files are "
         "named after the transient model (equipment_booking_extend.py, equipment_booking_extend_views.xml)."),
    ],
    'manifest': [
        ('mf1_depends_base', M + '__manifest__.py', "'depends':",
         "The manifest's depends lists 'base', which is implied and should not be listed."),
        ('mf2_direct_depends', M + '__manifest__.py', "'depends':",
         "depends lists 'sale', which the module never uses, while it uses product.product (the accessory lines, "
         "the wizard) without depending on 'product' directly. Flagging either half passes."),
        ('mf3_demo_in_data', M + '__manifest__.py', "'demo/equipment_booking_demo.xml'",
         "demo/equipment_booking_demo.xml is listed under 'data', so its demo records (a projector, a location, a "
         "booking) are loaded on every database, production included; it belongs under 'demo'."),
        ('mf4_license', M + '__manifest__.py', "'name': 'Equipment Booking'",
         "The manifest sets no 'license' (it falls back to LGPL-3 with a warning); set it deliberately."),
        ('mf5_auto_install', M + '__manifest__.py', "'auto_install': True",
         "auto_install is True on a feature module: it installs itself on every database with maintenance, portal "
         "and sale. auto_install is for link (bridge) modules only."),
        ('mf6_external_dependencies', M + 'report/booking_report.py', 'import phonenumbers',
         "report/booking_report.py imports the third-party phonenumbers library, which the manifest does not "
         "declare in external_dependencies (python)."),
    ],
    'python': [
        ('py1_import_order', M + 'models/booking.py', 'from datetime import timedelta',
         "The imports of models/booking.py are out of order: the odoo imports come before the stdlib ones "
         "(datetime, logging), and the third-party markupsafe comes last; the order is stdlib, third-party, odoo, "
         "odoo.addons, each sorted."),
        ('py2_plural_model_name', M + 'models/booking.py', "_name = 'equipment.booking.lines'",
         "The model name equipment.booking.lines is plural; model names are singular (equipment.booking.line), "
         "and so is the class name."),
        ('py3_model_variable_case', M + 'models/res_partner.py', "booking_obj = self.env['equipment.booking']",
         "In res.partner._get_upcoming_bookings, booking_obj holds a model; a variable holding a model is "
         "PascalCase (Booking)."),
        ('py4_record_named_id', M + 'controllers/booking_portal.py', 'partner_id = request.env.user.partner_id',
         "In portal_my_bookings, partner_id holds a res.partner record, not an id; the _id suffix is for ids "
         "(name it partner)."),
        ('py5_compute_method_name', M + 'models/booking.py', 'def _get_duration(self):',
         "The compute method of duration is named _get_duration instead of _compute_duration."),
        ('py6_constraint_method_name', M + 'models/booking.py', 'def _validate_no_overlap(self):',
         "The @api.constrains method is named _validate_no_overlap instead of _check_<name> (_check_no_overlap)."),
        ('py7_action_ensure_one', M + 'models/booking.py', 'def action_open_equipment(self):',
         "action_open_equipment reads self.equipment.id without self.ensure_one(); an action_* method acts on one "
         "record and starts with ensure_one()."),
        ('py8_model_body_order', M + 'models/equipment_booking_location.py', 'def create(self, vals_list):',
         "In equipment.booking.location, the create override sits above the field declarations; the model body "
         "order is private attributes, fields, constraints, computes, ..., CRUD overrides, actions."),
        ('tr1_format_before_lookup', M + 'models/booking.py', 'overlaps another booking of the same equipment" % booking.name',
         "In _validate_no_overlap, the message is %-formatted inside self.env._(\"Booking %s overlaps ...\" % "
         "booking.name), so the formatted string matches no exported term and is never translated; pass the value "
         "as an argument of _()."),
        ('tr2_format_after_lookup', M + 'models/booking.py', 'cannot be cancelled once returned") % booking.name',
         "In action_cancel, the message is formatted after the lookup: self.env._(\"... %s ...\") % booking.name; "
         "pass the value as an argument of _() so placeholders are validated per translation."),
        ('tr3_manual_join', M + 'models/booking.py', '", ".join(missing.product_id',
         "In _check_missing_accessories, the names are joined by hand (\", \".join) before being passed to _(); "
         "pass the list itself, which _() formats per language."),
        ('tr4_module_level_translation', M + 'models/booking.py', 'DEFAULT_BOOKING_NAME = _("New Booking")',
         "DEFAULT_BOOKING_NAME = _(\"New Booking\") calls _() at module level, at import time with no language: it "
         "is never translated (use LazyTranslate, or translate inside the method)."),
        ('tr5_bare_underscore', M + 'models/booking.py', 'return [_("%s (late)", booking.name)',
         "_get_late_labels uses the bare _ inside a list comprehension, where it cannot find the environment and "
         "returns the untranslated string; use self.env._."),
    ],
    'comments': [
        ('as1_em_dash_comment', M + 'models/booking.py', '# remind holders the day before',
         "The comment in _cron_send_reminders uses an em dash (—); comments use ASCII punctuation."),
        ('as2_curly_quotes_message', M + 'models/booking.py', 'Only a “confirmed” booking',
         "The UserError in checkin uses curly quotes (“confirmed”) in a user-facing string; use ASCII "
         "quotes."),
        ('as3_ellipsis_help', M + 'models/booking.py', 'battery level…',
         "The help of the note field ends with the ellipsis character (…); write three dots."),
    ],
    'orm': [
        ('or1_loop_instead_of_mapped', M + 'models/booking.py', 'equipment_ids.append(booking.equipment.id)',
         "action_return builds equipment_ids with a for loop and append where self.equipment (or mapped) reads "
         "better."),
        ('or2_len_test', M + 'models/booking.py', 'if len(bookings) > 0:',
         "_cron_send_reminders tests if len(bookings) > 0: instead of if bookings:."),
        ('or3_multi_record_read', M + 'models/booking.py', 'if not self.partner_id.email:',
         "_send_reminder reads self.partner_id.email on the whole recordset, while _cron_send_reminders calls it "
         "on every due booking: with bookings of two holders it raises 'Expected singleton', and the email check "
         "is not per booking. Iterate, or check per record."),
        ('or4_prefix_domain', M + 'models/booking.py', "self.search(['|', ('end_datetime'",
         "_cron_archive_past_bookings hand-builds a '|' prefix-notation domain; combine domains with "
         "odoo.fields.Domain (Domain(...) | Domain(...))."),
        ('or5_context_key', M + 'wizard/wizard.py', 'with_context(skip_overlap_check=True)',
         "The custom context key skip_overlap_check (set by the extend wizard, read by _validate_no_overlap) is not "
         "prefixed by the module; module-specific context keys are prefixed (equipment_booking_...) so they do not "
         "leak or collide. Flagging the key itself passes; flagging only that the wizard can bypass the overlap "
         "check does not."),
        ('or6_inherits', M + 'models/equipment_booking_location.py', "_inherits = {'res.partner': 'partner_id'}",
         "equipment.booking.location uses delegation inheritance (_inherits res.partner); it inherits fields but "
         "not methods and should be avoided where a plain Many2one to the address does the job."),
        ('or7_create_multi', M + 'models/booking.py', 'def create(self, vals):',
         "equipment.booking.lines overrides create(self, vals) with @api.model and a single vals; create takes a "
         "list of values with @api.model_create_multi (create(self, vals_list))."),
        ('or8_depends_incomplete', M + 'models/booking.py', "@api.depends('end_datetime')",
         "_compute_is_late reads state but @api.depends lists only end_datetime; every field read must be listed."),
        ('or9_compute_side_effect', M + 'models/booking.py', 'booking.message_post(body=self.env._("Equipment returned."))',
         "The stored compute _compute_return_datetime posts a chatter message (and reads the clock): a stored "
         "compute must have no side effects; it can run again on recompute, and posting belongs in action_return."),
        ('or10_onchange_integrity', M + 'models/booking.py', 'def _onchange_dates(self):',
         "That the end comes after the start is only enforced in _onchange_dates: RPC, the portal route, imports "
         "and the wizard can still store a booking ending before it starts. Enforce it with @api.constrains or a "
         "models.Constraint."),
        ('or11_sql_constraints', M + 'models/equipment_booking_location.py', '_sql_constraints = [',
         "equipment.booking.location declares _sql_constraints, which master ignores (with a warning): the unique "
         "constraint is never created; use models.Constraint."),
        ('or12_public_helper', M + 'models/booking.py', 'def compute_price_for_period(self, start, end):',
         "compute_price_for_period is a public method nothing calls from outside: it is exposed over RPC for no "
         "reason; make it private (_compute_price_for_period). (Reporting it only as unused code does not pass.)"),
        ('or13_premature_hook', M + 'models/booking.py', 'def _get_reminder_delay(self):',
         "_get_reminder_delay returns a constant, has one caller and no override: an extension point split off "
         "before anyone needs it."),
        ('or14_request_in_model', M + 'models/booking.py', 'url = f"{request.httprequest.host_url}',
         "action_share_link uses odoo.http.request in a model method; request is absent in crons, RPC, tests and "
         "the shell. Use self.get_base_url() (or pass the value in from the controller)."),
        ('or15_cr_commit', M + 'models/booking.py', 'self.env.cr.commit()',
         "_cron_archive_past_bookings calls self.env.cr.commit() in its loop, with no comment justifying it; the "
         "framework owns the transaction."),
        ('or16_broad_except', M + 'models/booking.py', 'except Exception:',
         "_send_reminder wraps the whole send in except Exception: pass, which silently swallows every error "
         "(template missing, mail failure, code bugs); catch specific exceptions over the smallest block, and "
         "log them."),
    ],
    'fields': [
        ('fd1_many2one_suffix', M + 'models/booking.py', "equipment = fields.Many2one('maintenance.equipment'",
         "The Many2one equipment lacks the _id suffix (equipment_id)."),
        ('fd2_one2many_suffix', M + 'models/booking.py', "lines = fields.One2many(",
         "The One2many lines lacks the _ids suffix (line_ids)."),
        ('fd3_low_cardinality_index', M + 'models/booking.py', 'reminder_sent = fields.Boolean(copy=False, index=True)',
         "reminder_sent is a boolean with index=True: an index on a low-cardinality field is wasted space and slows "
         "every write."),
        ('fd4_amount_without_currency', M + 'models/booking.py', "price = fields.Float('Price'",
         "price is an amount stored as a plain Float, with no currency; an amount is a Monetary field with its "
         "currency companion (currency_id)."),
        ('fd5_ondelete', M + 'models/booking.py', "ondelete='cascade', tracking=True",
         "The holder partner_id has ondelete='cascade': deleting (or merging away) a partner silently deletes their "
         "bookings and their history; restrict (or set null) is the sensible choice."),
        ('fd6_reserved_active', M + 'models/booking.py', "is_archived = fields.Boolean('Archived'",
         "is_archived is a custom archiving boolean; the reserved active field gives archiving for free "
         "(action_archive, the default filter) instead of the action's hand-written domain."),
        ('fd7_parent_store', M + 'models/equipment_booking_location.py', "parent_id = fields.Many2one('equipment.booking.location'",
         "The location tree has parent_id but no _parent_store and parent_path (indexed), while "
         "_get_bookings_in_subtree searches with child_of."),
        ('fd8_check_company', M + 'models/booking.py', "company_id = fields.Many2one('res.company'",
         "equipment.booking has a company_id but no company consistency: no _check_company_auto and no "
         "check_company on equipment and location_id, so a booking can link records of another company."),
        ('fd10_field_method_collision', M + 'models/booking.py', 'def checkin(self):',
         "The field checkin and the method checkin() share a name: the method, defined later in the class, "
         "replaces the field, which silently disappears from the model."),
        ('fd11_related_through_x2many', M + 'models/booking.py', "related='lines.product_id.name'",
         "accessory_name is related through the One2many lines (lines.product_id.name): the ORM silently keeps the "
         "first line only."),
        ('fd12_shared_inverse', M + 'models/booking.py', "end_date = fields.Date(compute='_compute_dates', inverse='_inverse_dates')",
         "start_date and end_date share one inverse, _inverse_dates: while it runs, both fields are protected and "
         "the sibling reads wrong values. Give each field its own inverse."),
        ('fd13_missing_index', M + 'models/maintenance_equipment.py', "checkin_code = fields.Char('Check-in Code'",
         "checkin_code is a selective code that /booking/checkin searches on, without an index."),
    ],
    'controllers': [
        ('ct1_override_without_route', M + 'controllers/booking_portal.py', 'def home(self, **kw):',
         "BookingPortal.home overrides the portal /my route without re-decorating it with @route() (the framework "
         "auto-decorates it with a warning)."),
        ('ct2_json_route_type', M + 'controllers/booking_portal.py', "@route('/booking/availability', type='json'",
         "/booking/availability uses type='json', a deprecated alias; use type='jsonrpc'."),
    ],
    'xml': [
        ('xm1_record_attribute_order', M + 'views/booking.xml', '<record model="ir.ui.view" id="equipment_booking_view_form">',
         "The form view record is written <record model=... id=...>: id comes before model."),
        ('xm2_records_grouped_by_model', M + 'views/booking.xml', None,
         "views/booking.xml interleaves records of different models (views, actions, views again, the equipment "
         "view, menus) instead of grouping them by model."),
        ('xm3_menuitem_tag', M + 'views/booking.xml', '<record id="equipment_booking_menu" model="ir.ui.menu">',
         "The menu equipment_booking_menu is a raw <record model=\"ir.ui.menu\"> instead of a <menuitem>."),
        ('xm4_noupdate_whole_file', M + 'data/mail-templates.xml', '<data noupdate="1">',
         "data/mail-templates.xml wraps its whole content in <data noupdate=\"1\">; for a fully noupdate file, set "
         "noupdate=\"1\" on <odoo> and drop <data>."),
        ('xm5_view_xml_id', M + 'views/booking.xml', '<record id="view_booking_list"',
         "The list view's xml id view_booking_list does not follow <model>_view_<type> "
         "(equipment_booking_view_list)."),
        ('xm6_action_xml_id', M + 'views/booking.xml', '<record id="action_bookings"',
         "The action's xml id action_bookings does not follow <model>_action (equipment_booking_action)."),
        ('xm7_group_xml_id', M + 'security/groups.xml', '<record id="group_booking_manager"',
         "The group's xml id group_booking_manager does not follow <module>_group_<name> "
         "(equipment_booking_group_manager)."),
        ('xm8_css_class_prefix', M + 'views/portal.xml', 'o_booking_status',
         "The portal template's CSS class o_booking_status is not prefixed by the module (o_equipment_booking_...); "
         "o_ alone is reserved for the web client."),
        ('xm9_positional_xpath', M + 'views/booking.xml', '//sheet/group/group[2]/field[2]',
         "The equipment form extension anchors on position (//sheet/group/group[2]/field[2]) instead of a name "
         "(<field name=\"technician_user_id\" position=\"after\">); it breaks or lands elsewhere when maintenance "
         "or another module changes the form."),
        ('xm10_inherit_view_name', M + 'views/booking.xml', 'maintenance.equipment.form.booking',
         "The inheriting view's name maintenance.equipment.form.booking lacks the .inherit. suffix "
         "(maintenance.equipment.form.inherit.equipment_booking)."),
        ('xm11_readded_field', M + 'views/booking.xml', '<field name="serial_number"/>',
         "The equipment form extension adds serial_number again in its Bookings page, while the parent form "
         "already shows it."),
        ('xm12_mode_primary', M + 'views/booking.xml', '<record id="equipment_booking_view_form_quick"',
         "equipment_booking_view_form_quick is meant as a variant of the booking form (the Quick Booking action) "
         "but inherits it without mode=\"primary\": it extends the main form, hiding the Accessories page for "
         "everyone."),
    ],
    'reports': [
        ('rp1_docs_missing', M + 'report/booking_report.py', 'def _get_report_values(self, docids, data=None):',
         "_get_report_values returns no docs (nor doc_ids, doc_model) while the template loops over docs; a custom "
         "_get_report_values must add them itself."),
        ('rp2_t_lang_without_t_call', M + 'report/booking_report.xml', '<div class="page" t-lang=',
         "t-lang is set on a <div>, not on a node carrying t-call: QWeb raises a SyntaxError when the report is "
         "rendered. Move the translated part into its own template called with t-call and t-lang."),
        ('rp3_needless_rebrowse', M + 'report/booking_report.py', "'localized': {booking.id: booking.with_context(lang=",
         "The report re-browses every booking in the holder's language (localized) while the template reads no "
         "translatable field from it (name, dates): a needless cost."),
    ],
    'access': [
        ('ac1_wizard_no_access_row', M + 'security/ir.access.csv', None,
         "The extend wizard equipment.booking.extend has no ir.access row: with default deny, users other than the "
         "superuser cannot use it."),
        ('ac2_portal_crud', M + 'security/ir.access.csv', 'equipment_booking_access_portal',
         "base.group_portal is granted crud on equipment.booking, with no domain: every portal user can read, "
         "create, edit and delete every booking through RPC."),
        ('ac3_company_restriction', M + 'security/ir.access.csv', None,
         "equipment.booking has a company_id but no group-less company restriction row "
         "([('company_id', 'in', company_ids)])."),
        ('ac4_partial_restriction', M + 'security/ir.access.csv', 'equipment_booking_lines_restrict_own',
         "The restriction row on equipment.booking.lines covers only r, while base.group_user is granted crud: a "
         "user can still write and delete lines of other users' bookings they cannot read (and the read "
         "restriction applies to managers too). Cover every operation that needs restricting."),
    ],
    'performance': [
        ('pf1_search_count_in_loop', M + 'models/res_partner.py', 'search_count([(\'partner_id\', \'=\', partner.id)])',
         "_compute_booking_count runs one search_count per partner; use one _read_group over all partners."),
        ('pf2_create_in_loop', M + 'wizard/wizard.py', "self.env['equipment.booking.lines'].create({",
         "action_extend creates one accessory line per product in a loop; build the vals list and create once."),
        ('pf3_browse_in_loop', M + 'models/res_partner.py', "browse(equipment_id) for equipment_id in equipment_ids",
         "_get_equipment_in_use browses the equipment one id at a time, defeating prefetch; browse(equipment_ids) "
         "once."),
        ('pf4_filtered_after_search', M + 'models/res_partner.py', ".filtered(lambda b: b.state == 'confirmed')",
         "_get_upcoming_bookings filters state in Python after the search; put the condition in the domain."),
        ('pf5_nested_loop', M + 'models/booking.py', 'for other in bookings:',
         "_validate_no_overlap loads every non-cancelled booking of the equipment, history included, and compares "
         "each checked booking with all of them in a nested loop; restrict the search to overlapping periods (or "
         "group by equipment) instead of an O(n*m) scan."),
    ],
    'tests': [
        ('ts1_test_file_not_imported', M + 'tests/test_portal.py', None,
         "tests/test_portal.py is not imported in tests/__init__.py, so its test never runs."),
        ('ts2_test_file_name', M + 'tests/booking_tests.py', None,
         "tests/booking_tests.py is not named test_*.py, so it is skipped although __init__.py imports it."),
        ('ts3_both_install_tags', M + 'tests/test_booking.py', "@tagged('post_install', 'at_install')",
         "TestEquipmentBooking is tagged both post_install and at_install, so it runs twice; set exactly one."),
        ('ts4_at_install_without_comment', M + 'tests/booking_tests.py', "@tagged('at_install', '-post_install')",
         "TestBookingLocation opts into at_install with no comment justifying it."),
        ('ts5_query_count_in_business_test', M + 'tests/test_booking.py', 'with self.assertQueryCount(60):',
         "test_price wraps business assertions in assertQueryCount(60), a loose budget in a business test; query "
         "counts belong in dedicated performance tests, with exact budgets."),
        ('ts6_mute_logger', M + 'tests/test_booking.py', 'def test_reminder_without_email(self):',
         "test_reminder_without_email triggers the expected 'holder has no email' warning without mute_logger, so "
         "it reaches the runbot log."),
        ('ts7_inherited_tests_not_run', M + 'tests/test_booking.py', 'class TestEquipmentBookingManager(TestEquipmentBooking):',
         "TestEquipmentBookingManager defines no test of its own; inherited test_* methods are not collected "
         "without allow_inherited_tests_method = True, so the manager variant runs nothing."),
        ('ts8_demo_data', M + 'tests/test_booking.py', "cls.env.ref('base.res_partner_2')",
         "The tests rely on the demo partner base.res_partner_2 from a plain TransactionCase; demo data is not "
         "guaranteed. Create the records (or start from BaseCommon)."),
        ('ts9_implementation_assert', M + 'tests/test_booking.py', "with patch.object(Booking, '_send_reminder')",
         "test_reminder_sent patches the private _send_reminder and asserts it is called, testing implementation "
         "rather than behavior (a mail queued, reminder_sent set)."),
    ],
    'javascript': [
        ('js1_files_by_type', WEB + 'components/booking_board.js', None,
         "static/src/ is organized by type (components/, hooks/, patches/, scss/, vendor/), so the booking board's "
         "component, template, hook and styles are spread over type folders. Code is organized by feature: one "
         "folder for the board holding all its files (static/src/booking_board/)."),
        ('js2_getter_title', WEB + 'components/booking_board.js', 'get title()',
         "BookingBoard.title is a getter: it hides that code runs and only saves a pair of parentheses. Use a plain "
         "method (or a plain value)."),
        ('js3_getter_derived_state', WEB + 'components/booking_board.js', 'get lateCount()',
         "BookingBoard.lateCount is a getter computing derived state (the late bookings among the loaded ones), "
         "re-run on every read. Use an Owl computed, which recomputes only when the bookings change, or at least "
         "a plain method."),
        ('js4_patch_form_controller', WEB + 'patches/form_controller_patch.js', 'patch(FormController.prototype',
         "The module patches FormController.prototype.onRecordSaved, which runs for every form view, to notify "
         "after saving a booking. Patching is strongly discouraged inside Odoo: use an extension point, such as a "
         "booking form view with a js_class whose controller extends FormController."),
    ],
    'scss': [
        ('css1_scss_variable_name', SCSS, '$bookingCardColor:',
         "The SCSS variable $bookingCardColor does not follow $o-[root]-[element]-[property]-[modifier] "
         "(e.g. $o-equipment-booking-card-color): camelCase, no o- prefix."),
        ('css2_mixin_name', SCSS, '@mixin cardShadow(',
         "The mixin cardShadow is not named o-[imperative verb] (e.g. o-add-card-shadow), and its argument $size "
         "is not in scoped form ($-size). Flagging either half passes."),
        ('css3_root_css_variable', SCSS, ':root {',
         "The CSS variable --booking-accent is defined on :root. CSS variables are for contextual DOM adaptation, "
         "not global design: use an SCSS variable, or define it on the board's own element."),
        ('css4_id_selector', SCSS, '#booking_board_header {',
         "#booking_board_header is an id selector; avoid id selectors, use a class "
         "(o_equipment_booking_board_header)."),
        ('css5_css_variable_bem', SCSS, '--columnGap: 12px;',
         "The CSS variable --columnGap does not follow the BEM convention --[root]__[element]-[property]--[modifier] "
         "(e.g. --BookingBoard__column-gap)."),
        ('css6_property_order', SCSS, '.o_equipment_booking_board_column {',
         "The properties of .o_equipment_booking_board_column are not ordered from the outside in: color and "
         "font-size come first, width and position last. Start with position, then layout and box (width, "
         "padding), and end with decorative ones (color, font)."),
        ('css7_nested_class_name', SCSS, '.o_equipment_booking_board_column_card_header_title {',
         "o_equipment_booking_board_column_card_header_title is a hyper-specific class name that spells out the "
         "DOM nesting; use the flat grandchild approach (o_equipment_booking_board_title)."),
        ('css8_hyphenated_class', SCSS, '.o-booking-card {',
         "The class o-booking-card uses hyphens (and drops the module name): classes use underscores and the "
         "o_<module> prefix (o_equipment_booking_board_card); hyphens are for SCSS variables, mixins and "
         "functions."),
        ('css9_unprefixed_class', SCSS, '.booking_late {',
         "The class booking_late has no o_<module> prefix (o_equipment_booking_board_late)."),
        ('css10_scoped_variable_placement', SCSS, '$-badge-radius: 1rem;',
         "The scoped variable $-badge-radius is declared mid-rule, after declarations; scoped SCSS and CSS "
         "variables go at the top of the rule, separated by a blank line."),
        ('css11_one_line_rule', SCSS, '.o_equipment_booking_board_note {',
         "The rule .o_equipment_booking_board_note is written on one line with three declarations: one "
         "declaration per line, closing brace on its own line."),
        ('css12_tab_indentation', SCSS, '.o_equipment_booking_board_empty {',
         "The rule .o_equipment_booking_board_empty is indented with tabs; SCSS is indented with 4 spaces."),
    ],
    'assets': [
        ('as1_image_by_url', WEB + 'components/booking_board.xml', 'src="https://cdn.jsdelivr.net',
         "The board's header icon is loaded from a CDN (cdn.jsdelivr.net). Every resource a page needs ships in "
         "the codebase: copy the image into the addon (or use the icon font)."),
        ('as2_font_by_url', SCSS, '@import url("https://fonts.googleapis.com',
         "booking_board.scss imports the Inter font from Google Fonts by URL. Fonts ship in the codebase (or use "
         "the webclient's fonts)."),
        ('as3_minified_library', WEB + 'vendor/reltime.min.js', None,
         "The third-party reltime library is vendored minified (reltime.min.js) in static/src/vendor/. "
         "Third-party libraries go in static/lib/, unminified, so they can be read and diffed."),
    ],
    'security': [
        ('sc1_public_route_exposes_data', M + 'controllers/booking_portal.py', "@route('/booking/calendar/<int:equipment_id>'",
         "/booking/calendar/<id> is auth='public' and searches bookings with sudo: anonymous visitors see holder "
         "names and booking notes of any equipment."),
        ('sc2_sql_injection', M + 'controllers/booking_portal.py', "AND start_datetime::date = '{day}'",
         "/booking/availability interpolates the request parameter day into the SQL with an f-string: SQL "
         "injection. Pass it as a query parameter."),
        ('sc3_raw_sql_bypasses_orm', M + 'models/res_partner.py', 'self.env.cr.execute("""',
         "_get_equipment_in_use reads equipment_booking with raw SQL where an ORM search does it, bypassing access "
         "rules and the ORM (flush, active)."),
        ('sc4_domain_injection', M + 'controllers/booking_portal.py', 'domain = json.loads(filter_domain) + domain',
         "portal_my_bookings prepends the request's filter_domain to the ownership domain and searches with sudo: a "
         "filter starting with '|' turns it into 'anything or mine', exposing every booking. Combine with Domain "
         "(AND) and validate the user domain."),
        ('sc5_public_method_sudo_write', M + 'models/booking.py', 'def set_booking_state(self, state):',
         "set_booking_state is public, so callable over RPC on any ids, and writes the given state with sudo: any "
         "user can set any booking to any state."),
        ('sc6_get_route_changes_state', M + 'controllers/booking_portal.py', "@route('/my/bookings/<int:booking_id>/cancel'",
         "/my/bookings/<id>/cancel cancels a booking on a GET request: a link or an image tag on another site "
         "cancels the victim's booking (CSRF). Use POST with the CSRF token."),
        ('sc7_csrf_disabled', M + 'controllers/booking_portal.py', 'csrf=False',
         "/my/bookings/<id>/update is an http POST route with csrf=False: any site can submit it as the logged-in "
         "user."),
        ('sc8_form_without_csrf_token', M + 'views/portal.xml', '<form t-attf-action="/my/bookings/#{booking.id}/update" method="post">',
         "The portal booking page's update form posts without the csrf_token hidden input (the reason the route "
         "disables CSRF)."),
        ('sc9_markup_fstring', M + 'models/booking.py', 'Markup(f"<p>Cancelled: {reason}</p>")',
         "action_cancel builds Markup(f\"<p>Cancelled: {reason}</p>\"): the f-string defeats escaping, so the "
         "reason is posted to the chatter as raw HTML (XSS). Use Markup(\"<p>Cancelled: %s</p>\") % reason, or "
         ".format."),
        ('sc10_t_esc_server_qweb', M + 'report/booking_report.xml', '<span t-esc="holder_phones[doc.id]"/>',
         "The report uses t-esc, which server QWeb ignores (it renders nothing), so the holder's phone never shows; "
         "use t-out."),
        ('sc11_token_without_groups', M + 'models/res_partner.py', "booking_feed_token = fields.Char(",
         "res.partner.booking_feed_token is a secret (it authenticates the calendar feed) with no groups: any "
         "internal user can read every partner's token with search_read. Restrict it (base.group_system or "
         "fields.NO_ACCESS)."),
        ('sc12_related_sudo_secret', M + 'models/booking.py', "feed_token = fields.Char(related='partner_id.booking_feed_token')",
         "feed_token is a related field (computed with sudo by default) reaching the partner's feed token through "
         "the user-writable partner_id: point a booking at any partner and read their token. Set related_sudo=False "
         "or drop the field."),
        ('sc13_related_attachment', M + 'models/booking.py', "related='manual_attachment_id.raw'",
         "manual_file is a sudo-computed related field onto ir.attachment through the user-writable "
         "manual_attachment_id: set it to any attachment id and read any file. Use a plain Binary or the "
         "attachment's own access checks."),
        ('sc14_sudo_write_request_params', M + 'controllers/booking_portal.py', 'booking_sudo.write(post)',
         "portal_booking_update writes the raw request parameters with sudo (booking_sudo.write(post)): the holder "
         "can set any field (state, partner_id, price, company_id, line commands). Whitelist the keys (note)."),
        ('sc15_with_user_from_request', M + 'controllers/booking_portal.py', "with_user(booked_by)",
         "portal_booking_create switches to with_user(int(post['user_id'])): the request picks the user the "
         "booking is created as, any user included."),
        ('sc16_open_builtin', M + 'report/booking_report.py', "with open(path, 'rb') as picture:",
         "_get_equipment_picture opens a path built from the equipment's serial number with the builtin open(): a "
         "serial number like ../../.. reads arbitrary files. Use file_open, or store the picture as an attachment."),
        ('sc17_safe_eval_user_expression', M + 'models/equipment_booking_location.py', 'safe_eval(self.booking_condition',
         "_accepts_booking runs safe_eval on booking_condition, which any internal user can write (cru on "
         "locations): evaluating an expression is only for trusted, privileged users."),
        ('sc18_pickle', M + 'models/res_partner.py', 'pickle.loads(',
         "_get_booking_preferences unpickles a stored field: pickle runs arbitrary code on load; store JSON."),
        ('sc19_getattr_request_name', M + 'controllers/booking_portal.py', 'getattr(booking, sortby)',
         "portal_my_bookings sorts with getattr(booking, sortby), sortby coming from the request, on sudo records: "
         "the user picks any attribute (private methods, any field). Whitelist sort keys and use record[name]."),
        ('sc20_token_comparison', M + 'controllers/booking_portal.py', 'partner.booking_feed_token != token',
         "booking_feed compares the feed token with != instead of a constant-time comparison (consteq)."),
        ('sc21_mutable_default', M + 'models/booking.py', 'def _prepare_reminder_values(self, extra_values={}):',
         "_prepare_reminder_values has a mutable default (extra_values={}) that it updates: the dict is shared "
         "across calls and carries the previous booking's reply_to."),
        ('sc22_public_method_returns_object', M + 'models/maintenance_equipment.py', 'def get_label_signer(self):',
         "get_label_signer is a public method returning an hmac object keyed with database.secret: reachable from "
         "safe_eval'd code (server actions) and RPC, it lets anyone sign check-in codes or walk the object. Make "
         "it private, or a module-level function."),
        ('sc23_markup_note_js', WEB + 'components/booking_board.js', 'return markup(booking.note',
         "The booking board renders booking.note through markup(), which marks it as safe HTML. Portal users "
         "write the note (/my/bookings/<id>/update), so their HTML and scripts run in the backend of every user "
         "who opens the board (stored XSS). Render the note as plain text."),
    ],
    'consumers': [
        ('rv1_override_signature', 'addons/maintenance/models/maintenance.py', '_get_owner_methods_by_equipment_assign_to(date=',
         "_compute_owner now calls _get_owner_methods_by_equipment_assign_to(date=...), but the overrides in "
         "hr_maintenance and fleet_maintenance take no date argument: computing the owner raises a TypeError "
         "wherever one of them is installed. Naming one of those overrides (or the existing overrides in general, "
         "found by searching for them) passes."),
        ('rv2_field_rename', 'addons/maintenance/models/maintenance.py', "serial_number = fields.Char('Serial Number'",
         "The rename of maintenance.equipment.serial_no to serial_number is not carried to its consumers: "
         "stock_maintenance (a @depends and a view), fleet_maintenance and hr_maintenance (views) still use "
         "serial_no and fail to install or load. Naming one of those modules passes."),
    ],
    'merits': [
        ('jg1_back_to_back_rejected', M + 'models/booking.py', 'other.start_datetime <= booking.end_datetime',
         "The overlap check compares with <= and >=, so a booking starting exactly when another ends is rejected "
         "as overlapping; back-to-back bookings need strict comparisons."),
        ('jg2_date_compared_to_datetime', M + 'models/booking.py', 'limit = fields.Date.today() + timedelta(',
         "_cron_send_reminders compares start_datetime with a date (fields.Date.today() + 1 day, midnight UTC): a "
         "booking starting tomorrow at 9:00 is not due until the next day, so the reminder comes on the day "
         "itself, not the day before; timezones are ignored as well."),
        ('jg3_rounding', M + 'models/booking.py', 'booking.price = round(hourly * booking.duration, 2)',
         "_compute_price rounds with round(..., 2) instead of the currency's rounding."),
        ('jg4_vacuous_test', M + 'tests/test_booking.py', 'self.assertTrue(self.booking.state)',
         "test_cancel asserts that state is truthy, which it always is: the test passes whether or not the "
         "booking was cancelled."),
        ('jg5_message_claim', None, None,
         "The commit message says cancelling a booking notifies the equipment's technician; action_cancel notifies "
         "no one (it only posts the reason on the booking)."),
    ],
}
