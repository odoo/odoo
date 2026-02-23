import re
from odoo.upgrade_code.tools_etree import update_etree
from odoo.upgrade_code.tools_js_expressions import update_template, VariableAggregator

EXCLUDED_FILES = (
    'addons/spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
    'addons/web/static/lib/owl/owl.js',
    'addons/web/static/src/owl2/utils.js',
    'pos_blackbox_be/static/src/pos/overrides/navbar/navbar.xml',
    'html_builder/static/tests/custom_tab/builder_components/builder_list.test.js',  # Test has weird string formatting syntax easier to skip
    'html_builder/static/tests/custom_tab/builder_components/builder_row.test.js',  # Test has weird string formatting syntax easier to skip
)

# Templates that are called by:
# - this.renderAt   (Interaction)
# - renderToString
# - renderToFragment
# - renderToElement
EXCLUDED_TEMPLATES = (
    'Appointment.appointment_info_no_capacity',
    'Appointment.appointment_info_no_slot',
    'Appointment.appointment_info_no_slot_month',
    'Appointment.appointment_info_upcoming_appointment',
    'Appointment.appointment_svg',
    'ai.VoiceTranscriptionBlueprint',
    'ai_website_livechat.s_ai_livechat_edit',
    'appointment.resources_capacity_options',
    'appointment.resources_list',
    'appointment.slots_list',
    'calendar.AttendeeCalendarCommonRenderer.event',
    'delivery.locationSelector.map',
    'event.EventSlotCalendarCommonRenderer.event',
    'event_booth_checkbox_list',
    'event_booth_registration_complete',
    'event_track_proposal_success',
    'google_recaptcha.recaptcha_legal_terms',
    'hr_calendar.CalendarCommonRenderer.buttonWorklocation',
    'hr_calendar.CalendarCommonRendererHeader',
    'hr_contract_salary.salary_package_resume',
    'hr_contract_salary_payroll.salary_package_brut_to_net_modal',
    'html_builder.BuilderOverlay',
    'html_builder.background_grid',
    'html_editor.EmbeddedCaptionBlueprint',
    'html_editor.EmbeddedFileBlueprint',
    'html_editor.EmbeddedSyntaxHighlightingBlueprint',
    'html_editor.EmbeddedToggleBlockBlueprint',
    'html_editor.EmbeddedVideoBlueprint',
    'html_editor.Signature',
    'html_editor.StaticFileBox',
    'html_editor.TableOfContentBlueprint',
    'knowledge.ArticleBlueprint',
    'knowledge.ArticleIndexBlueprint',
    'knowledge.ArticleItemTemplate',
    'knowledge.EmbeddedClipboardBlueprint',
    'knowledge.EmbeddedViewBlueprint',
    'knowledge.EmbeddedViewLinkBlueprint',
    'knowledge.FoldableSectionBlueprint',
    'knowledge.threadBeacon',
    'mail.ExpandableButton',
    'mail.Message.edited',
    'mail.Message.mentionedChannelIcon',
    'mail.Message.messageLink',
    'mail.Wysiwyg.mentionLink',
    'mass_mailing.FavoritePreviewBody',
    'mass_mailing.IframeBody',
    'mass_mailing.IframeHead',
    'mass_mailing.MailingPreviewIframeBody',
    'mass_mailing.portal.list_form_con',
    'mass_mailing.portal.list_form_content_readonly',
    'mass_mailing.s_masonry_block_alternation_image_text_template',
    'mass_mailing.s_masonry_block_alternation_text_image_template',
    'mass_mailing.s_masonry_block_alternation_text_image_text_template',
    'mass_mailing.s_masonry_block_alternation_text_template',
    'mass_mailing.s_masonry_block_default_template',
    'mass_mailing.s_masonry_block_image_texts_image_template',
    'mass_mailing.s_masonry_block_images_template',
    'mass_mailing.s_masonry_block_mosaic_template',
    'mass_mailing.s_masonry_block_reversed_template',
    'mass_mailing.s_masonry_block_texts_image_texts_template',
    'mass_mailing.social_media_link',
    'mass_mailing.social_media_placeholder',
    'mass_mailing.social_media_title',
    'mass_mailing_sale.s_product_snapshot_aside_fragment',
    'mass_mailing_sale.s_product_snapshot_card_fragment',
    'mass_mailing_sale.s_product_snapshot_columns_fragment',
    'mrp.CalendarCommonRenderer.event',
    'o-spreadsheet-CustomTooltip',
    'planning.allocation_info',
    'planning.daygrid_event',
    'point_of_sale.pos_cash_move_receipt',
    'point_of_sale.pos_order_change_receipt',
    'point_of_sale.pos_order_receipt',
    'point_of_sale.pos_sale_details_receipt',
    'point_of_sale.pos_tip_receipt',
    'portal.Chatter.Attachments',
    'portal.Composer',
    'portal_rating.PopupComposer',
    'portal_rating.rating_stars_static',
    'project_enterprise.TaskGanttRenderer.Header',
    'quiz.badge',
    'quiz.comment',
    'quiz.validation',
    'sign.signItem',
    'slide.course.join',
    'slide.course.prerequisite',
    'slide.slide.quiz',
    'slide.slide.quiz.validation',
    'stock_enterprise.markerPopup',
    'survey.survey_breadcrumb_template',
    'survey.survey_image_zoomer',
    'survey.survey_session_text_answer',
    'test.render.template.1',
    'web.CalendarCommonRenderer.event',
    'web.CalendarCommonRendererHeader',
    'web.ProfilingQwebView.hover',
    'web.ProfilingQwebView.info',
    'web.TestSubInteraction1',
    'web.caps_lock_warning',
    'web.sign_svg_text',
    'web.testRenderAt',
    'web_gantt.GanttRenderer.Header',
    'web_map.marker',
    'web_map.markerPopup',
    'website.AddPageTemplatePreviewDynamicMessage',
    'website.MapsDescription',
    'website.PageDependencies.Tooltip',
    'website.background.video',
    'website.cookiesWarning',
    'website.cookies_bar.classic',
    'website.cookies_bar.discrete',
    'website.cookies_bar.popup',
    'website.cookies_bar.text_button_all',
    'website.cookies_bar.text_button_essential',
    'website.cookies_bar.text_primary',
    'website.cookies_bar.text_secondary',
    'website.cookies_bar.text_title',
    'website.empty_image_gallery_alert',
    'website.empty_social_media_alert',
    'website.example_social_media_link',
    'website.form_field_binary',
    'website.form_field_boolean',
    'website.form_field_char',
    'website.form_field_date',
    'website.form_field_datetime',
    'website.form_field_description',
    'website.form_field_email',
    'website.form_field_float',
    'website.form_field_hidden',
    'website.form_field_html',
    'website.form_field_integer',
    'website.form_field_many2many',
    'website.form_field_many2one',
    'website.form_field_monetary',
    'website.form_field_one2many',
    'website.form_field_selection',
    'website.form_field_tel',
    'website.form_field_text',
    'website.form_field_url',
    'website.homepage_editor_welcome_message',
    'website.image_mirror.lightbox',
    'website.s_card.imageWrapper',
    'website.s_carousel_cards.imageWrapper',
    'website.s_countdown.end_message',
    'website.s_countdown.end_redirect_message',
    'website.s_dynamic_snippet.carousel',
    'website.s_dynamic_snippet.grid',
    'website.s_floating_blocks.alert.empty',
    'website.s_floating_blocks.new_card',
    'website.s_image_gallery_slideshow',
    'website.s_searchbar.autocomplete',
    'website.s_website_form_end_message',
    'website.s_website_form_recaptcha_legal',
    'website.s_website_form_status_custom_error',
    'website.s_website_form_status_error',
    'website.s_website_form_status_success',
    'website.slides.fullscreen.certification',
    'website.slides.fullscreen.content',
    'website.slides.fullscreen.video.google_drive',
    'website.slides.fullscreen.video.vimeo',
    'website.slides.fullscreen.video.youtube',
    'website.slides.sidebar.done.button',
    'website.social_modal',
    'website_cf_turnstile.turnstile_container',
    'website_cf_turnstile.turnstile_remote_script',
    'website_event_track.email_reminder_modal',
    'website_event_track.pwa_install_banner',
    'website_event_track_live.website_event_track_replay_suggestion',
    'website_event_track_live.website_event_track_suggestion',
    'website_forum.spam_search_name',
    'website_helpdesk.knowledge_base_autocomplete',
    'website_links.RecentLink',
    'website_mass_mailing.NewsletterMailingListsCheckboxes',
    'website_mass_mailing.subscribeListMissingError',
    'website_mass_mailing_event.s_event_snapshot_aside_fragment',
    'website_mass_mailing_event.s_event_snapshot_card_fragment',
    'website_mass_mailing_event.s_event_snapshot_columns_fragment',
    'website_payment.donation.descriptionTranslationInputs',
    'website_payment.donation.prefilledButtons',
    'website_payment.donation.prefilledButtonsDescriptions',
    'website_payment.donation.slider',
    'website_payment.s_supported_payment_methods.icons',
    'website_payment.s_supported_payment_methods.no_payment_methods_alert',
    'website_sale.s_dynamic_snippet_category.grid',
    'website_sale_autocomplete.AutocompleteDropDown',
    'website_sale_mondialrelay',
    'website_sale_stock.product_availability',
    'website_sale_stock.product_availability_wishlist',
    'website_sale_subscription.SubscriptionPricingTableSelect',
)


