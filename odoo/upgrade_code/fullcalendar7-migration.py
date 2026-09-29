"""
Migrate the calendar view customizations to FullCalendar v7 and its Odoo theme.

FullCalendar v7 no longer renders the `fc-*` class names of v6 (its own classes
are hashed), and the calendar view now styles its elements with the Odoo theme
(`web/static/src/views/calendar/calendar_theme.js`). This script renames, in the
static files (js, xml, scss, css):

- the FullCalendar v6 classes to the classes of the Odoo theme, e.g.
  `fc-daygrid-day` to `o_calendar_day`, `fc-day-today` to `[aria-current=date]`;
- the `o_cw_*` classes and the `--o-cw-*` variables to the `o_calendar_*` and
  `--o-calendar-*` ones;
- the FullCalendar v6 CSS variables to the ones of the Odoo theme palette;
- the FullCalendar options renamed in v7, e.g. `eventClassNames` to `eventClass`.

What can't be renamed safely is reported: the v6 classes without equivalent, and
the APIs removed in v7 (`updateSize()`, `windowResize`, luxon format strings...).

Usage: odoo-bin upgrade_code --script fullcalendar7 --addons-path=<your addons>
"""
import re

EXCLUDED_PATH = (
    '/static/lib/',
    '/node_modules/',
)

# FullCalendar v6 class -> class (or selector, for a leading `.`) of the Odoo theme.
CLASSES = {
    'fc-bg-event': 'o_calendar_bg_event',
    'fc-bg': 'o_calendar_event_bg',
    'fc-time': 'o_calendar_event_time',
    'fc-col-header-row': 'o_calendar_header_row',
    'fc-col-header-cell': 'o_calendar_header_cell',
    'fc-col-header-cell-cushion': 'o_calendar_header_cell_inner',
    'fc-daygrid-row': 'o_calendar_day_row',
    'fc-daygrid-day': 'o_calendar_day',
    'fc-day': 'o_calendar_day',
    'fc-day-other': 'o_calendar_day_other',
    'fc-daygrid-day-top': 'o_calendar_day_top',
    'fc-daygrid-day-number': 'o_calendar_day_top_number',
    'fc-daygrid-day-events': 'o_calendar_day_events',
    'fc-daygrid-week-number': 'o_calendar_week_number',
    'fc-week-number': 'o_calendar_week_number_header',
    'fc-timegrid-col': 'o_calendar_lane',
    'fc-timegrid-slot-lane': 'o_calendar_time_slot',
    'fc-timegrid-slot-label': 'o_calendar_time_slot_label',
    'fc-timegrid-slot-label-cushion': 'o_calendar_time_slot_label_inner',
    'fc-timegrid-slot-minor': 'o_calendar_time_slot_minor',
    'fc-timegrid-divider': 'o_calendar_all_day_divider',
    'fc-timegrid-now-indicator-line': 'o_calendar_now_line',
    'fc-event': 'o_calendar_event',
    'fc-event-main': 'o_calendar_event_main',
    'fc-event-start': 'o_calendar_event_start',
    'fc-event-end': 'o_calendar_event_end',
    'fc-event-mirror': 'o_calendar_event_mirror',
    'fc-event-dragging': 'o_calendar_event_dragging',
    'fc-daygrid-event': 'o_calendar_row_event',
    'fc-daygrid-block-event': 'o_calendar_row_event',
    'fc-timegrid-event': 'o_calendar_column_event',
    'fc-event-resizer': 'o_calendar_resizer',
    'fc-event-resizer-start': 'o_calendar_resizer_start',
    'fc-event-resizer-end': 'o_calendar_resizer_end',
    'fc-more-link': 'o_calendar_more_link',
    'fc-daygrid-more-link': 'o_calendar_more_link',
    'fc-timegrid-more-link': 'o_calendar_more_link',
    'fc-popover': 'o_calendar_more_popover',
    'fc-more-popover': 'o_calendar_more_popover',
    'fc-popover-close': 'o_calendar_more_popover_close',
    'fc-highlight': 'o_calendar_highlight',
    'fc-non-business': 'o_calendar_non_business',
    'fc-view': 'o_calendar_fc_view',
    'fc-dayGridYear-view': 'o_calendar_fc_view_multiMonthYear',
    'fc-month': 'o_calendar_month',
    'o-fc-week': 'o_calendar_week',
    'o-fc-week-header': 'o_calendar_week_header',
}

# FullCalendar v6 class only used in selectors -> attribute selector rendered by v7.
SELECTORS = {
    '.fc-day-today': '[aria-current=date]',
    '.fc-day-disabled': '[aria-disabled]',
}

VIEW_CLASS_RE = re.compile(r'(?<![\w-])fc-(dayGridMonth|dayGridWeek|dayGridDay|timeGridWeek|timeGridDay|multiMonthYear|listWeek)-view(?![\w-])')

