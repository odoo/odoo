import re
from odoo.upgrade_code.tools_etree import update_etree
from odoo.upgrade_code.tools_js_expressions import update_template, VariableAggregator

EXCLUDED_PATH = (
    'web/static/lib/hoot',
    'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
    'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.xml',
    'iot_drivers/static/src/',
    'web/static/src/owl2',
    'addons/web/static/lib/owl/owl.js',
    'html_builder/static/tests/custom_tab/builder_components/builder_list.test.js',  # Test has weird string formatting syntax easier to skip
    'html_builder/static/tests/custom_tab/builder_components/builder_row.test.js',  # Test has weird string formatting syntax easier to skip
    'web_studio/static/src/client_action/report_editor/report_editor_xml/translate_xml.js',  # Weird inline xml, easier to do by hand
    '/node_modules/',
    'test_assetsbundle/static/invalid_src',
    'test_assetsbundle/static/accessible.xml',
)


CHECKSUM_FILES = (
    'pos_blackbox_be/static/src/pos/overrides/navbar/navbar.xml',
    'iot_drivers/iot_handlers/drivers/serial_scale_driver.py',
)


# Templates that are called by:
# - this.renderAt   (Interaction)
# - renderToString
# - renderToFragment
# - renderToElement
EXCLUDED_TEMPLATES = (
    'point_of_sale.Navbar',  # Inherited from checksum file, to remove from list when checksum is recertified
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
    'mass_mailing.portal.list_form_content',
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


class JSTooling:
    @staticmethod
    def is_commented(content: str, position: int) -> bool:
        """Checks if the word at the given position is on a commented line.

        Args:
            content: The full file content.
            position: The index of the word to check.

        Returns:
            True if the line starts with //, /* or /** before the position.
        """
        # We look back to the start of the current line
        line_start = content.rfind('\n', 0, position) + 1
        line_text = content[line_start:position].lstrip()
        return '//' in line_text or '/*' in line_text or '/**' in line_text or line_text.startswith("*")

    @staticmethod
    def add_import(content: str, name: str, source: str) -> str:
        """Adds a named import to a specific source.

        If the source already exists, appends the name and preserves multiline
        formatting if the original import was multiline.

        Args:
            content: The JS file content.
            name: The name of the hook or variable to import.
            source: The library source (e.g., '@odoo/owl').

        Returns:
            The updated file content.
        """
        pattern = rf'import\s*\{{([^}}]*)\}}\s*from\s*(["\']){source}\2;?'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            raw_content = match.group(1)
            quote = match.group(2)
            is_multiline = '\n' in raw_content
            names = [n.strip() for n in raw_content.split(',') if n.strip()]

            if name not in names:
                names.append(name)
                names.sort()  # Alphabetical order for consistency

                if is_multiline:
                    formatted = ',\n    '.join(names)
                    new_import = f'import {{\n    {formatted},\n}} from {quote}{source}{quote};'
                else:
                    new_import = f'import {{ {", ".join(names)} }} from {quote}{source}{quote};'

                return content[:match.start()] + new_import + content[match.end():]
            return content

        return f'import {{ {name} }} from "{source}";\n{content}'

    @staticmethod
    def remove_import(content: str, name: str, source: str) -> str:
        """Removes a named import from a source.

        Deletes the entire line if no imports are left.
        Handles multiline formatting during cleanup.

        Args:
            content: The JS file content.
            name: The name of the import to remove.
            source: The library source.

        Returns:
            The updated file content.
        """
        pattern = rf'import\s*\{{([^}}]*)\}}\s*from\s*(["\']){source}\2;?\n?'

        def replacer(match):
            raw_content = match.group(1)
            quote = match.group(2)
            is_multiline = '\n' in raw_content
            names = [n.strip() for n in raw_content.split(',') if n.strip()]

            if name in names:
                names.remove(name)

            if not names:
                return ""  # Line is removed if no names left

            if is_multiline and len(names) > 1:
                formatted = ',\n    '.join(names)
                return f'import {{\n    {formatted},\n}} from {quote}{source}{quote};\n'
            else:
                return f'import {{ {", ".join(names)} }} from {quote}{source}{quote};\n'

        return re.sub(pattern, replacer, content, flags=re.DOTALL)

    @staticmethod
    def transform_xml_literals(content: str, transform_func: callable) -> str:
        """Finds all xml`template` literals and applies a transformation function.

        Args:
            content: The JS file content.
            transform_func: Function to apply to the inner XML string.

        Returns:
            The JS content with transformed XML templates.
        """
        pattern = re.compile(r"(\bxml\s*`)(.*?)(`)", re.DOTALL)

        def replacer(match: re.Match) -> str:
            prefix = match.group(1)
            xml_content = match.group(2)
            suffix = match.group(3)
            return f"{prefix}{transform_func("<t>" + xml_content + "</t>")[3:][:-4]}{suffix}"

        return pattern.sub(replacer, content)

    @staticmethod
    def transform_js_string_literals(content: str, transform_func: callable) -> str:
        """Finds JS string literals ('...', "...", `...`) and applies a transformation function.

        Args:
            content: The JS file content.
            transform_func: Function to apply to the inner string.

        Returns:
            The JS content with transformed string literals.
        """
        pattern = re.compile(
            r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`",
            re.DOTALL,
        )

        def replacer(match: re.Match) -> str:
            literal = match.group(0)
            delimiter = literal[0]
            inner = literal[1:-1]
            return delimiter + transform_func(inner) + delimiter

        return pattern.sub(replacer, content)

    @staticmethod
    def transform_arch_templates(content: str, transform_func: callable) -> str:
        """Finds arch: `...` or arch = `...` template literals and applies a transform
        function to the inner XML string.
        """
        pattern = re.compile(r"(\barch\b\s*(?:[:=])\s*`)(.*?)(`)", re.DOTALL)

        def replacer(match: re.Match) -> str:
            prefix = match.group(1)
            xml_content = match.group(2)
            suffix = match.group(3)
            return f"{prefix}{transform_func(xml_content)}{suffix}"

        return pattern.sub(replacer, content)

    @staticmethod
    def has_active_usage(content: str, word: str) -> bool:
        """Checks if a word is used outside of a comment line.

        Args:
            content: The file content.
            word: The word to look for (e.g., 'useEffect').

        Returns:
            True if at least one usage is not commented out.
        """
        for match in re.finditer(rf'\b{word}\(', content):
            if not JSTooling.is_commented(content, match.start()):
                return True
        return False

    @staticmethod
    def replace_usage(content: str, old_name: str, new_name: str) -> str:
        """Replaces usage on lines that aren't comments.

        Args:
            content: The file content.
            old_name: Original variable name.
            new_name: New variable name.
        Returns:
            The updated content.
        """
        def replacer(match):
            if JSTooling.is_commented(content, match.start()):
                return match.group(0)  # Return unchanged
            return new_name

        return re.sub(rf'\b{old_name}\b', replacer, content)

    @staticmethod
    def clean_whitespace(content: str) -> str:
        """Removes trailing whitespace and lines containing only spaces.

        Args:
            content: The file content.

        Returns:
            Cleaned content.
        """
        content = re.sub(r'^[ \t]+$', '', content, flags=re.MULTILINE)
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
        return content

    @staticmethod
    def get_js_files(file_manager, include_test_files=False):
        """Gets all static js files. Include .test.js files if include_test_files is True."""
        path_pattern = re.compile('|'.join(EXCLUDED_PATH + CHECKSUM_FILES))

        return [
            f for f in file_manager
            if str(f.path).endswith('.js')
            and '/static/' in str(f.path)
            and not path_pattern.search(str(f.path))
        ]

    @staticmethod
    def get_template_files(file_manager):
        excluded_path_pattern = re.compile('|'.join(EXCLUDED_PATH + CHECKSUM_FILES))
        return [
            file for file in file_manager
            if '/static/' in str(file.path)
            and (str(file.path).endswith('.js') or str(file.path).endswith('.xml'))
            and not re.search(excluded_path_pattern, str(file.path))
        ]

    @staticmethod
    def get_xml_files(file_manager):
        path_pattern = re.compile('|'.join(EXCLUDED_PATH + CHECKSUM_FILES))
        return [
            file for file in file_manager
            if '/static/' in str(file.path)
            and str(file.path).endswith('.xml')
            and not re.search(path_pattern, str(file.path))
        ]


class MigrationCollector:
    """Collects logs from multiple sub-functions and pushes them to FileManager."""

    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.reports = []

    def run_sub(self, name: str, func, **kwargs) -> None:
        modified_before = sum(1 for f in self.file_manager if f.dirty)
        errors = []
        infos = []

        def log_info(msg):
            infos.append(msg)

        def log_error(path, err):
            errors.append(f"  ❌ {path}: {err}")

        func(self.file_manager, log_info, log_error, **kwargs)

        modified_after = sum(1 for f in self.file_manager if f.dirty)
        count = modified_after - modified_before

        report = [f"\n🚀 TASK: {name}", "-" * 40]
        if infos:
            report.extend([f"  ℹ️  {i}" for i in infos])
        if errors:
            report.append("  ⚠️  ERRORS:")
            report.extend(errors)
        report.append(f"  ✅ Files modified: {count}")

        self.reports.append("\n".join(report))

    def finalize(self) -> None:
        if self.reports:
            self.file_manager.add_to_summary("\n".join(self.reports))


def upgrade_useeffect(file_manager, log_info, log_error):
    """Sub-task: Migrate useEffect to useLayoutEffect, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useEffect'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useEffect', '@odoo/owl')
            file.content = JSTooling.replace_usage(file.content, 'useEffect', 'useLayoutEffect')
            file.content = JSTooling.add_import(file.content, 'useLayoutEffect', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_onwillrender(file_manager, log_info, log_error):
    """Sub-task: Migrate onWillRender, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'onWillRender'):
                continue
            file.content = JSTooling.remove_import(file.content, 'onWillRender', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'onWillRender', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_onrendered(file_manager, log_info, log_error):
    """Sub-task: Migrate onRendered, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'onRendered'):
                continue
            file.content = JSTooling.remove_import(file.content, 'onRendered', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'onRendered', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_usecomponent(file_manager, log_info, log_error):
    """Sub-task: Migrate useComponent, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useComponent'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useComponent', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useComponent', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_useenv(file_manager, log_info, log_error):
    """Sub-task: Migrate useEnv, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useEnv'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useEnv', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useEnv', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_usesubenv(file_manager, log_info, log_error):
    """Sub-task: Migrate useSubEnv, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useSubEnv'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useSubEnv', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useSubEnv', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_usechildsubenv(file_manager, log_info, log_error):
    """Sub-task: Migrate useChildSubEnv, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useChildSubEnv'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useChildSubEnv', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useChildSubEnv', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_useref(file_manager, log_info, log_error):
    """Sub-task: Migrate useRef, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useRef'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useRef', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useRef', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_usestate(file_manager, log_info, log_error):
    """Sub-task: Migrate useState, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useState'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useState', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useState', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_reactive(file_manager, log_info, log_error):
    """Sub-task: Migrate reactive, ignoring comments."""
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'reactive'):
                continue
            file.content = JSTooling.remove_import(file.content, 'reactive', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'reactive', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_use_external_listener(file_manager, log_info, log_error):
    """ Changes the imports from useExternalListeners from "@odoo/owl" to "@web/owl2/utils". """
    js_files = JSTooling.get_js_files(file_manager)

    for fileno, file in enumerate(js_files, start=1):
        try:
            if not JSTooling.has_active_usage(file.content, 'useExternalListener'):
                continue
            file.content = JSTooling.remove_import(file.content, 'useExternalListener', '@odoo/owl')
            file.content = JSTooling.add_import(file.content, 'useExternalListener', '@web/owl2/utils')
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)
        file_manager.print_progress(fileno, len(js_files))


def upgrade_tportal(file_manager, log_info, log_error):
    """Sub-task: Migrate t-portal, ignoring comments."""
    files = JSTooling.get_template_files(file_manager)
    if not files:
        return

    reg_t_portal = re.compile(r"\bt-portal(?=\s*=\s*['\"])")

    for fileno, file in enumerate(files, start=1):
        try:
            content = file.path.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            log_error(file.path, f'Upgrade_code: skipping non-utf8 file({e})')
            continue

        if 't-portal' not in content:
            continue

        try:
            content = reg_t_portal.sub('t-custom-portal', content)
            file.content = content
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(files))


def upgrade_t_esc(file_manager, log_info, log_error):
    """Replaces the t-esc directive in xml templates with the t-out directive"""
    files = JSTooling.get_template_files(file_manager)
    if not files:
        return

    reg_t_esc_attr = re.compile(r"\bt-esc(?=\s*=\s*['\"])")
    # matches: <attribute name="t-esc">  /  <attribute name="t-esc"/> /  <attribute remove="1" name="t-esc" />
    reg_att_t_esc = re.compile(r'(<attribute\b[^>]*\bname\s*=\s*(["\']))t-esc(\2)')

    def replace_t_esc(s: str) -> str:
        s = reg_t_esc_attr.sub("t-out", s)
        s = reg_att_t_esc.sub(r"\1t-out\3", s)
        return s

    for fileno, file in enumerate(files, start=1):
        try:
            content = file.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            # For file enterprise/l10n_cl_edi_factoring/template/aec_template.xml
            log_error(file.path, f"Upgrade_code: skipping non-utf8 file({e})")
            continue

        if "t-esc" not in content:
            continue

        try:
            if file.path.name.endswith(".test.js"):
                content = JSTooling.transform_js_string_literals(content, replace_t_esc)
            elif file.path.suffix == ".js":
                content = JSTooling.transform_xml_literals(content, replace_t_esc)
                content = JSTooling.transform_arch_templates(content, replace_t_esc)
            else:  # .xml
                content = replace_t_esc(content)
            file.content = content
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(files))


def upgrade_t_ref(file_manager, log_info, log_error):
    files = JSTooling.get_template_files(file_manager)
    reg_t_ref = re.compile(r'\b(?<!-)t-ref([^=\s]*\s*=)')

    def apply_transformations(text):
        text = reg_t_ref.sub(r't-custom-ref\1', text)
        return text

    for fileno, file in enumerate(files, start=1):
        try:
            raw_content = file.path.read_bytes()
            content = raw_content.decode("utf-8", errors="ignore")

            if file.path.suffix == ".js":
                new_content = JSTooling.transform_xml_literals(content, apply_transformations)
            else:
                new_content = apply_transformations(content)

            if new_content != content:
                file.content = new_content

        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(files))


def upgrade_t_model(file_manager, log_info, log_error):
    files = JSTooling.get_template_files(file_manager)
    reg_t_model = re.compile(r'\b(?<!-)t-model([^=\s]*\s*=)')

    def apply_transformations(text):
        text = reg_t_model.sub(r't-custom-model\1', text)
        return text

    for fileno, file in enumerate(files, start=1):
        try:
            raw_content = file.path.read_bytes()
            content = raw_content.decode("utf-8", errors="ignore")

            if file.path.suffix == ".js":
                new_content = JSTooling.transform_xml_literals(content, apply_transformations)
            else:
                new_content = apply_transformations(content)

            if new_content != content:
                file.content = new_content

        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(files))


WEB_WHITELIST = {
    "web.Breadcrumb.Name": {'breadcrumb'},  # Var above t-call
    "web.CalendarFilterSection.filter": {'filter', 'filterId'},  # dynamic t-call
    "web.CalendarYearPopover.record": {'record'},  # t-for-each above dynamic t-call
    "web.FieldTooltip": {'field', 'debug', 'resModel'},  # JSON stringify context
    "web.ListRenderer.RecordRow": {'record', 'group', 'groupId', '_canSelectRecord'},  # dynamic t-call
    'web.ListRenderer.Rows': {'list'},  # dynamic t-call
    "web.ListRenderer.GroupRow": {'group', 'group_index'},  # dynamic t-call from loop
    "web.ListHeaderTooltip": {'field'},  # JSON stringify context
    "web.Many2ManyBinaryField.attachment_preview": {'file'},  # t-for-each above t-call
    "web.Many2ManyTagsAvatarField.option": {'autoCompleteItemScope'},  # t-slot-scope above dynamic t-call
    "web.NavBar.AppsMenu.Sidebar": {'apps', 'subMenu_index'},  # nested t-calls
    "web.PivotMeasure": {'cell'},  # for each + t-call
    "web.SearchPanelContent": {'section'},  # dynamic t-call
    "web.SearchPanel.Small": {'section'},  # dynamic t-call
    "web.SearchPanel.Category": {'isChildList', 'section', 'values'},  # dynamic t-call
    "web.SearchPanel.FiltersGroup": {'values', 'section', 'group', 'isChildList'},  # dynamic t-call
    "web.SectionMenu": {'subMenu_index', 'apps'},  # dynamic t-call in t-foreach
    "web.SelectMenu.ChoiceItem": {'choice', 'choice_index'},  # dynamic t-call
    "web.SelectMenu.search": {'inputClass'},  # Var above t-call
    "web.EmojiPicker.emoji": {'itemIndex'},  # dynamic t-call in t-foreach
    "web.StatusBarField": {'items'},  # dynamic t-call
    "web.TreeEditor.condition:editable": {'node'},  # Nested inherit
    "web.TreeEditor.condition:readonly": {'node'},  # Nested inherit
    "web.TreeEditor.controls": {'node', 'ancestors', 'parent'},  # Nested inherit
    "web.TreeEditor.connector.value": {'node'},  # Nested inherit
    "web.TreeEditor.condition": {'node'},  # Nested inherit
    "web.TreeEditor.complex_condition": {'node'},  # Nested inherit
}
WEB_EXT_WHITELIST = {
    "web_map.MapRenderer.PinListItems": {'records', 'renderer'},  # dynamic t-call
    'web_map.MapRenderer.PinListContainer': {'renderer'},  # dynamic t-call
    "web_gantt.GanttRenderer.RowHeader": {'row'},  # dynamic t-calls from loops
    "web_gantt.GanttRenderer.RowContent": {'row'},  # dynamic t-calls from loops
    "web_gantt.GanttRenderer.Pill": {'pill', 'row'},  # dynamic t-calls from loops
    "web_gantt.GanttRenderer.GroupPill": {'pill', 'row'},  # dynamic t-calls from loops
    "web_gantt.GanttRenderer.ConnectorCreator": {'pill', 'alignment'},  # dynamic t-calls from loops
    "web_grid.Section": {'row'},  # dynamic t-calls from loops
    "web_grid.Row": {'row', 'section'},  # dynamic t-calls from loops
    "web_grid.AddLine": {'row'},  # dynamic t-calls from loops
    "web_studio.Form.InnerGroup": {'row_index'},  # dynamic t-calls from loops
    'web_studio.ViewEditor.InteractiveEditorProperties.PythonExpressionCheckbox': {'name'},
    "web_studio.ViewEditor.View": {'scope'},  # dynamic t-call
    "web_studio.property.subOptions": {'attribute'},  # dynamic t-call
    "web_studio.property.defaultInput": {'attribute'},  # dynamic t-call
    "web_studio.property.selection": {'attribute'},  # dynamic t-call
    "web_studio.property.domain": {'attribute'},  # dynamic t-call
    "web_studio.property.digits": {'attribute'},  # dynamic t-call
    "web_studio.property.boolean": {'attribute'},  # dynamic t-call
    "web_studio.property.field": {'attribute'},  # dynamic t-call
    "web_studio.property.number": {'attribute'},  # dynamic t-call
    "web_studio.property.string": {'attribute'},  # dynamic t-call
    "web_studio.StudioHomeMenu": {'app_index'},  # xpath on a t-foreach
    "web_studio.ViewEditorSidebar.ApprovalRule": {'rule'},  # dynamic t-call
    "web_gantt.ConnectorStrokeHead": {'xmlAttributes'},  # dynamic t-call
    'web_studio.ViewSelector.ChoiceItemRecursive': {'choice'}  # dynamic t-call
}
MAIL_WHITELIST = {
    "discuss.GifPicker.gif": {'gif_value'},  # for-each above t-call
    "mail.Action.content": {'inMeetingViewCallButtonsFullscreen'},  # Var above t-call
    "mail.ActivityViewCell": {'resId', 'type', 'record'},  # for each + t-call
    "mail.ActivityViewRow": {'resId'},  # for each + t-call
    "mail.Composer.extraActions": {'partitionedActions', 'actionsContainerClass'},  # Var above t-call
    "mail.Composer.moreActions": {'actionsContainerClass'},  # Var above t-call
    "mail.Composer.quickActions": {'partitionedActions', 'actionsContainerClass'},  # Var above t-call
    "mail.Composer.suggestionSpecial": {'option'},  # dynamic t-call
    "mail.Composer.suggestionPartner": {'option'},  # dynamic t-call
    "mail.Composer.suggestionRole": {'option'},  # dynamic t-call
    "mail.Composer.suggestionChannel": {'option'},  # dynamic t-call
    "mail.Composer.suggestionChannelCommand": {'option'},  # dynamic t-call
    "mail.Composer.suggestionCannedResponse": {'option'},  # dynamic t-call
    "mail.Composer.suggestionEmoji": {'option'},  # dynamic t-call
    "mail.MessageSeenIndicatorPopover.card": {'member'},  # for-each above t-call
    "mail.NotificationItem": {'notificationBody'},  # t-slot with name = ... where name is just used for an xpath
    "mail.RottingStatusBarDurationField": {'item'},  # dynamic t-call
    "mail.SubChannelPreview.message": {'message'},  # dynamic t-call
    "mail.ThreadIcon.typing": {'attr'},  # dynamic t-call
}
MISC_WHITELIST = {
    "account.MoveStatusBarSecuredField.ItemLabel": {'item'},  # dynamic t-call
    "account_disallowed_expenses.warning_multi_rate": {'warningParams'},  # dynamic t-call
    'account_fiscal_categories.warning_multi_rate': {'warningParams'},  # dynamic t-call
    "account_fiscal_categories_fleet.warning_missing_fiscal_category": {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_expired_trans': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_premature_trans': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_missing_trans': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_expired_goods': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_premature_goods': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_missing_goods': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_expired_services': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_premature_services': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_missing_services': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_missing_weight': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_missing_unit': {'warningParams'},  # dynamic t-call
    'account_intrastat.intrastat_warning_missing_product': {'warningParams'},  # dynamic t-call
    "account_reports.has_bank_miscellaneous_move_lines": {'warningParams'},  # dynamic t-call
    "account_reports.journal_balance": {'warningParams'},  # dynamic t-call
    "account_reports.inconsistent_statement_warning": {'warningParams'},  # dynamic t-call
    "account_saft.company_data_warning": {'warningParams'},  # dynamic t-call
    "appointment.AppointmentTemplateCard": {'templateElemClass'},  # didn't check
    "auth_passkey_portal.rename": {'oldname'},  # t-attf-value
    "crm.ColumnProgress": {'bar'},  # Nested inherit
    "discuss.ChannelInvitation-selectableItem": {"selectablePartner"},  # nested t-call
    "documents.SearchPanel.Category": {'isChildList'},  # dynamic t-call
    "documents.SearchPanel.Category.Small": {'value'},  # Nested t-call/inherit
    "equity.CapTableCell": {'cell'},  # dynamic t-call
    "event.mailTemplateReferenceField": {'relation'},  # Nested t-inherits
    "helpdesk_timesheet.TimesheetTimerInlineForm": {'data'},  # Nested t-call/inherits
    "hr.DepartmentChart.Department": {'dept'},  # dynamic t-call
    "html_builder.invisibleSnippetEntry": {'entry', 'toggleElementVisibility'},  # t- call-context
    "html_builder.ShadowOptionItem": {'onClick'},  # dynamic t-call
    "html_editor.ExternalImage": {'record'},  # nested t-inherit / t-call
    "hr_calendar.CalendarCommonRenderer.buttonWorklocation": {'multiCalendar'},  # Nested t-inherits with a xpath t-call
    "hr_calendar.AttendeeCalendarCommonPopover.body": {'slot'},  # dynamic t-call
    "hr_payroll.ActionableWarningLine": {'warning'},  # Didn't check
    "hr_skills.SkillsListRenderer.Rows": {'list'},  # dynamic t-call I guess
    "lunch.LunchDashboardOrder": {'currency'},  # Var above t-call
    'l10n_ae_faf.company_data_warning': {'warningParams'},  # dynamic t-call
    'l10n_be_reports.partner_vat_listing_missing_partners_warning': {'warningParams'},  # dynamic t-call
    'l10n_be_reports.duplicate_partner_vat': {'warningParams'},  # dynamic t-call
    'l10n_be_reports.tax_report_warning_checks': {'warningParams'},  # dynamic t-call
    'l10n_ee_reports.kmd_inf_listing_missing_partners_warning': {'warningParams'},  # dynamic t-call
    'l10n_fr_reports.tax_report_warning_checks': {'warningParams'},  # dynamic t-call
    'l10n_in_reports.invalid_intra_state_warning': {'warningParams'},  # dynamic t-call
    'l10n_in_reports.invalid_inter_state_warning': {'warningParams'},  # dynamic t-call
    'l10n_in_reports.missing_hsn_warning': {'warningParams'},  # dynamic t-call
    'l10n_in_reports.invalid_uqc_code_warning': {'warningParams'},  # dynamic t-call
    'l10n_in_reports.unlinked_reversed_moves_warning': {'warningParams'},  # dynamic t-call
    'l10n_in_reports.missing_pan_tds_tcs_warning': {'warningParams'},  # dynamic t-call
    'l10n_lu_reports.annual_tax_report_warning_checks': {'warningParams'},  # dynamic t-call
    'l10n_ng_reports.tax_report_period_check': {'warningParams'},  # dynamic t-call
    'l10n_ph_reports.warning_partner_without_vat': {'warningParams'},  # dynamic t-call
    'l10n_tr_reports.waiting_nilvera_status_warning': {'warningParams'},  # dynamic t-call
    'l10n_uk_reports_cis.warning_cis_unregistered_partner': {'warningParams'},  # dynamic t-call
    "mrp_workorder.ProductCatalogKanbanRenderer": {'groupOrRecord'},  # Nested t-call or inherit
    "planning.PlanningCalendarCommonPopover.body": {'slot'},  # dynamic t-calls from loops
    "point_of_sale.ScenarioCard": {'item'},  # dynamic t-call
    "pos_blackbox_be.CashierClockButtons": {'employee', 'isCachier'},  # dynamic t-call
    "pos_event.QuestionInputs": {'questions', 'stateObject'},  # Var above t-call
    "pos.floor_screen_shape": {'shape'},  # didn't check
    "pos_restaurant.floor_screen_element": {'element', 'kanbanMode'},  # for each + t-call
    "pos_restaurant_appointment.PosResAppointmentListRenderer.Rows": {'list'},  # Nested t-inherit
    "product_matrix.matrix": {'format'},  # Var passed via t-set above t-call
    "product_matrix.extra_price": {'format'},  # nested t-call
    "project.NotebookTaskListRenderer.Rows": {'list'},  # dynamic t-call
    "project.DependOnIdsListRowsRenderer": {'list'},  # dynamic t-call
    "project_enterprise.TaskGanttRenderer.ColoredCellBorder": {'column'},  # Nested t-call or inherit
    "sale.ListRenderer.RecordRow": {'record', 'column', 'hasDeleteButton'},  # Nested t-inherits
    "sale_management.ListRenderer.RecordRow": {'record'},  # Nested t-inherits
    "composition_button": {'record'},  # Weird case where we use a tname to xpath
    "sale_timesheet_enterprise.TimesheetTimerInlineForm": {'data'},  # Nested t-call or inherit
    "slide.quiz.answer.line": {'answer'},  # dynamic t-call
    "social.AccountsStatsValue": {'socialAccount'},  # dynamic t-call
    "social.MentionsTemplate": {'option'},  # Nested t-call or inherit
    "stock.PickingLockedStatusBarField.ItemLabel": {'item'},  # dynamic t-call
    "stock_barcode.LineQuantity": {'lowerButtons'},  # dynamic t-call
    "stock_barcode.LineTitle": {'upperButtons'},  # dynamic t-call
    "views.ViewButtonTooltip": {'debug', 'button', 'model'},  # JSON stringify context
    "website.dialog.addFont.singlePreview": {'previewFontName'},  # Nested t-call
    'website.dialog.addFont.preview': {'previewFontName'},  # Recursive t-call
    "website.form_field": {'fieldTypeClasses', 'form_checkbox'},  # dynamic t-call
    "website.form_radio": {'record_index', 'record'},  # dynamic t-calls from loops
    "website.form_checkbox": {'record_index', 'record'},  # dynamic t-calls from loops
    "website_sale.DynamicSnippetProductsOption": {'filteredTemplates', 'isSingleMode'},  # dynamic t-calls from loops
}


def upgrade_parametric_tcall(file_manager, log_info, log_error):
    """Converts parametric t-call children (t-set nodes) into inline t-call attributes.
    """
    xml_files = JSTooling.get_xml_files(file_manager)
    for fileno, file in enumerate(xml_files, start=1):
        if not file.content or not file.content.strip():
            continue
        try:
            res, warnings = update_template(
                file.path._str, file.content, [], None, None,
                apply_tcall_param=True, apply_this=False,
            )
            if res != file.content:
                file.content = res
            for warning in warnings:
                print(warning)  # noqa: T201
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(xml_files))


def upgrade_this(file_manager, log_info, log_error, targets=[]):
    """ Adds `this.` to all .xml templates variables coming from components
        (in other words to all variables not defined in the template with t-set, t-foreach...)

    Args:
        targets (array[string]) : Use to target specific modules.
            eg. "web" will target "web", "web_editor"...
            Leave empty to run on entire codebase
    """
    # Iteration 1: search for component template names in js files
    component_templates = list()
    template_re = re.compile(r"""static\s+template\s*=\s*["']([^'"]+)["']""")
    js_files = JSTooling.get_js_files(file_manager)
    for file in js_files:
        content = file.content
        for template_name in template_re.findall(content):
            component_templates.append(template_name)

    # Iteration 2: Build template metadata dicts in VariableAggregator (variable, t-call vars, inheritance chain...)
    xml_files = JSTooling.get_xml_files(file_manager)
    aggregator = VariableAggregator(component_templates)
    for _, file in enumerate(xml_files, start=1):
        def callback(tree):
            aggregator.link_templates(tree, file.path._str)
            aggregator.aggregate_inside_vars(tree)
            aggregator.aggregate_call_vars(tree)

        if not file.content or not file.content.strip():
            continue

        update_etree(file.content, callback)
    aggregator.map_inherits_and_calls()

    # Merge white list of vars with vars parsed by aggregator
    white_vars = MAIL_WHITELIST | WEB_WHITELIST | WEB_EXT_WHITELIST | MISC_WHITELIST
    d1, d2 = aggregator.all_vars, white_vars
    merged = {k: d1.get(k, set()) | d2.get(k, set()) for k in d1.keys() | d2.keys()}

    aggregator.all_vars = merged

    # Iteration 3: Update templates
    for fileno, file in enumerate(xml_files, start=1):
        try:
            res, warnings = update_template(file.path._str, file.content, targets, aggregator, EXCLUDED_TEMPLATES)
            file.content = res
            for warning in warnings:
                print(warning)  # noqa: T201
        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)


def upgrade_this_in_js(file_manager, log_info, log_error, targets=[]):
    """ Adds `this.` to all .js templates variables coming from components
        (in other words to all variables not defined in the template with t-set, t-foreach...)

    Args:
        targets (array[string]) : Use to target specific modules.
            eg. "web" will target "web", "web_editor"...
            Leave empty to run on entire codebase
    """
    js_files = JSTooling.get_js_files(file_manager, include_test_files=True)
    pattern = re.compile(r"(\bxml\s*`)(.*?)(`)", re.DOTALL)
    for _, file in enumerate(js_files, start=1):
        if targets and not any(
            f"/{module}/" in file.path._str or f"/{module}_" in file.path._str
            for module in targets
        ):
            continue
        try:
            def process_match(match):
                prefix = match.group(1)   # The "xml`" part
                raw_xml = match.group(2)  # The content inside backticks
                suffix = match.group(3)   # The closing "`"

                if re.search(r'\$\{', raw_xml):
                    return match.group(0)  # Just skip test with dynamic JS interpolation

                wrapped_xml = f"<t t-name='xyz'>{raw_xml}</t>"

                aggregator = VariableAggregator(is_testing=True)
                processed_wrapped, _ = update_template("", wrapped_xml, {}, aggregator, EXCLUDED_TEMPLATES)

                inner_xml = re.sub(r'^<[^>]+>', '', processed_wrapped)
                inner_xml = re.sub(r'</[^>]+>$', '', inner_xml)

                return f"{prefix}{inner_xml}{suffix}"

            new_content = pattern.sub(process_match, file.content)

            if new_content != file.content:
                file.content = new_content

        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)


def upgrade_t_slot(file_manager, log_info, log_error):
    files = JSTooling.get_template_files(file_manager)
    reg_t_slot = re.compile(r'\b(?<!-)t-slot(\s*=)')

    def apply_transformations(text):
        text = reg_t_slot.sub(r't-call-slot\1', text)
        return text

    for fileno, file in enumerate(files, start=1):
        try:
            raw_content = file.path.read_bytes()
            content = raw_content.decode("utf-8", errors="ignore")

            if file.path.suffix == ".js":
                new_content = JSTooling.transform_xml_literals(content, apply_transformations)
            else:
                new_content = apply_transformations(content)

            if new_content != content:
                file.content = new_content

        except Exception as e:  # noqa: BLE001
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(files))


