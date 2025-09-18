# Directory Map

> **231 directories** | Maps directory → layer + responsibility
>
> Layers (Feature-Sliced Design): shared → entities → features → widgets → pages

| Directory | Layer | Files | Lines | Primary Responsibility |
|-----------|-------|------:|------:|----------------------|
| `boot/` | misc | 2 | 85 | Entry point that launches the web client (replaced in enterprise) |
| `components/` | features | 3 | 293 | Reusable OWL UI components (pickers, dropdowns, editors, file handling) |
| `components/action_swiper/` | features | 1 | 250 | Touch swipe component that triggers actions on left/right swipe gestures |
| `components/autocomplete/` | features | 1 | 557 | Generic autocomplete dropdown with multi-source results, keyboard navigation,... |
| `components/barcode/` | features | 4 | 689 | BarcodeDetector polyfill built on ZXing for browsers without native support |
| `components/checkbox/` | features | 1 | 110 | Accessible checkbox component with label slot and hotkey support |
| `components/code_editor/` | features | 1 | 195 | Ace-based code editor component with syntax highlighting and theme support |
| `components/color_picker/` | features | 1 | 459 | Full-featured color picker with preset palette, custom colors, and gradient s... |
| `components/color_picker/custom_color_picker/` | features | 1 | 766 | HSL/RGB color picker with canvas gradient, sliders, and hex input |
| `components/color_picker/tabs/` | features | 2 | 80 | Color picker tab for custom color input with gradient support |
| `components/colorlist/` | features | 1 | 75 | Expandable color swatch picker for selecting from predefined Odoo color indices |
| `components/copy_button/` | features | 1 | 52 | Clipboard copy button with success tooltip feedback |
| `components/datetime/` | features | 5 | 1,516 | Date/time text input component that opens a DateTimePicker popover |
| `components/domain_selector/` | features | 3 | 275 | Visual domain builder that converts between string domains and tree editors |
| `components/domain_selector_dialog/` | features | 1 | 120 | Modal dialog for editing and validating an Odoo domain filter |
| `components/dropdown/` | features | 6 | 650 | Collapsible accordion panel with animated expand/collapse transitions |
| `components/dropdown/_behaviours/` | features | 3 | 276 | Hook that registers a dropdown within a DropdownGroup and tracks group open s... |
| `components/dropzone/` | features | 2 | 148 | Visual drop target overlay that tracks drag enter/leave and fires onDrop |
| `components/emoji_picker/` | features | 2 | 36,741 | Emoji data (generated) and picker UI with search and categories |
| `components/errors/` | features | 2 | 444 | Error dialog components for RPC, client, network, and validation errors |
| `components/expression_editor/` | features | 2 | 147 | Visual tree-based editor for Python expressions with field path selection |
| `components/expression_editor_dialog/` | features | 1 | 92 | Modal dialog for editing Python expressions with validation preview |
| `components/file_input/` | features | 1 | 134 | Customizable file upload input with route-based server upload and multi-file ... |
| `components/file_upload/` | features | 3 | 96 | Progress bar with cancel button for active file uploads |
| `components/file_viewer/` | features | 3 | 469 | FileModelMixin providing URL routing and type detection for viewable file att... |
| `components/ir_ui_view_code_editor/` | features | 1 | 95 | Extended code editor that highlights invalid XPath locators in ir.ui.view arch |
| `components/model_field_selector/` | features | 2 | 487 | Field path selector with breadcrumb display and popover field browser |
| `components/model_selector/` | features | 1 | 113 | Autocomplete component for searching and selecting Odoo model names |
| `components/notebook/` | features | 1 | 198 | Tabbed notebook component that renders one page at a time with tab navigation |
| `components/pager/` | features | 2 | 280 | Pagination component with prev/next navigation and editable page range input |
| `components/record_selectors/` | features | 5 | 423 | Base class for record selector components with display name loading infrastru... |
| `components/resizable_panel/` | features | 1 | 169 | Side panel component with drag handle for interactive width resizing |
| `components/select_menu/` | features | 1 | 518 | Searchable dropdown select menu with multi-select tags and keyboard navigation |
| `components/signature/` | features | 2 | 410 | Signature pad component with draw, auto-generate, and load modes |
| `components/tags_list/` | features | 1 | 47 | Renders a list of colored tags with optional visibility limit and overflow co... |
| `components/time_picker/` | features | 1 | 304 | Time input component with dropdown hour/minute selection and configurable rou... |
| `components/tree_editor/` | features | 19 | 2,638 | AST manipulation helpers for boolean wrapping, negation, and path validation |
| `components/user_switch/` | features | 1 | 67 | Login page component for quick-switching between recently connected user acco... |
| `core/` | shared | 7 | 1,875 | Lazy-loads CSS/JS asset bundles into documents with caching |
| `core/browser/` | shared | 5 | 776 | Prevents default scroll on bare "#" anchor clicks |
| `core/colors/` | shared | 1 | 223 | Predefined color palettes for charts and graph visualizations |
| `core/errors/` | shared | 1 | 215 | Traceback formatting, source-map annotation, and error chain utilities |
| `core/l10n/` | shared | 7 | 1,214 | Luxon-based date/datetime parsing, formatting, serialization, and locale-awar... |
| `core/l10n/utils/` | shared | 3 | 395 | Locale-aware list formatting via Intl.ListFormat (conjunction, disjunction, u... |
| `core/network/` | shared | 5 | 1,191 | Content-Disposition header parser (RFC 6266/5987) |
| `core/position/` | shared | 2 | 558 | OWL hook for auto-repositioning a popper element relative to a target |
| `core/py_js/` | shared | 9 | 2,573 | Public API for parsing and evaluating Python expressions in JS |
| `core/utils/` | shared | 18 | 2,633 | ErrorHandler component that catches child rendering errors |
| `core/utils/collections/` | shared | 3 | 505 | Array helpers: groupBy, sortBy, unique, intersection, cartesian, zip |
| `core/utils/dnd/` | shared | 7 | 2,287 | useDraggable OWL hook for free-form element dragging |
| `core/utils/dom/` | shared | 8 | 1,289 | useAutoresize hook to auto-grow input/textarea elements on content change |
| `core/utils/format/` | shared | 4 | 1,151 | Binary size detection, base64 length calculation, and human-readable byte for... |
| `fields/` | features | 14 | 2,308 | OWL hook that opens a dynamic placeholder popover on trigger key |
| `fields/basic/` | features | 2 | 93 | Abstract base class for numeric input fields with shared focus and parse logic |
| `fields/basic/boolean/` | features | 1 | 42 | Checkbox field widget for Boolean columns |
| `fields/basic/boolean_favorite/` | features | 1 | 70 | Star toggle field for marking records as favorites |
| `fields/basic/boolean_icon/` | features | 1 | 45 | Clickable icon field that toggles a Boolean value |
| `fields/basic/boolean_toggle/` | features | 2 | 77 | Toggle switch field widget for Boolean columns |
| `fields/basic/char/` | features | 1 | 117 | Single-line text input field for Char columns |
| `fields/basic/color/` | features | 1 | 46 | Native color picker input field for Char columns |
| `fields/basic/copy_clipboard/` | features | 1 | 120 | Wrapper field that adds a copy-to-clipboard button to Char/URL fields |
| `fields/basic/email/` | features | 1 | 54 | Email input field with mailto link in readonly mode |
| `fields/basic/float/` | features | 1 | 156 | Numeric input field for Float columns with locale-aware formatting |
| `fields/basic/float_factor/` | features | 1 | 46 | Float field that applies a multiplication factor for display and storage |
| `fields/basic/float_time/` | features | 1 | 66 | Time duration input that stores hours as a float (e.g. 1.5 = 1h30) |
| `fields/basic/float_toggle/` | features | 1 | 106 | Cyclic button that steps through a list of float values on click |
| `fields/basic/html/` | features | 1 | 17 | Simple HTML field widget extending TextField for Html columns |
| `fields/basic/integer/` | features | 1 | 113 | Numeric input field for Integer columns with locale-aware formatting |
| `fields/basic/json/` | features | 1 | 28 | Read-only display field for JSON columns |
| `fields/basic/json_checkboxes/` | features | 1 | 64 | Checkbox group field backed by a JSON object of boolean flags |
| `fields/basic/monetary/` | features | 1 | 145 | Currency-aware numeric input field for Monetary columns |
| `fields/basic/percentage/` | features | 1 | 64 | Numeric input field that displays and parses percentage values |
| `fields/basic/phone/` | features | 1 | 57 | Phone number input field with tel: link in readonly mode |
| `fields/basic/text/` | features | 1 | 151 | Multi-line textarea input field for Text columns |
| `fields/basic/url/` | features | 1 | 77 | URL input field with clickable hyperlink in readonly mode |
| `fields/display/badge/` | features | 1 | 75 | Read-only badge pill for Selection and Many2one columns |
| `fields/display/contact_statistics/` | features | 1 | 27 | Read-only list display for contact statistics stored as JSON |
| `fields/display/gauge/` | features | 1 | 141 | Chart.js doughnut gauge visualization for numeric fields |
| `fields/display/handle/` | features | 1 | 31 | Drag handle icon for manual record reordering in list views |
| `fields/display/percent_pie/` | features | 1 | 37 | Pie chart visualization showing a percentage value |
| `fields/display/progress_bar/` | features | 2 | 197 | Kanban-view variant of the progress bar field |
| `fields/display/stat_info/` | features | 1 | 77 | Stat button content showing a formatted value with a label |
| `fields/display/statusbar/` | features | 1 | 405 | Horizontal pipeline status bar for Selection and Many2one columns |
| `fields/media/attachment_image/` | features | 1 | 22 | Read-only image display field for Many2one attachment references |
| `fields/media/binary/` | features | 1 | 114 | File upload/download field for Binary columns |
| `fields/media/contact_image/` | features | 1 | 51 | Image field variant with fallback to a preview image when empty |
| `fields/media/image/` | features | 1 | 351 | Image upload, preview, and zoom field for Binary image columns |
| `fields/media/image_url/` | features | 1 | 72 | Image display field that loads from a URL stored in a Char column |
| `fields/media/pdf_viewer/` | features | 1 | 122 | Embedded PDF viewer field for Binary columns using PDF.js |
| `fields/media/signature/` | features | 1 | 196 | Signature pad field for capturing and storing handwritten signatures |
| `fields/relational/` | features | 5 | 1,237 | Autocomplete component for many2one/many2many fields with search, quick-creat... |
| `fields/relational/many2many_binary/` | features | 1 | 106 | File attachment list field for Many2many relations to ir.attachment |
| `fields/relational/many2many_checkboxes/` | features | 1 | 109 | Checkbox group field for Many2many relations |
| `fields/relational/many2many_tags/` | features | 2 | 428 | Kanban-view variant of Many2many tags showing only colored tags |
| `fields/relational/many2many_tags_avatar/` | features | 1 | 176 | Avatar tag list field for Many2many relations with user images |
| `fields/relational/many2one/` | features | 2 | 536 | Core Many2One autocomplete component with search, navigation, and barcode sup... |
| `fields/relational/many2one_avatar/` | features | 2 | 65 | Kanban-view Many2one field displaying an avatar image |
| `fields/relational/many2one_barcode/` | features | 1 | 28 | Many2one field with barcode scanner support |
| `fields/relational/many2one_reference/` | features | 1 | 58 | Many2one field for Many2oneReference columns with dynamic relation model |
| `fields/relational/many2one_reference_integer/` | features | 1 | 24 | Integer display field for Many2oneReference columns showing the record ID |
| `fields/relational/reference/` | features | 1 | 271 | Reference field widget combining a model selector with a Many2one picker |
| `fields/relational/x2many/` | features | 2 | 412 | Read-only list-view summary field for One2many and Many2many columns |
| `fields/selection/` | features | 1 | 69 | Abstract base class for selection-like fields with special data loading |
| `fields/selection/badge_selection/` | features | 2 | 151 | Clickable badge group field for Selection and Many2one columns |
| `fields/selection/badge_selection_with_filter/` | features | 1 | 42 | Badge selection field filtered by an allowed-values field |
| `fields/selection/label_selection/` | features | 1 | 53 | Colored label display field for Selection columns |
| `fields/selection/priority/` | features | 1 | 122 | Star rating field for priority Selection columns |
| `fields/selection/radio/` | features | 1 | 116 | Radio button group field for Selection and Many2one columns |
| `fields/selection/selection/` | features | 2 | 194 | Selection dropdown field with whitelist/blacklist value filtering |
| `fields/selection/state_selection/` | features | 1 | 121 | Kanban-style colored state dot dropdown for Selection columns |
| `fields/specialized/ace/` | features | 1 | 102 | Code editor field using the Ace/CodeEditor component |
| `fields/specialized/color_picker/` | features | 1 | 40 | Predefined color palette picker field for Integer columns |
| `fields/specialized/domain/` | features | 1 | 391 | Domain expression editor field with record count and selector UI |
| `fields/specialized/field_selector/` | features | 1 | 97 | Model field path selector field for Char columns |
| `fields/specialized/google_slide_viewer/` | features | 1 | 63 | Embedded Google Slides presentation viewer field |
| `fields/specialized/iframe_wrapper/` | features | 1 | 50 | Iframe wrapper that renders HTML field content inside an isolated iframe |
| `fields/specialized/ir_ui_view_ace/` | features | 1 | 22 | Code editor field variant for ir.ui.view XML arch editing |
| `fields/specialized/journal_dashboard_graph/` | features | 1 | 186 | Chart.js graph field for accounting journal dashboard data |
| `fields/specialized/kanban_color_picker/` | features | 1 | 38 | Inline color palette picker for kanban card color selection |
| `fields/specialized/properties/` | features | 8 | 2,827 | Calendar-view read-only variant of the properties field |
| `fields/temporal/datetime/` | features | 2 | 775 | Date and datetime field widget with inline editing and picker integration |
| `fields/temporal/remaining_days/` | features | 1 | 108 | Deadline countdown field showing remaining days with color-coded urgency |
| `fields/temporal/timezone_mismatch/` | features | 1 | 109 | Timezone selection field that warns when browser and user timezones differ |
| `legacy/js/core/` | misc | 1 | 185 | Legacy class inheritance system based on John Resig's simple JavaScript inher... |
| `legacy/js/public/` | misc | 5 | 1,791 | Lazy script loader that defers event handling until all JS bundles are loaded |
| `libs/` | misc | 1 | 117 | (generated/vendored — no description) |
| `model/` | entities | 6 | 1,594 | Sample server, property field definitions, and shared model utilities |
| `model/relational_model/` | entities | 23 | 7,218 | x2many ORM command serialization and deduplication (CREATE, UPDATE, LINK, SET... |
| `polyfills/` | misc | 1 | 138 | (generated/vendored — no description) |
| `public/` | pages | 11 | 1,922 | Interaction that detects Caps Lock state and toggles a warning on password in... |
| `search/` | widgets | 16 | 4,045 | CallbackRecorder utility and useSetupAction hook for persisting view state ac... |
| `search/action_menus/` | widgets | 1 | 217 | Action/Print dropdown menus for executing server actions on selected records |
| `search/breadcrumbs/` | widgets | 1 | 29 | Navigation breadcrumb trail showing the action stack with back-navigation |
| `search/cog_menu/` | widgets | 1 | 100 | Combined cog dropdown merging Action, Print, and registry-based menu items |
| `search/control_panel/` | widgets | 1 | 861 | Control panel UI with search bar, breadcrumbs, filter/groupby menus, and embe... |
| `search/custom_favorite_item/` | widgets | 1 | 104 | Dropdown form for saving the current search as a named favorite filter |
| `search/custom_group_by_item/` | widgets | 1 | 31 | Dropdown item for selecting a custom field to group by |
| `search/properties_group_by_item/` | widgets | 1 | 84 | Group-by dropdown item that lazily loads property definitions for grouping |
| `search/search_bar/` | widgets | 2 | 882 | Search bar with autocomplete suggestions, facet display, and keyboard navigation |
| `search/search_bar_menu/` | widgets | 1 | 204 | Dropdown menu grouping Filter, Group By, Favorites, and search panels |
| `search/search_panel/` | widgets | 1 | 507 | Sidebar filter panel with category trees and grouped checkbox filters |
| `search/utils/` | widgets | 3 | 507 | Date period/quarter/interval option definitions and domain generators for sea... |
| `search/with_search/` | widgets | 1 | 112 | Wrapper component that creates a SearchModel and injects it into the sub-envi... |
| `services/` | shared | 15 | 2,969 | Currency lookup, formatting, and exchange rate fetching |
| `services/commands/` | shared | 5 | 961 | (generated/vendored — no description) |
| `services/debug/` | shared | 6 | 513 | Debug context manager that collects and merges debug menu items by category |
| `services/hotkeys/` | shared | 2 | 552 | useHotkey hook to register/unregister keyboard shortcuts with component lifec... |
| `services/install_scoped_app/` | shared | 1 | 63 | Public page component for installing scoped Progressive Web Apps |
| `services/navigation/` | shared | 1 | 472 | Keyboard arrow-key navigation hook for selectable item lists |
| `services/pwa/` | shared | 2 | 295 | Dialog showing Safari-specific PWA installation instructions (iOS and macOS) |
| `ui/` | shared | 1 | 53 | (generated/vendored — no description) |
| `ui/block/` | shared | 2 | 380 | Full-screen overlay component that blocks UI during long-running operations |
| `ui/bottom_sheet/` | shared | 2 | 437 | Mobile-friendly slide-up panel with drag-to-dismiss and snap points |
| `ui/dialog/` | shared | 3 | 408 | Standard confirm/cancel dialog with async button handling |
| `ui/effects/` | shared | 2 | 174 | Service that triggers visual effects (rainbow man) via the effects registry |
| `ui/notification/` | shared | 3 | 206 | Individual notification toast with auto-close progress bar and action buttons |
| `ui/overlay/` | shared | 2 | 192 | Renders overlay entries (popovers, dialogs, effects) with nested click-away t... |
| `ui/popover/` | shared | 3 | 499 | Positioned popover component with click-away close, hotkey escape, and arrow ... |
| `ui/tooltip/` | shared | 3 | 328 | Simple tooltip component rendered by the tooltip service |
| `views/` | widgets | 13 | 2,836 | Empty-state placeholder shown when a view has no records |
| `views/calendar/` | widgets | 8 | 2,086 | Parses calendar view XML arch into field mappings, scales, filters, and popov... |
| `views/calendar/calendar_common/` | widgets | 3 | 675 | Popover for calendar events in day/week/month scales |
| `views/calendar/calendar_filter_section/` | widgets | 1 | 205 | Collapsible sidebar filter section for a calendar filter field (attendees, re... |
| `views/calendar/calendar_side_panel/` | widgets | 1 | 65 | Side panel with date picker and filter sections for the calendar view |
| `views/calendar/calendar_year/` | widgets | 2 | 355 | Popover listing grouped records when clicking a day cell in year view |
| `views/calendar/hooks/` | widgets | 3 | 425 | Hook managing calendar event popovers with desktop/mobile responsive behavior |
| `views/calendar/mobile_filter_panel/` | widgets | 1 | 48 | Compact filter panel for mobile calendar with sidebar toggle |
| `views/calendar/quick_create/` | widgets | 1 | 90 | Lightweight dialog for creating a calendar event with just a title |
| `views/form/` | widgets | 7 | 2,014 | Parses form view XML arch into field/widget descriptors, active actions, and ... |
| `views/form/button_box/` | widgets | 1 | 46 | Responsive stat-button container with overflow dropdown for form views |
| `views/form/form_cog_menu/` | widgets | 1 | 10 | Form-view variant of the cog menu with save-before-action behavior |
| `views/form/form_error_dialog/` | widgets | 1 | 59 | Error dialog shown on form save failure with discard/redirect/stay options |
| `views/form/form_group/` | widgets | 1 | 112 | OuterGroup and InnerGroup components for form view column layout |
| `views/form/form_status_indicator/` | widgets | 1 | 62 | Save/discard indicator shown when the form record is dirty or invalid |
| `views/form/setting/` | widgets | 1 | 74 | Individual setting row with label, help text, and company-dependent icon |
| `views/form/status_bar_buttons/` | widgets | 1 | 29 | Renders action buttons in the form status bar with overflow dropdown |
| `views/graph/` | widgets | 6 | 1,914 | Parses graph view XML arch into chart mode, measures, groupBy, and display flags |
| `views/kanban/` | widgets | 14 | 3,685 | Parses kanban view XML arch into card templates, field nodes, progress bars, ... |
| `views/list/` | widgets | 17 | 6,150 | Column width calculation, min/max enforcement, and resize-freeze hook for lis... |
| `views/list/export_all/` | widgets | 1 | 46 | Cog-menu item triggering direct XLSX export of all records |
| `views/pivot/` | widgets | 11 | 2,425 | Parses pivot view XML arch into measures, row/column groupBy, and display flags |
| `views/view_button/` | widgets | 3 | 399 | ViewButton variant for list/kanban headers that operates on multiple selected... |
| `views/view_components/` | widgets | 9 | 810 | Numeric display with smooth CSS animation on value changes and optional multi... |
| `views/view_dialogs/` | widgets | 3 | 826 | Export configuration dialog: field selection, template management, and format... |
| `views/widgets/` | widgets | 2 | 163 | Standard OWL prop definitions shared by all view widgets (record and readonly) |
| `views/widgets/attach_document/` | widgets | 1 | 101 | Widget button that uploads files as ir.attachment records and optionally call... |
| `views/widgets/documentation_link/` | widgets | 1 | 66 | Widget rendering a hyperlink to versioned Odoo documentation |
| `views/widgets/notification_alert/` | widgets | 1 | 27 | Widget displaying a warning banner when browser push notifications are blocked |
| `views/widgets/ribbon/` | widgets | 1 | 70 | Decorative ribbon on the top-right corner of a form view with configurable la... |
| `views/widgets/signature/` | widgets | 1 | 98 | Widget opening a signature drawing dialog and writing the captured image to a... |
| `views/widgets/week_days/` | widgets | 1 | 62 | Widget rendering seven day-of-week checkboxes respecting the locale's week st... |
| `webclient/` | pages | 5 | 389 | Service that auto-reloads currencies when res.currency records are mutated |
| `webclient/actions/` | pages | 13 | 2,778 | Executes action buttons (type=object/action/special) with RPC, context filter... |
| `webclient/actions/reports/` | pages | 4 | 327 | Client action rendering an HTML report in an iframe with print button and act... |
| `webclient/burger_menu/` | pages | 1 | 77 | Fullscreen mobile menu displaying user menu, company switcher, and current ap... |
| `webclient/burger_menu/burger_user_menu/` | pages | 1 | 20 | Mobile variant of the user menu shown inside the burger menu overlay |
| `webclient/burger_menu/mobile_switch_company_menu/` | pages | 1 | 32 | Mobile company switcher with collapsible toggle for many companies |
| `webclient/clickbot/` | pages | 2 | 636 | Automated UI testing bot that clicks through all apps, views, and filters to ... |
| `webclient/debug/` | pages | 1 | 72 | Debug menu items for running unit tests, opening views, and toggling technica... |
| `webclient/debug/profiling/` | pages | 4 | 577 | Debug menu dropdown item for toggling SQL/trace profiling collectors |
| `webclient/density/` | pages | 2 | 122 | Service managing content density (default/compact/condensed) via body CSS cla... |
| `webclient/errors/` | pages | 2 | 72 | Error handler converting browser "Failed to fetch" TypeErrors into Connection... |
| `webclient/loading_indicator/` | pages | 1 | 72 | Loading indicator counting active RPCs and blocking the UI after a 3s delay |
| `webclient/menus/` | pages | 3 | 340 | Utility functions to traverse the menu tree and compute flat app/menuItem lis... |
| `webclient/navbar/` | pages | 1 | 287 | Main navigation bar with app switcher, sub-menus, systray items, and mobile s... |
| `webclient/res_user_group_ids_field/` | pages | 3 | 520 | Field widget for visualizing and configuring res.users access rights (group_ids) |
| `webclient/settings_form_view/` | pages | 5 | 481 | Three-way dialog (Save/Discard/Stay) for unsaved settings changes |
| `webclient/settings_form_view/fields/` | pages | 2 | 82 | Boolean field for settings that shows an Enterprise upgrade dialog when checked |
| `webclient/settings_form_view/fields/settings_binary_field/` | pages | 1 | 32 | BinaryField variant resolving download URLs via the related field's relation |
| `webclient/settings_form_view/highlight_text/` | pages | 3 | 74 | FormLabel variant with search-term highlighting and enterprise upgrade badge |
| `webclient/settings_form_view/settings/` | pages | 5 | 339 | Setting variant with search-based visibility filtering and URL hash highlighting |
| `webclient/settings_form_view/widgets/` | pages | 5 | 308 | Service that checks whether demo data is active in the current database |
| `webclient/share_target/` | pages | 1 | 76 | Service receiving shared files from the PWA service worker (Web Share Target ... |
| `webclient/switch_company_menu/` | pages | 2 | 488 | Single company row in the switch-company dropdown with toggle and log-into ac... |
| `webclient/user_menu/` | pages | 2 | 245 | Systray dropdown displaying current user avatar and menu items from the user_... |
| `(root)` | misc | 4 | 774 | Top-level entry points and session |
