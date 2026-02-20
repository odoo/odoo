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
THIS_TARGETS = ["account"]


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
        "sale.ListRenderer.RecordRow": {'record'},  # nested inherits under dynamic t-call
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
            file.content = update_template(file.path._str, file.content, THIS_TARGETS, aggregator)
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

                processed_wrapped = update_template("", wrapped_xml, {}, {}, [])

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
