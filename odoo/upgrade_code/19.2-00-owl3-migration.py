import re
import sys
import os

# Get the folder containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Force Python to look in this folder for imports
if current_dir not in sys.path:
    sys.path.append(current_dir)

from tools_js_expressions import update_template, aggregate_vars, replace_x_path_only

EXCLUDED_FILES = (
    'addons/spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
    'addons/web/static/lib/owl/owl.js',
    'addons/web/static/src/owl2/utils.js',
    'pos_blackbox_be/static/src/pos/overrides/navbar/navbar.xml',
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
    def has_active_usage(content: str, word: str) -> bool:
        """Checks if a word is used outside of a comment line.

        Args:
            content: The file content.
            word: The word to look for (e.g., 'useEffect').

        Returns:
            True if at least one usage is not commented out.
        """
        for match in re.finditer(rf'\b{word}\b', content):
            if not JSTooling.is_commented(content, match.start()):
                return True
        return False

    @staticmethod
    def replace_usage(content: str, old_name: str, new_name: str) -> str:
        """Replaces usage ONLY if the line is not a comment.

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
    def clean_whitespace(content: str) -> str:
        """Removes trailing whitespace and lines containing only spaces.

        Args:
            content: The file content.

        Returns:
            Cleaned content.
        """
        # Delete spaces on lines that only contain spaces
        content = re.sub(r'^[ \t]+$', '', content, flags=re.MULTILINE)
        # Delete trailing whitespace at the end of lines
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
        return content


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


def upgrade_this(file_manager, log_info, log_error):

    web_files = [
        f for f in file_manager
        if 'addons/web/static/src' in f.path._str
        and f.path.suffix == '.xml'
        and not any(f.path._str.endswith(p) for p in EXCLUDED_FILES)
    ]

    # Step 1: Gather all variables in the web module
    outside_vars = {
        "mail.Composer.quickActions": {'partitionedActions'},
        "web.Breadcrumb.Name": {'breadcrumb'},
        "web.SearchPanel.Category": {'section'}
    }  # vars defined under t-call
    inside_vars = {} # vars defined inside template, eg. using t-set

    for fileno, file in enumerate(web_files, start=1):
        aggregate_vars(file.content, outside_vars, inside_vars)

    # Step 2: Add this. to all non local template vars (except those coming from external t-call)
    for fileno, file in enumerate(web_files, start=1):
        try:
            file.content = update_template(file.content, outside_vars, inside_vars)
        except Exception as e:
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(web_files))

    # Step 3: Modify x-path targetting web files we might have modified above
    INHERIT_PATTERN = re.compile(r't-inherit=["\']web\..*?["\']')  # Matches t-inherit="web.xxxxx
    all_files = [
        f for f in file_manager
        if 'static/src/' in f.path._str
        and f.path.suffix == '.xml'
        and not any(f.path._str.endswith(p) for p in EXCLUDED_FILES)
    ]

    for fileno, file in enumerate(all_files, start=1):
        try:
            if INHERIT_PATTERN.search(file.content):
                file.content = replace_x_path_only(file.content, inside_vars)

        except Exception as e:
            log_error(file.path, e)

        file_manager.print_progress(fileno, len(web_files))


def upgrade(file_manager) -> str:
    """Main entry point called by Odoo."""
    collector = MigrationCollector()

    collector.run_sub("Migrating this.", upgrade_this, file_manager)

    return collector.get_final_logs()
