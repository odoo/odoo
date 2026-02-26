import re


EXCLUDED_PATH = (
    'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
    'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.xml',
    'iot_drivers/static/src/',
    'web/static/src/owl2',
    'addons/web/static/lib/owl/owl.js',
)

CHECKSUM_FILES = (
    'pos_blackbox_be/static/src/pos/overrides/navbar/navbar.xml',
    'l10n_eu_iot_scale_cert/controllers/checksum.py',
    'l10n_eu_iot_scale_cert/static/src/app/utils/scale/certified_iot_scale.js',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/scale_screen/certified_scale_screen.js',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/scale_screen/certified_scale_screen.xml',
    'l10n_eu_iot_scale_cert/receipt/pos_order_receipt.xml',
    'l10n_eu_iot_scale_cert/static/src/pos_overrides/components/orderline/certified_orderline.xml',
    'iot_drivers/iot_handlers/drivers/serial_scale_driver.py',
)


class JSTooling:
    @staticmethod
    def is_commented(content: str, position: int) -> bool:
        """Checks if the word at the given position is on a commented line.

        Args:
            content: The full file content.
            position: The index of the word to check.

        Returns:
            True if the line starts with // before the position.
        """
        # We look back to the start of the current line
        line_start = content.rfind('\n', 0, position) + 1
        line_text = content[line_start:position]
        return '//' in line_text

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
            return f"{prefix}{transform_func(xml_content)}{suffix}"

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

    def replace_usage(content: str, old_name: str, new_name: str) -> str:
        """Replaces variable usage using word boundaries.

        Args:
            content: The file content.
            old_name: Original variable name.
            new_name: New variable name.
        Returns:
            The updated content.
        """
        return re.sub(rf'\b{old_name}\b', new_name, content)

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
    def get_js_files(file_manager):
        path_pattern = re.compile('|'.join(EXCLUDED_PATH))
        return [
            file for file in file_manager
            if '/static/src/' in file.path._str
            and file.path.suffix == '.js'
            and not re.search(path_pattern, file.path._str)
        ]

    def get_template_files(file_manager):
        excluded_path_pattern = re.compile('|'.join(EXCLUDED_PATH + CHECKSUM_FILES))
        return [
            file for file in file_manager
            if '/static/src/' in file.path._str
            and file.path.suffix in ['.xml', '.js']
            and not re.search(excluded_path_pattern, file.path._str)
        ]


class MigrationCollector:
    """Collects logs from multiple sub-functions and pushes them to FileManager."""

    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.reports = []

    def run_sub(self, name: str, func) -> None:
        modified_before = sum(1 for f in self.file_manager if f.dirty)
        errors = []
        infos = []

        def log_info(msg):
            infos.append(msg)

        def log_error(path, err):
            errors.append(f"  ❌ {path}: {err}")

        func(self.file_manager, log_info, log_error)

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
    path_pattern = re.compile('|'.join(EXCLUDED_PATH))
    files = [
        file for file in file_manager
        if '/static/src/' in file.path._str
        and file.path.suffix in ['.xml', '.js']
        and not re.search(path_pattern, file.path._str)
    ]
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
    excluded_path_pattern = re.compile('|'.join(EXCLUDED_PATH + CHECKSUM_FILES))
    files = [
        file for file in file_manager
        if file.path.suffix in ['.xml', '.js'] and not re.search(excluded_path_pattern, file.path._str)
    ]
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

    collector.finalize()
