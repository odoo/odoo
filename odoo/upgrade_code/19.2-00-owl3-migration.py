import re


EXCLUDED_PATH = (
    'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
    'iot_drivers/static/src/',
    'web/static/src/owl2',
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
        pattern = r'(xml\s*`)(.*?)(`)'

        def replacer(match):
            prefix = match.group(1)
            xml_content = match.group(2)
            suffix = match.group(3)
            return f"{prefix}{transform_func(xml_content)}{suffix}"

        return re.sub(pattern, replacer, content, flags=re.DOTALL)

    @staticmethod
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

    collector.finalize()