class MigrationCollector:
    """Collects logs from multiple sub-functions within a single upgrade script."""

    def __init__(self):
        self.reports = []

    def run_sub(self, name: str, func, file_manager) -> None:
        """Executes a sub-upgrade function and stores its result.

        Args:
            name: The display name of the task.
            func: The function to execute.
            file_manager: The Odoo file manager instance.
        """
        modified_before = sum(1 for f in file_manager if f.dirty)
        errors = []
        infos = []

        # Internal loggers for the sub-function
        def log_info(msg): infos.append(msg)
        def log_error(path, err): errors.append(f"  ❌ {path}: {err}")

        func(file_manager, log_info, log_error)

        modified_after = sum(1 for f in file_manager if f.dirty)
        count = modified_after - modified_before

        report = [f"\n🚀 TASK: {name}", "-" * 40]
        if infos:
            report.extend([f"  ℹ️  {i}" for i in infos])
        if errors:
            report.append("  ⚠️  ERRORS:")
            report.extend(errors)
        report.append(f"  ✅ Files modified in this task: {count}")

        self.reports.append("\n".join(report))

    def get_final_logs(self) -> str:
        """Returns all collected reports as a single string."""
        return "\n".join(self.reports)


WEB_WHITELIST = {
    "web.Breadcrumb.Name": {'breadcrumb'},  # Var above t-call
    "web.CalendarFilterSection.filter": {'filter'},  # dynamic t-call
    "web.CalendarYearPopover.record": {'record'},  # t-for-each above dynamic t-call
    "web.FieldTooltip": {'field', 'debug', 'resModel'},  # JSON stringify context
    "web.ListRenderer.RecordRow": {'record', 'group', 'groupId', '_canSelectRecord'},  # dynamic t-call I guess,
    "web.ListRenderer.GroupRow": {'group'},  # dynamic t-call I guess
    "web.ListHeaderTooltip": {'field'},  # JSON stringify context
    "web.Many2ManyBinaryField.attachment_preview": {'file'},  # t-for-each above t-call
    "web.Many2ManyTagsAvatarField.option": {'autoCompleteItemScope'},  # t-slot-scope above dynamic t-call
    "web.PivotMeasure": {'cell'},  # for each + t-call
    "web.SearchPanelContent": {'section'},  # dynamic t-call
    "web.SearchPanel.Small": {'section'},  # dynamic t-call
    "web.SearchPanel.Category": {'section'},  # dynamic t-call
    "web.SearchPanel.FiltersGroup": {'values', 'section', 'group'},  # dynamic t-call
    "web.SelectMenu.ChoiceItem": {'choice', 'choice_index'},  # dynamic t-call
    "web.SelectMenu.search": {'inputClass'},  # Var above t-call
    "web.TreeEditor.condition:editable": {'node'},  # Nested inherit
    "web.TreeEditor.condition:readonly": {'node'},  # Nested inherit
    "web.TreeEditor.controls": {'node', 'ancestors', 'parent'},  # Nested inherit
    "web.TreeEditor.connector.value": {'node'},  # Nested inherit
    "web.TreeEditor.condition": {'node'},  # Nested inherit
    "web.TreeEditor.complex_condition": {'node'},  # Nested inherit
    "views.ViewButtonTooltip": {'debug', 'button', 'model'},  # JSON stringify context
}
MAIL_WHITELIST = {
    "discuss.GifPicker.gif": {'gif_value'},  # for-each above t-call
    "mail.MessageSeenIndicatorPopover.card": {'member'},  # for-each above t-call
    "mail.Composer.extraActions": {'partitionedActions'},  # Var above t-call
    "mail.Composer.quickActions": {'partitionedActions'},  # Var above t-call
    "mail.Composer.suggestionSpecial": {'option'},  # dynamic t-call
    "mail.Composer.suggestionPartner": {'option'},  # dynamic t-call
    "mail.Composer.suggestionRole": {'option'},  # dynamic t-call
    "mail.Composer.suggestionChannel": {'option'},  # dynamic t-call
    "mail.Composer.suggestionChannelCommand": {'option'},  # dynamic t-call
    "mail.Composer.suggestionCannedResponse": {'option'},  # dynamic t-call
    "mail.Composer.suggestionEmoji": {'option'},  # dynamic t-call
}
EVENT_WHITELIST = {
    "pos_event.QuestionInputs": {'questions', 'stateObject'},  # Var above t-call
    "event.mailTemplateReferenceField": {'relation'},  # Nested t-inherits
}