VARIABLES = {
    '--o-cw-bg': '--o-calendar-day-number-bg',
    '--o-cw-color': '--o-calendar-day-number-color',
    '--o-cw-border-color': '--o-calendar-border',
    '--o-bg-opacity': '--o-calendar-bg-opacity',
    '--o-overlay-opacity': '--o-calendar-overlay-opacity',
    '--o-event-bg--subtle-rgb': '--o-calendar-event-bg-subtle-rgb',
    '--o-event-bg': '--o-calendar-event-bg',
    '--fc-event-bg-color': '--fc-event-color',
    '--fc-bg-event-color': '--fc-event-color',
    '--fc-event-text-color': '--fc-event-contrast-color',
    '--fc-event-border-color': '--o-calendar-event-border-color',
    '--fc-border-color': '--o-calendar-border',
    '--fc-page-bg-color': '--o-calendar-background',
    '--fc-non-business-color': '--o-calendar-non-business',
    '--fc-highlight-color': '--o-calendar-highlight',
    '--fc-neutral-bg-color': '--o-calendar-neutral',
    '--fc-today-bg-color': '--o-calendar-today',
    '--fc-timegrid-divider-size': '--o-calendar-divider-size',
}

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

# Removed without a direct equivalent: reported, to be adapted by hand.
REPORTED = {
    r'(?<![\w-])fc-day-(sun|mon|tue|wed|thu|fri|sat|past|future|today|disabled)(?![\w-])': "use `[data-date]`, `[aria-current=date]`, `[aria-disabled]` or the `dayCellClass` info instead",
    r'(?<![\w-])fc-(scrollgrid|daygrid-body|timegrid-body|timegrid-axis|col-header|month-container|has-event|readonly-year-view|widget-[a-z]+|daygrid-day-frame|daygrid-day-bg|timegrid-slot|toolbar[a-z-]*)(?![\w-])': "not rendered anymore, target the Odoo theme classes",
    r'--fc-timegrid-divider-background': "use the `.o_calendar_all_day_divider` element",
}

# Removed FullCalendar APIs, only reported in the files using FullCalendar.
REPORTED_API = {
    r'\.updateSize\(\)': "removed, FullCalendar v7 resizes by itself",
    r'\b(handleWindowResize|windowResize|windowResizeDelay)\b': "removed, FullCalendar v7 resizes by itself",
    r'\.currentData\b': "internal, use `calendar.getOption()`",
    r'\b(dayHeaderFormat|titleFormat|eventTimeFormat|slotHeaderFormat|slotLabelFormat)\s*:\s*["\'`]': "luxon format strings aren't supported anymore, use Intl options",
}


def word_re(name):
    return re.compile(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])')


CLASS_RES = [(word_re(old), new) for old, new in sorted(CLASSES.items(), key=lambda item: -len(item[0]))]
VARIABLE_RES = [(word_re(old), new) for old, new in sorted(VARIABLES.items(), key=lambda item: -len(item[0]))]
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


def upgrade_classes(file_manager, log):
    files = get_files(file_manager, ('.js', '.xml', '.scss', '.css'))
    for fileno, file in enumerate(files, start=1):
        content = file.content
        for old, new in SELECTORS.items():
            content = re.sub(re.escape(old) + r'(?![\w-])', new, content)
        content = VIEW_CLASS_RE.sub(r'o_calendar_fc_view_\1', content)
        content = rename(content, CLASS_RES)
        content = re.sub(r'(?<![\w-])o_cw_', 'o_calendar_', content)
        file.content = content
        file_manager.print_progress(fileno, len(files))


def upgrade_variables(file_manager, log):
    files = get_files(file_manager, ('.js', '.xml', '.scss', '.css'))
    for fileno, file in enumerate(files, start=1):
        content = rename(file.content, VARIABLE_RES)
        file.content = re.sub(r'(?<![\w-])--o-cw-', '--o-calendar-', content)
        file_manager.print_progress(fileno, len(files))


def upgrade_options(file_manager, log):
    files = get_files(file_manager, ('.js',))
    for fileno, file in enumerate(files, start=1):
        file.content = rename(file.content, OPTION_RES + PROPERTY_RES)
        file_manager.print_progress(fileno, len(files))


USES_FULLCALENDAR_RE = re.compile(r'FullCalendar|useFullCalendar|\bfc\(\)')


def report_removed(file_manager, log):
    reported = [(re.compile(pattern), hint) for pattern, hint in REPORTED.items()]
    reported_api = [(re.compile(pattern), hint) for pattern, hint in REPORTED_API.items()]
    for file in get_files(file_manager, ('.js', '.xml', '.scss', '.css')):
        checks = reported + (reported_api if USES_FULLCALENDAR_RE.search(file.content) else [])
        path = file.path.relative_to(file.addon.parent)
        for lineno, line in enumerate(file.content.splitlines(), start=1):
            for regex, hint in checks:
                if match := regex.search(line):
                    log(f"{path}:{lineno}: `{match[0]}`: {hint}")


def upgrade(file_manager):
    reports = []
    for name, func in (
        ("Renaming the calendar classes", upgrade_classes),
        ("Renaming the calendar CSS variables", upgrade_variables),
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