def upgrade(file_manager) -> str:
    """Main upgrade_code entry point."""
    collector = MigrationCollector(file_manager)

    collector.run_sub("Migrating useEffect", upgrade_useeffect)
    collector.run_sub("Migrating onWillRender", upgrade_onwillrender)
    collector.run_sub("Migrating onRendered", upgrade_onrendered)
    collector.run_sub("Migrating useComponent", upgrade_usecomponent)
    collector.run_sub("Migrating useEnv", upgrade_useenv)
    collector.run_sub("Migrating useSubEnv", upgrade_usesubenv)
    collector.run_sub("Migrating useChildSubEnv", upgrade_usechildsubenv)
    collector.run_sub("Migrating useRef", upgrade_useref)
    collector.run_sub("Migrating useState", upgrade_usestate)
    collector.run_sub("Migrating reactive", upgrade_reactive)
    collector.run_sub("Migrating useExternalListener", upgrade_use_external_listener)
    collector.run_sub("Migrating t-portal", upgrade_tportal)
    collector.run_sub("Migrating t-esc", upgrade_t_esc)
    collector.run_sub("Migrating t-ref", upgrade_t_ref)
    collector.run_sub("Migrating t-model", upgrade_t_model)
    collector.run_sub("Migrating this. in xml templates", upgrade_this, targets=[])
    collector.run_sub("Migrating this. in test.js xml fragments", upgrade_this_in_js, targets=[])
    collector.run_sub("Migrating t-slot", upgrade_t_slot)
    collector.run_sub("Migrating parametric t-call", upgrade_parametric_tcall)

    collector.finalize()