ACCOUNT_WHITELIST = {
    "account_saft.company_data_warning": {'warningParams'},  # dynamic t-call
    "account_disallowed_expenses.warning_multi_rate": {'warningParams'},  # dynamic t-call
    "account_fiscal_categories_fleet.warning_missing_fiscal_category": {'warningParams'},  # dynamic t-call
    "account_reports.has_bank_miscellaneous_move_lines": {'warningParams'},  # dynamic t-call
    "account_reports.journal_balance": {'warningParams'},  # dynamic t-call
    "account_reports.inconsistent_statement_warning": {'warningParams'},  # dynamic t-call
}
THIS_TARGETS = ["ai"]


def upgrade_this(file_manager, log_info, log_error):
    all_files = [
        f for f in file_manager
        if 'static/src' in f.path._str
        and f.path.suffix == '.xml'
        and not any(f.path._str.endswith(p) for p in EXCLUDED_FILES)
    ]

    white_vars = {
        "crm.ColumnProgress": {'bar'},  # Nested inherit
        "pos_restaurant.floor_screen_element": {'element'},  # for each + t-call
    }  # vars defined inside template, eg. using t-set
    white_vars = white_vars | MAIL_WHITELIST | WEB_WHITELIST | EVENT_WHITELIST

    # Iteration 1: Gather all variables
    aggregator = VariableAggregator()
    for _, file in enumerate(all_files, start=1):
        def callback(tree):
            aggregator.aggregate_inside_vars(tree)
            aggregator.aggregate_call_vars(tree)

        update_etree(file.content, callback)

    aggregator.all_vars = aggregator.all_vars | white_vars

    # Iteration 2: Update templates
    for fileno, file in enumerate(all_files, start=1):
        try:
            file.content = update_template(file.path._str, file.content, THIS_TARGETS, aggregator, EXCLUDED_TEMPLATES)
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)


