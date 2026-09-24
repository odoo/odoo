"""
Migrate the calendar view customizations to FullCalendar v7.

This script renames, in the static files, the FullCalendar options renamed in
v7, e.g. `eventClassNames` to `eventClass`, and reports the APIs removed in v7
(`updateSize()`, `windowResize`...).

Usage: odoo-bin upgrade_code --script fullcalendar7 --addons-path=<your addons>
"""
import re

EXCLUDED_PATH = (
    '/static/lib/',
    '/node_modules/',
)

# FullCalendar options renamed in v7.
OPTIONS = {
    'eventClassNames': 'eventClass',
    'dayCellClassNames': 'dayCellClass',
    'dayHeaderClassNames': 'dayHeaderClass',
    'slotLaneClassNames': 'slotLaneClass',
    'slotLabelClassNames': 'slotHeaderClass',
    'slotLabelContent': 'slotHeaderContent',
    'slotLabelFormat': 'slotHeaderFormat',
    'slotLabelDidMount': 'slotHeaderDidMount',
    'allDayClassNames': 'allDayHeaderClass',
    'allDayContent': 'allDayHeaderContent',
    'allDayDidMount': 'allDayHeaderDidMount',
    'moreLinkClassNames': 'moreLinkClass',
    'viewClassNames': 'viewClass',
    'noEventsClassNames': 'noEventsClass',
}

# Properties renamed in v7.
PROPERTIES = {
    'fcSeg': 'fcEventRange',
}

# Removed FullCalendar APIs, only reported in the files using FullCalendar.
REPORTED_API = {
    r'\.updateSize\(\)': "removed, FullCalendar v7 resizes by itself",
    r'\b(handleWindowResize|windowResize|windowResizeDelay)\b': "removed, FullCalendar v7 resizes by itself",
    r'\.currentData\b': "internal, use `calendar.getOption()`",
}

# only the option keys: Odoo methods of the same name (e.g. `eventClassNames()`) are kept
OPTION_RES = [(re.compile(r'\b' + old + r'(?=\s*:)'), new) for old, new in OPTIONS.items()]
PROPERTY_RES = [(re.compile(r'\b' + old + r'\b'), new) for old, new in PROPERTIES.items()]


def get_files(file_manager, extensions):
    return [
        file for file in file_manager
        if '/static/' in str(file.path)
        and file.path.suffix in extensions
        and not any(excluded in str(file.path) for excluded in EXCLUDED_PATH)
    ]


def rename(content, renames):
    for regex, new in renames:
        content = regex.sub(new, content)
    return content


def upgrade_options(file_manager, log):
    files = get_files(file_manager, ('.js',))
    for fileno, file in enumerate(files, start=1):
        file.content = rename(file.content, OPTION_RES + PROPERTY_RES)
        file_manager.print_progress(fileno, len(files))


USES_FULLCALENDAR_RE = re.compile(r'FullCalendar|useFullCalendar|\bfc\(\)')


def report_removed(file_manager, log):
    reported_api = [(re.compile(pattern), hint) for pattern, hint in REPORTED_API.items()]
    for file in get_files(file_manager, ('.js', '.xml')):
        if not USES_FULLCALENDAR_RE.search(file.content):
            continue
        path = file.path.relative_to(file.addon.parent)
        for lineno, line in enumerate(file.content.splitlines(), start=1):
            for regex, hint in reported_api:
                if match := regex.search(line):
                    log(f"{path}:{lineno}: `{match[0]}`: {hint}")


def upgrade(file_manager):
    reports = []
    for name, func in (
        ("Renaming the FullCalendar options", upgrade_options),
        ("To adapt by hand", report_removed),
    ):
        logs = []
        modified_before = sum(1 for file in file_manager if file.dirty)
        func(file_manager, logs.append)
        modified = sum(1 for file in file_manager if file.dirty) - modified_before
        report = [f"\n{name}", "-" * 40, *(f"  {log}" for log in logs)]
        if func is not report_removed:
            report.append(f"  Files modified: {modified}")
        reports.append("\n".join(report))
    file_manager.add_to_summary("\n".join(reports))