def upgrade_this_in_js(file_manager, log_info, log_error):
    pattern = re.compile(r"(\bxml\s*`)(.*?)(`)", re.DOTALL)

    test_files = [
        f for f in file_manager
        if f.path._str.endswith(".js")
        and not any(f.path._str.endswith(p) for p in EXCLUDED_FILES)
    ]

    pattern = re.compile(r"(\bxml\s*`)(.*?)(`)", re.DOTALL)
    for _, file in enumerate(test_files, start=1):
        # TODO add warning for clients who have ${} inside fragments
        if THIS_TARGETS and not any(
            f"/{module}/" in file.path._str or f"/{module}_" in file.path._str
            for module in THIS_TARGETS
        ):
            continue
        try:
            def process_match(match):
                prefix = match.group(1)   # The "xml`" part
                raw_xml = match.group(2)  # The content inside backticks
                suffix = match.group(3)   # The closing "`"

                wrapped_xml = f"<t t-name='xyz'>{raw_xml}</t>"

                processed_wrapped = update_template("", wrapped_xml, {}, {}, [], {})

                inner_xml = re.sub(r'^<[^>]+>', '', processed_wrapped)
                inner_xml = re.sub(r'</[^>]+>$', '', inner_xml)

                return f"{prefix}{inner_xml}{suffix}"

            new_content = pattern.sub(process_match, file.content)

            if new_content != file.content:
                file.content = new_content

        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)


def upgrade(file_manager) -> str:
    """Main entry point called by Odoo."""
    collector = MigrationCollector()

    collector.run_sub("Migrating this. in xml templates", upgrade_this, file_manager)
    # collector.run_sub("Migrating this. in test.js xml fragments", upgrade_this_in_js, file_manager)

    return collector.get_final_logs()
