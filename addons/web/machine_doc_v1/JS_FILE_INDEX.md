# JS File Index

> **602 files** | **145,217 lines** | Auto-generated from `@module` JSDoc
>
> Search this file to answer "where is X implemented?"

## boot/ (2 files, 85 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `boot/main.js` | 14 | Entry point that launches the web client (replaced in enterprise) |
| `boot/start.js` | 71 | Initializes session data, caches, and mounts the root web client component |

## components/ (89 files, 50,383 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `components/action_swiper/action_swiper.js` | 250 | Touch swipe component that triggers actions on left/right swipe gestures |
| `components/autocomplete/autocomplete.js` | 557 | Generic autocomplete dropdown with multi-source results, keyboard navigation, and debounced search |
| `components/barcode/ZXingBarcodeDetector.js` | 174 | BarcodeDetector polyfill built on ZXing for browsers without native support |
| `components/barcode/barcode_dialog.js` | 67 | Dialog wrapper for the barcode video scanner with error state handling |
| `components/barcode/barcode_video_scanner.js` | 258 | Camera-based barcode scanner using BarcodeDetector API with ZXing fallback |
| `components/barcode/crop_overlay.js` | 190 | Draggable and resizable crop region overlay for barcode scanning area |
| `components/checkbox/checkbox.js` | 110 | Accessible checkbox component with label slot and hotkey support |
| `components/code_editor/code_editor.js` | 195 | Ace-based code editor component with syntax highlighting and theme support |
| `components/color_picker/color_picker.js` | 459 | Full-featured color picker with preset palette, custom colors, and gradient support |
| `components/color_picker/custom_color_picker/custom_color_picker.js` | 766 | HSL/RGB color picker with canvas gradient, sliders, and hex input |
| `components/color_picker/tabs/color_picker_custom_tab.js` | 49 | Color picker tab for custom color input with gradient support |
| `components/color_picker/tabs/color_picker_solid_tab.js` | 31 | Color picker tab rendering the preset solid color palette grid |
| `components/colorlist/colorlist.js` | 75 | Expandable color swatch picker for selecting from predefined Odoo color indices |
| `components/copy_button/copy_button.js` | 52 | Clipboard copy button with success tooltip feedback |
| `components/datetime/datetime_input.js` | 62 | Date/time text input component that opens a DateTimePicker popover |
| `components/datetime/datetime_picker.js` | 734 | Calendar grid date/time picker with range selection and time input |
| `components/datetime/datetime_picker_hook.js` | 40 | Hook that wires input refs to the datetime picker service |
| `components/datetime/datetime_picker_popover.js` | 35 | Popover wrapper that hosts a DateTimePicker with keyboard dismiss support |
| `components/datetime/datetime_picker_service.js` | 645 | Service managing date picker popover lifecycle, positioning, and input synchronization |
| `components/domain_selector/domain_selector.js` | 171 | Visual domain builder that converts between string domains and tree editors |
| `components/domain_selector/domain_selector_operator_editor.js` | 74 | Maps field types to their valid domain comparison operators |
| `components/domain_selector/utils.js` | 30 | Default condition and domain builders for the domain selector |
| `components/domain_selector_dialog/domain_selector_dialog.js` | 120 | Modal dialog for editing and validating an Odoo domain filter |
| `components/dropdown/_behaviours/dropdown_group_hook.js` | 44 | Hook that registers a dropdown within a DropdownGroup and tracks group open state |
| `components/dropdown/_behaviours/dropdown_nesting.js` | 165 | Parent-child nesting state and close propagation logic for nested dropdowns |
| `components/dropdown/_behaviours/dropdown_popover.js` | 67 | Popover content renderer for dropdown menus with item list and slot support |
| `components/dropdown/accordion_item.js` | 42 | Collapsible accordion panel with animated expand/collapse transitions |
| `components/dropdown/checkbox_item.js` | 16 | Dropdown menu item variant with an integrated checkbox toggle |
| `components/dropdown/dropdown.js` | 427 | Core dropdown component with popover positioning, nesting, and keyboard navigation |
| `components/dropdown/dropdown_group.js` | 47 | Groups multiple dropdowns so only one can be open at a time |
| `components/dropdown/dropdown_hooks.js` | 55 | Reactive DropdownState class and hooks for open/close control |
| `components/dropdown/dropdown_item.js` | 63 | Single selectable item within a dropdown menu with configurable close behavior |
| `components/dropzone/dropzone.js` | 28 | Visual drop target overlay that tracks drag enter/leave and fires onDrop |
| `components/dropzone/dropzone_hook.js` | 120 | Hooks for attaching drag-and-drop file upload zones to DOM elements |
| `components/emoji_picker/emoji_data.js` | 35,980 | (generated/vendored — no description) |
| `components/emoji_picker/emoji_picker.js` | 761 | Emoji picker with category navigation, fuzzy search, and recent emoji tracking |
| `components/errors/error_dialogs.js` | 256 | Error dialog components for RPC, client, network, and validation errors |
| `components/errors/error_handlers.js` | 188 | Registry-based error handlers that route exceptions to appropriate dialogs or notifications |
| `components/expression_editor/expression_editor.js` | 120 | Visual tree-based editor for Python expressions with field path selection |
| `components/expression_editor/expression_editor_operator_editor.js` | 27 | Filters domain operators to the subset valid for Python expressions |
| `components/expression_editor_dialog/expression_editor_dialog.js` | 92 | Modal dialog for editing Python expressions with validation preview |
| `components/file_input/file_input.js` | 134 | Customizable file upload input with route-based server upload and multi-file support |
| `components/file_upload/file_upload_progress_bar.js` | 35 | Progress bar with cancel button for active file uploads |
| `components/file_upload/file_upload_progress_container.js` | 14 | Container that renders progress indicators for all active file uploads |
| `components/file_upload/file_upload_progress_record.js` | 47 | Per-record file upload overlay showing percentage and MB progress |
| `components/file_viewer/file_model.js` | 152 | FileModelMixin providing URL routing and type detection for viewable file attachments |
| `components/file_viewer/file_viewer.js` | 272 | Full-screen image, PDF, video, and text file preview with navigation controls |
| `components/file_viewer/file_viewer_hook.js` | 45 | Factory and hook for opening/closing a file viewer as a main component |
| `components/index.js` | 88 | (generated/vendored — no description) |
| `components/ir_ui_view_code_editor/code_editor.js` | 95 | Extended code editor that highlights invalid XPath locators in ir.ui.view arch |
| `components/main_components_container.js` | 46 | Renders all dynamically registered main_components from the registry |
| `components/model_field_selector/model_field_selector.js` | 111 | Field path selector with breadcrumb display and popover field browser |
| `components/model_field_selector/model_field_selector_popover.js` | 376 | Searchable field browser popover with pagination through relational field chains |
| `components/model_selector/model_selector.js` | 113 | Autocomplete component for searching and selecting Odoo model names |
| `components/notebook/notebook.js` | 198 | Tabbed notebook component that renders one page at a time with tab navigation |
| `components/pager/pager.js` | 235 | Pagination component with prev/next navigation and editable page range input |
| `components/pager/pager_indicator.js` | 45 | Floating toast indicator showing current page position on pager updates |
| `components/record_selectors/base_record_selector.js` | 52 | Base class for record selector components with display name loading infrastructure |
| `components/record_selectors/multi_record_selector.js` | 81 | Multi-value record picker with tag display and autocomplete search |
| `components/record_selectors/record_autocomplete.js` | 149 | Autocomplete search for records with name_search and "Search More" dialog |
| `components/record_selectors/record_selector.js` | 52 | Single-value record picker with avatar display and autocomplete |
| `components/record_selectors/tag_navigation_hook.js` | 89 | Keyboard navigation hook for moving between and deleting tags in record selectors |
| `components/resizable_panel/resizable_panel.js` | 169 | Side panel component with drag handle for interactive width resizing |
| `components/select_menu/select_menu.js` | 518 | Searchable dropdown select menu with multi-select tags and keyboard navigation |
| `components/signature/name_and_signature.js` | 361 | Signature pad component with draw, auto-generate, and load modes |
| `components/signature/signature_dialog.js` | 49 | Dialog wrapper for capturing and uploading a signature |
| `components/tags_list/tags_list.js` | 47 | Renders a list of colored tags with optional visibility limit and overflow counter |
| `components/time_picker/time_picker.js` | 304 | Time input component with dropdown hour/minute selection and configurable rounding |
| `components/transition.js` | 159 | CSS transition helpers for mount/unmount animations with configurable class names |
| `components/tree_editor/ast_utils.js` | 39 | AST manipulation helpers for boolean wrapping, negation, and path validation |
| `components/tree_editor/condition_tree.js` | 366 | Core tree data structures (conditions, connectors, expressions) and tree manipulation functions |
| `components/tree_editor/construct_domain_from_tree.js` | 75 | Converts a condition tree into an Odoo domain string representation |
| `components/tree_editor/construct_expression_from_tree.js` | 177 | Converts a condition tree into a Python expression string |
| `components/tree_editor/construct_tree_from_domain.js` | 87 | Parses an Odoo domain string into a condition tree structure |
| `components/tree_editor/construct_tree_from_expression.js` | 209 | Parses a Python expression string into a condition tree structure |
| `components/tree_editor/domain_contains_expressions.js` | 37 | Checks whether a domain string contains dynamic Python expressions |
| `components/tree_editor/domain_from_tree.js` | 11 | High-level tree-to-domain conversion with virtual operator elimination |
| `components/tree_editor/expression_from_tree.js` | 11 | High-level tree-to-expression conversion with virtual operator elimination |
| `components/tree_editor/operators.js` | 39 | Operator negation maps and comparator constants for domain/expression trees |
| `components/tree_editor/tree_editor.js` | 261 | Recursive tree editor component for visually building domain and expression conditions |
| `components/tree_editor/tree_editor_autocomplete.js` | 86 | Record autocomplete variants for single and multi-value domain/expression editors |
| `components/tree_editor/tree_editor_components.js` | 100 | Shared input, select, range, and list sub-components for tree editor value entry |
| `components/tree_editor/tree_editor_operator_editor.js` | 198 | Operator descriptions, labels, and editor info for domain/expression tree conditions |
| `components/tree_editor/tree_editor_value_editors.js` | 436 | Field-type-specific value editor configurations for tree editor conditions |
| `components/tree_editor/tree_from_domain.js` | 11 | High-level domain-to-tree conversion with virtual operator introduction |
| `components/tree_editor/tree_from_expression.js` | 11 | High-level expression-to-tree conversion with virtual operator introduction |
| `components/tree_editor/utils.js` | 55 | Shared helpers for value disambiguation, ID checking, model resolution, and default paths |
| `components/tree_editor/virtual_operators.js` | 429 | Introduces and eliminates virtual operators (between, in range, any/all) in condition trees |
| `components/user_switch/user_switch.js` | 67 | Login page component for quick-switching between recently connected user accounts |

## core/ (81 files, 16,921 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `core/assets.js` | 313 | Lazy-loads CSS/JS asset bundles into documents with caching |
| `core/browser/anchor_scroll.js` | 15 | Prevents default scroll on bare "#" anchor clicks |
| `core/browser/browser.js` | 125 | Patchable browser API facade (localStorage, fetch, setTimeout, etc.) for testability |
| `core/browser/cookie.js` | 41 | Read, write, and delete browser cookies via document.cookie |
| `core/browser/feature_detection.js` | 136 | Browser and device capability checks (Chrome, mobile, touch, PWA) |
| `core/browser/router.js` | 459 | URL routing: parse, serialize, and push browser history state |
| `core/colors/colors.js` | 223 | Predefined color palettes for charts and graph visualizations |
| `core/context.js` | 97 | Builds an evaluation context by merging and evaluating Python expressions |
| `core/domain.js` | 475 | Domain expression AST: parsing, combining, evaluation, and conversion to string |
| `core/errors/error_utils.js` | 215 | Traceback formatting, source-map annotation, and error chain utilities |
| `core/index.js` | 10 | (generated/vendored — no description) |
| `core/l10n/date_serialization.js` | 81 | Server-format date serialization and deserialization with WeakMap caching |
| `core/l10n/date_utils.js` | 138 | Pure date comparison, clamping, range checks, and locale-aware week helpers |
| `core/l10n/dates.js` | 433 | Luxon-based date/datetime parsing, formatting, and smart date input (delegates serialization to date_serialization.js, utilities to date_utils.js) |
| `core/l10n/localization.js` | 41 | Shared reactive localization object (date/number formats, direction, locale) |
| `core/l10n/time.js` | 309 | Time class for 24h time representation with locale-aware parsing |
| `core/l10n/translation.js` | 213 | Runtime i18n: _t() tagged-template translator with markup-safe interpolation |
| `core/l10n/utils.js` | 7 | Re-exports format_list, locales, and normalize l10n utilities |
| `core/l10n/utils/format_list.js` | 89 | Locale-aware list formatting via Intl.ListFormat (conjunction, disjunction, unit) |
| `core/l10n/utils/locales.js` | 101 | Bidirectional JS (BCP 47) to Python (XPG) locale conversion |
| `core/l10n/utils/normalize.js` | 205 | Unicode normalization, case folding, and accent-insensitive string matching |
| `core/network/content_disposition.js` | 248 | Content-Disposition header parser (RFC 6266/5987) |
| `core/network/download.js` | 346 | File download via RPC with content-disposition filename extraction |
| `core/network/rpc.js` | 216 | JSON-RPC client with error classification, request bus events, and XHR settings |
| `core/network/rpc_cache.js` | 318 | Encrypted RAM/IndexedDB cache for RPC responses |
| `core/network/rpc_dedup.js` | 63 | Shares a single promise across identical concurrent RPC requests |
| `core/position/position_hook.js` | 154 | OWL hook for auto-repositioning a popper element relative to a target |
| `core/position/utils.js` | 404 | Compute optimal popper placement with direction/variant flipping and RTL support |
| `core/py_js/py.js` | 72 | Public API for parsing and evaluating Python expressions in JS |
| `core/py_js/py_builtin.js` | 131 | Python built-in functions (bool, len, set, sorted, etc.) for the JS evaluator |
| `core/py_js/py_date.js` | 552 | Python date, datetime, time, and relativedelta emulation (delegates helpers to py_date_helpers.js, timedelta to py_timedelta.js) |
| `core/py_js/py_date_helpers.js` | 270 | Calendar arithmetic: ordinal conversions, leap year detection, date normalization constants |
| `core/py_js/py_interpreter.js` | 518 | AST-walking interpreter for Python expressions used in domains and QWeb |
| `core/py_js/py_parser.js` | 412 | Pratt parser that converts Python token streams into AST nodes |
| `core/py_js/py_tokenizer.js` | 345 | Lexer that splits Python expression strings into typed tokens |
| `core/py_js/py_timedelta.js` | 164 | Python timedelta emulation: normalized duration stored as (days, seconds, microseconds) |
| `core/py_js/py_utils.js` | 136 | AST-to-value conversion and AST-to-string formatting for Python expressions |
| `core/registry.js` | 293 | Hierarchical key-value store for services, components, fields, and actions |
| `core/template_inheritance.js` | 423 | XPath-based QWeb template inheritance (apply, validate, deep clone) |
| `core/templates.js` | 264 | Template registry: parses, inherits, caches, and retrieves QWeb templates |
| `core/utils/collections/arrays.js` | 283 | Array helpers: groupBy, sortBy, unique, intersection, cartesian, zip |
| `core/utils/collections/cache.js` | 72 | Generic key-path cache with lazy value computation |
| `core/utils/collections/objects.js` | 150 | Object helpers: deepEqual, deepCopy, pick, omit, deepMerge |
| `core/utils/components.js` | 15 | ErrorHandler component that catches child rendering errors |
| `core/utils/concurrency.js` | 207 | Async primitives: Mutex, KeepLast, Race, Deferred, and delay |
| `core/utils/decorations.js` | 39 | Maps decoration-* XML attributes to Bootstrap CSS classes |
| `core/utils/dependency_graph.js` | 114 | Iterative DFS cycle detection for directed dependency graphs |
| `core/utils/dnd/draggable.js` | 57 | useDraggable OWL hook for free-form element dragging |
| `core/utils/dnd/draggable_hook_builder.js` | 913 | Factory for configurable drag-and-drop OWL hooks with touch and scroll support |
| `core/utils/dnd/draggable_hook_builder_owl.js` | 35 | OWL-lifecycle adapter for the draggable hook builder |
| `core/utils/dnd/draggable_hook_builder_utils.js` | 378 | Stateless helpers, constants, and DOM utilities for the draggable hook builder |
| `core/utils/dnd/nested_sortable.js` | 482 | useNestedSortable OWL hook for drag-and-drop with hierarchical nesting |
| `core/utils/dnd/sortable.js` | 387 | useSortable hook for reordering elements within and across groups |
| `core/utils/dnd/sortable_owl.js` | 35 | OWL-lifecycle adapter for useSortable with reactive state |
| `core/utils/dom/autoresize.js` | 156 | useAutoresize hook to auto-grow input/textarea elements on content change |
| `core/utils/dom/classname.js` | 75 | Helpers to add, merge, and toggle CSS classes from strings or objects |
| `core/utils/dom/dvu.js` | 119 | Dynamic viewport units with virtual keyboard and visualViewport tracking |
| `core/utils/dom/events.js` | 32 | Mark and query DOM events as handled during propagation |
| `core/utils/dom/html.js` | 296 | Safe HTML creation, text highlighting, and markup-aware content helpers |
| `core/utils/dom/scrolling.js` | 222 | Scroll detection, scrollIntoView, and scrollbar compensation utilities |
| `core/utils/dom/ui.js` | 221 | DOM visibility, proximity, and tabable-element queries |
| `core/utils/dom/xml.js` | 168 | XML parse, serialize, create, and manipulate DOM elements |
| `core/utils/files.js` | 126 | File size validation and upload hook for multipart form submissions |
| `core/utils/format/binary.js` | 36 | Binary size detection, base64 length calculation, and human-readable byte formatting |
| `core/utils/format/colors.js` | 500 | Color conversions between RGB, HSL, hex, and gradient opacity manipulation |
| `core/utils/format/numbers.js` | 328 | Locale-aware number formatting, parsing, rounding, and human-readable display |
| `core/utils/format/strings.js` | 287 | String helpers: sprintf, escapeRegExp, email validation, intersperse |
| `core/utils/functions.js` | 37 | memoize and uniqueId general-purpose function helpers |
| `core/utils/hooks.js` | 334 | OWL component hooks: useService, useBus, useAutofocus, useOwnedDialogs, useForwardRefToParent |
| `core/utils/indexed_db.js` | 271 | IndexedDB wrapper with versioned schema, quota management, and mutex locking |
| `core/utils/macro.js` | 282 | Step-based macro engine for automated UI interaction sequences |
| `core/utils/order_by.js` | 42 | Converts between OrderTerm arrays and SQL-like "field ASC/DESC" strings |
| `core/utils/patch.js` | 151 | Reversible monkey-patching for class prototypes and object properties |
| `core/utils/pdfjs.js` | 80 | PDF.js viewer button visibility control and library lazy-loading |
| `core/utils/reactive.js` | 70 | Reactive base class and side-effect helper for OWL reactivity system |
| `core/utils/render.js` | 90 | Render QWeb templates to Element, DocumentFragment, Markup, or string |
| `core/utils/search.js` | 170 | Fuzzy text search with consecutive-letter scoring and normalized matching |
| `core/utils/timing.js` | 224 | Batched callbacks, debounce, throttle, and recurring animation frame scheduling |
| `core/utils/urls.js` | 183 | URL construction, origin resolution, image URL generation, and redirect handling |
| `core/utils/virtual_grid.js` | 198 | useVirtualGrid hook for windowed rendering of large row/column grids |

## fields/ (105 files, 15,106 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `fields/basic/boolean/boolean_field.js` | 42 | Checkbox field widget for Boolean columns |
| `fields/basic/boolean_favorite/boolean_favorite_field.js` | 70 | Star toggle field for marking records as favorites |
| `fields/basic/boolean_icon/boolean_icon_field.js` | 45 | Clickable icon field that toggles a Boolean value |
| `fields/basic/boolean_toggle/boolean_toggle_field.js` | 49 | Toggle switch field widget for Boolean columns |
| `fields/basic/boolean_toggle/list_boolean_toggle_field.js` | 28 | List-view variant of the Boolean toggle switch |
| `fields/basic/char/char_field.js` | 117 | Single-line text input field for Char columns |
| `fields/basic/color/color_field.js` | 46 | Native color picker input field for Char columns |
| `fields/basic/copy_clipboard/copy_clipboard_field.js` | 120 | Wrapper field that adds a copy-to-clipboard button to Char/URL fields |
| `fields/basic/email/email_field.js` | 54 | Email input field with mailto link in readonly mode |
| `fields/basic/float/float_field.js` | 156 | Numeric input field for Float columns with locale-aware formatting |
| `fields/basic/float_factor/float_factor_field.js` | 46 | Float field that applies a multiplication factor for display and storage |
| `fields/basic/float_time/float_time_field.js` | 66 | Time duration input that stores hours as a float (e.g. 1.5 = 1h30) |
| `fields/basic/float_toggle/float_toggle_field.js` | 106 | Cyclic button that steps through a list of float values on click |
| `fields/basic/html/html_field.js` | 17 | Simple HTML field widget extending TextField for Html columns |
| `fields/basic/integer/integer_field.js` | 113 | Numeric input field for Integer columns with locale-aware formatting |
| `fields/basic/json/json_field.js` | 28 | Read-only display field for JSON columns |
| `fields/basic/json_checkboxes/json_checkboxes_field.js` | 64 | Checkbox group field backed by a JSON object of boolean flags |
| `fields/basic/monetary/monetary_field.js` | 145 | Currency-aware numeric input field for Monetary columns |
| `fields/basic/numeric_input_field_base.js` | 42 | Abstract base class for numeric input fields with shared focus and parse logic |
| `fields/basic/percentage/percentage_field.js` | 64 | Numeric input field that displays and parses percentage values |
| `fields/basic/phone/phone_field.js` | 57 | Phone number input field with tel: link in readonly mode |
| `fields/basic/text/text_field.js` | 151 | Multi-line textarea input field for Text columns |
| `fields/basic/text_input_field_base.js` | 51 | Abstract base class for text input fields with translation and dynamic placeholder support |
| `fields/basic/url/url_field.js` | 77 | URL input field with clickable hyperlink in readonly mode |
| `fields/display/badge/badge_field.js` | 75 | Read-only badge pill for Selection and Many2one columns |
| `fields/display/contact_statistics/contact_statistics.js` | 27 | Read-only list display for contact statistics stored as JSON |
| `fields/display/gauge/gauge_field.js` | 141 | Chart.js doughnut gauge visualization for numeric fields |
| `fields/display/handle/handle_field.js` | 31 | Drag handle icon for manual record reordering in list views |
| `fields/display/percent_pie/percent_pie_field.js` | 37 | Pie chart visualization showing a percentage value |
| `fields/display/progress_bar/kanban_progress_bar_field.js` | 19 | Kanban-view variant of the progress bar field |
| `fields/display/progress_bar/progress_bar_field.js` | 178 | Editable progress bar displaying current/max numeric values |
| `fields/display/stat_info/stat_info_field.js` | 77 | Stat button content showing a formatted value with a label |
| `fields/display/statusbar/statusbar_field.js` | 405 | Horizontal pipeline status bar for Selection and Many2one columns |
| `fields/dynamic_placeholder_hook.js` | 115 | OWL hook that opens a dynamic placeholder popover on trigger key |
| `fields/dynamic_placeholder_popover.js` | 132 | Popover component for selecting dynamic placeholder field paths |
| `fields/field.js` | 570 | Generic Field component that resolves and renders the appropriate field widget from the registry |
| `fields/field_tooltip.js` | 36 | Builds JSON tooltip info for field debug tooltips |
| `fields/field_types.js` | 6 | Constants for x2many field type identification |
| `fields/file_handler.js` | 129 | FileUploader component for handling file input, validation, and base64 conversion |
| `fields/formatters.js` | 493 | Field value formatters for all ORM field types (date, float, monetary, selection, etc.) |
| `fields/index.js` | 65 | (generated/vendored — no description) |
| `fields/input_field_hook.js` | 214 | OWL hook that syncs an input element with the ORM record and handles dirty/parse/save lifecycle |
| `fields/media/attachment_image/attachment_image_field.js` | 22 | Read-only image display field for Many2one attachment references |
| `fields/media/binary/binary_field.js` | 114 | File upload/download field for Binary columns |
| `fields/media/contact_image/contact_image_field.js` | 51 | Image field variant with fallback to a preview image when empty |
| `fields/media/image/image_field.js` | 351 | Image upload, preview, and zoom field for Binary image columns |
| `fields/media/image_url/image_url_field.js` | 72 | Image display field that loads from a URL stored in a Char column |
| `fields/media/pdf_viewer/pdf_viewer_field.js` | 122 | Embedded PDF viewer field for Binary columns using PDF.js |
| `fields/media/signature/signature_field.js` | 196 | Signature pad field for capturing and storing handwritten signatures |
| `fields/numpad_decimal_hook.js` | 76 | OWL hook that replaces numpad decimal key with the locale decimal separator |
| `fields/parsers.js` | 262 | Field value parsers for all ORM field types (date, float, integer, monetary, percentage, etc.) |
| `fields/relational/many2many_binary/many2many_binary_field.js` | 106 | File attachment list field for Many2many relations to ir.attachment |
| `fields/relational/many2many_checkboxes/many2many_checkboxes_field.js` | 109 | Checkbox group field for Many2many relations |
| `fields/relational/many2many_tags/kanban_many2many_tags_field.js` | 29 | Kanban-view variant of Many2many tags showing only colored tags |
| `fields/relational/many2many_tags/many2many_tags_field.js` | 399 | Colored tag list field with autocomplete for Many2many relations |
| `fields/relational/many2many_tags_avatar/many2many_tags_avatar_field.js` | 176 | Avatar tag list field for Many2many relations with user images |
| `fields/relational/many2one/many2one.js` | 398 | Core Many2One autocomplete component with search, navigation, and barcode support |
| `fields/relational/many2one/many2one_field.js` | 138 | Standard Many2one field with autocomplete, create, and open actions |
| `fields/relational/many2one_avatar/kanban_many2one_avatar_field.js` | 36 | Kanban-view Many2one field displaying an avatar image |
| `fields/relational/many2one_avatar/many2one_avatar_field.js` | 29 | Many2one field variant that displays the related record avatar |
| `fields/relational/many2one_barcode/many2one_barcode_field.js` | 28 | Many2one field with barcode scanner support |
| `fields/relational/many2one_reference/many2one_reference_field.js` | 58 | Many2one field for Many2oneReference columns with dynamic relation model |
| `fields/relational/many2one_reference_integer/many2one_reference_integer_field.js` | 24 | Integer display field for Many2oneReference columns showing the record ID |
| `fields/relational/many2x_autocomplete.js` | 584 | Autocomplete component for many2one/many2many fields with search, quick-create, and dialog creation |
| `fields/relational/reference/reference_field.js` | 271 | Reference field widget combining a model selector with a Many2one picker |
| `fields/relational/relational_active_actions.js` | 112 | Reactive OWL hook for computing x2many field CRUD permissions |
| `fields/relational/special_data.js` | 62 | OWL hook for loading and caching special data tied to a record lifecycle |
| `fields/relational/x2many/list_x2many_field.js` | 26 | Read-only list-view summary field for One2many and Many2many columns |
| `fields/relational/x2many/x2many_field.js` | 386 | Full-featured x2many field with embedded list/kanban sub-views and CRUD controls |
| `fields/relational/x2many_crud.js` | 72 | OWL hook providing CRUD operations (save, update, remove) for x2many fields |
| `fields/relational/x2many_dialog.js` | 407 | Form dialog component for creating and editing x2many inline records |
| `fields/selection/badge_selection/badge_selection_field.js` | 93 | Clickable badge group field for Selection and Many2one columns |
| `fields/selection/badge_selection/list_badge_selection_field.js` | 58 | List-view variant of the badge selection field with color support |
| `fields/selection/badge_selection_with_filter/badge_selection_field_with_filter.js` | 42 | Badge selection field filtered by an allowed-values field |
| `fields/selection/label_selection/label_selection_field.js` | 53 | Colored label display field for Selection columns |
| `fields/selection/priority/priority_field.js` | 122 | Star rating field for priority Selection columns |
| `fields/selection/radio/radio_field.js` | 116 | Radio button group field for Selection and Many2one columns |
| `fields/selection/selection/filterable_selection_field.js` | 85 | Selection dropdown field with whitelist/blacklist value filtering |
| `fields/selection/selection/selection_field.js` | 109 | Standard dropdown selection field for Selection and Many2one columns |
| `fields/selection/selection_like_field.js` | 69 | Abstract base class for selection-like fields with special data loading |
| `fields/selection/state_selection/state_selection_field.js` | 121 | Kanban-style colored state dot dropdown for Selection columns |
| `fields/specialized/ace/ace_field.js` | 102 | Code editor field using the Ace/CodeEditor component |
| `fields/specialized/color_picker/color_picker_field.js` | 40 | Predefined color palette picker field for Integer columns |
| `fields/specialized/domain/domain_field.js` | 391 | Domain expression editor field with record count and selector UI |
| `fields/specialized/field_selector/field_selector_field.js` | 97 | Model field path selector field for Char columns |
| `fields/specialized/google_slide_viewer/google_slide_viewer.js` | 63 | Embedded Google Slides presentation viewer field |
| `fields/specialized/iframe_wrapper/iframe_wrapper_field.js` | 50 | Iframe wrapper that renders HTML field content inside an isolated iframe |
| `fields/specialized/ir_ui_view_ace/ace_field.js` | 22 | Code editor field variant for ir.ui.view XML arch editing |
| `fields/specialized/journal_dashboard_graph/journal_dashboard_graph_field.js` | 186 | Chart.js graph field for accounting journal dashboard data |
| `fields/specialized/kanban_color_picker/kanban_color_picker_field.js` | 38 | Inline color palette picker for kanban card color selection |
| `fields/specialized/properties/calendar_properties_field.js` | 20 | Calendar-view read-only variant of the properties field |
| `fields/specialized/properties/card_properties_field.js` | 22 | Kanban/hierarchy card read-only variant of the properties field |
| `fields/specialized/properties/properties_field.js` | 1,136 | Dynamic property field editor with drag-and-drop reordering and inline definition |
| `fields/specialized/properties/property_definition.js` | 513 | Property type and configuration editor for defining dynamic property fields |
| `fields/specialized/properties/property_definition_selection.js` | 330 | Sortable option editor for property definition selection/tags types |
| `fields/specialized/properties/property_tags.js` | 343 | Tag list component with color picker for property tag values |
| `fields/specialized/properties/property_text.js` | 20 | Auto-resizing textarea component for property text values |
| `fields/specialized/properties/property_value.js` | 443 | Polymorphic value editor component supporting all property field types |
| `fields/standard_field_props.js` | 18 | Standard OWL props schema shared by all field widget components |
| `fields/temporal/datetime/datetime_field.js` | 736 | Date and datetime field widget with inline editing and picker integration |
| `fields/temporal/datetime/list_datetime_field.js` | 39 | List-view variant of datetime/date fields with auto-resizing input |
| `fields/temporal/remaining_days/remaining_days_field.js` | 108 | Deadline countdown field showing remaining days with color-coded urgency |
| `fields/temporal/timezone_mismatch/timezone_mismatch_field.js` | 109 | Timezone selection field that warns when browser and user timezones differ |
| `fields/translation_button.js` | 67 | Translation button component and useTranslationDialog hook for translatable fields |
| `fields/translation_dialog.js` | 125 | Dialog for editing field translation values across installed languages |

## legacy/ (6 files, 1,976 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `legacy/js/core/class.js` | 185 | Legacy class inheritance system based on John Resig's simple JavaScript inheritance |
| `legacy/js/public/lazyloader.js` | 228 | Lazy script loader that defers event handling until all JS bundles are loaded |
| `legacy/js/public/minimal_dom.js` | 135 | Async handler protection and button debouncing utilities for public DOM events |
| `legacy/js/public/public_root.js` | 448 | Legacy PublicRoot widget that bootstraps the OWL app and public widget registry |
| `legacy/js/public/public_root_instance.js` | 11 | Singleton PublicRoot widget instance creation and lazy-loader registration |
| `legacy/js/public/public_widget.js` | 969 | Legacy widget framework for public pages with parent-child lifecycle and DOM event handling |

## libs/ (1 files, 117 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `libs/bootstrap.js` | 117 | (generated/vendored — no description) |

## model/ (29 files, 8,521 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `model/index.js` | 14 | (generated/vendored — no description) |
| `model/model.js` | 304 | Abstract base Model class with OWL lifecycle integration and sample data fallback |
| `model/record.js` | 288 | Standalone OWL component for loading and displaying a single record |
| `model/relational_model/command_builder.js` | 174 | x2many ORM command serialization and deduplication (CREATE, UPDATE, LINK, SET, DELETE, UNLINK) |
| `model/relational_model/datapoint.js` | 64 | Abstract reactive base class for all data model nodes (records, lists, groups) |
| `model/relational_model/dynamic_group_list.js` | 442 | Server-backed grouped list with expand/collapse, cross-group record moves, and progress bars |
| `model/relational_model/dynamic_list.js` | 631 | Abstract paginated list with sorting, domain filtering, and drag-and-drop resequencing |
| `model/relational_model/dynamic_record_list.js` | 210 | Server-backed flat record list with pagination, CRUD, and domain-based selection |
| `model/relational_model/errors.js` | 38 | Error types and handlers for record fetch failures |
| `model/relational_model/field_context.js` | 89 | Context and domain resolution for relational fields |
| `model/relational_model/field_metadata.js` | 336 | ActiveField construction with visibility, readonly, and required modifiers |
| `model/relational_model/field_spec.js` | 122 | Builds server field specifications from active fields for data fetching |
| `model/relational_model/field_values.js` | 339 | Server value parsing, aggregation constants, and default value helpers |
| `model/relational_model/group.js` | 159 | Single group node within a grouped list, holding aggregates and a nested record list |
| `model/relational_model/onchange_coalescer.js` | 104 | Debounce rapid field changes into a single coalesced onchange RPC call |
| `model/relational_model/operation.js` | 33 | Arithmetic operation class for numeric field transformations |
| `model/relational_model/record.js` | 1,458 | Field value management, change tracking, dirty state, and save/discard for individual records |
| `model/relational_model/record_hooks.js` | 73 | OWL hooks for observing record value changes in field components |
| `model/relational_model/record_utils.js` | 151 | Pure utility functions for field attribute evaluation (invisible, readonly, required) |
| `model/relational_model/record_validator.js` | 99 | Pure validation logic to find unset required fields in a record |
| `model/relational_model/record_value_transforms.js` | 181 | Stateless value formatting, defaults, and eval context extraction |
| `model/relational_model/relational_model.js` | 967 | Top-level data model orchestrating records, groups, and lists with ORM loading and onchange |
| `model/relational_model/resequence.js` | 108 | Reorders records by sequence field via drag-and-drop position changes |
| `model/relational_model/static_list.js` | 1,257 | In-memory x2many list: add, remove, reorder records and generate ORM commands |
| `model/relational_model/static_list_utils.js` | 148 | Sorting comparators, record duplication, and sort-direction cycling for StaticList |
| `model/relational_model/utils.js` | 35 | Barrel re-export of field metadata, spec, values, and context utilities for external consumers |
| `model/sample_data.js` | 105 | Sample data constants, field-name regex patterns, and ID-based sample lookup |
| `model/sample_field_generators.js` | 174 | Random value generators for all field types used by the sample server |
| `model/sample_server.js` | 706 | Fake ORM server generating realistic sample data for empty views (delegates generation to sample_field_generators.js, constants to sample_data.js) |

## polyfills/ (1 files, 138 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `polyfills/clipboard.js` | 138 | (generated/vendored — no description) |

## public/ (11 files, 1,922 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `public/caps_lock_warning.js` | 43 | Interaction that detects Caps Lock state and toggles a warning on password inputs |
| `public/colibri.js` | 599 | Mini-framework runtime that manages Interaction lifecycles, dynamic content, and event bindings for public pages |
| `public/database_manager.js` | 102 | DOM event handlers for the database manager page (eye toggle, modals, master password) |
| `public/datetime_picker.js` | 49 | Public interaction that attaches a datetime picker to data-widget elements |
| `public/error_notifications.js` | 42 | Registers Odoo exception types as notification-style error handlers instead of dialogs |
| `public/interaction.js` | 502 | Base class for public page interactions with selector matching, dynamic content, and service access |
| `public/interaction_service.js` | 297 | Core service that discovers, mounts, and manages Interaction instances on DOM elements |
| `public/login.js` | 42 | Login form interaction that adds a loading effect on submit |
| `public/public_component_interaction.js` | 34 | Interaction that mounts OWL components declared via owl-component HTML elements |
| `public/show_password.js` | 27 | Interaction that toggles password field visibility via an eye icon button |
| `public/utils.js` | 185 | PairSet data structure and button click handler utilities for public pages |

## search/ (31 files, 7,683 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `search/action_hook.js` | 200 | CallbackRecorder utility and useSetupAction hook for persisting view state across action switches |
| `search/action_menus/action_menus.js` | 217 | Action/Print dropdown menus for executing server actions on selected records |
| `search/breadcrumbs/breadcrumbs.js` | 29 | Navigation breadcrumb trail showing the action stack with back-navigation |
| `search/cog_menu/cog_menu.js` | 100 | Combined cog dropdown merging Action, Print, and registry-based menu items |
| `search/control_panel/control_panel.js` | 861 | Control panel UI with search bar, breadcrumbs, filter/groupby menus, and embedded actions |
| `search/custom_favorite_item/custom_favorite_item.js` | 104 | Dropdown form for saving the current search as a named favorite filter |
| `search/custom_group_by_item/custom_group_by_item.js` | 31 | Dropdown item for selecting a custom field to group by |
| `search/index.js` | 9 | (generated/vendored — no description) |
| `search/layout.js` | 45 | Top-level view layout assembling ControlPanel, SearchPanel, and content slots |
| `search/pager_hook.js` | 39 | OWL hook that injects reactive pager props into the sub-environment |
| `search/properties_group_by_item/properties_group_by_item.js` | 84 | Group-by dropdown item that lazily loads property definitions for grouping |
| `search/search_arch_parser.js` | 508 | Parses search view XML arch into structured filter, groupby, and search panel items |
| `search/search_bar/search_bar.js` | 817 | Search bar with autocomplete suggestions, facet display, and keyboard navigation |
| `search/search_bar/search_bar_toggler.js` | 65 | Toggle button and hook for responsive search bar visibility on small screens |
| `search/search_bar_menu/search_bar_menu.js` | 204 | Dropdown menu grouping Filter, Group By, Favorites, and search panels |
| `search/search_context.js` | 75 | Context computation utilities for SearchModel |
| `search/search_domain.js` | 293 | Domain computation utilities for SearchModel |
| `search/search_enrichment.js` | 77 | Pure search-item enrichment producing activated copies with period/interval metadata |
| `search/search_facets.js` | 156 | Facet building utilities for SearchModel |
| `search/search_favorites.js` | 182 | Favorites/ir.filters utilities for SearchModel |
| `search/search_group_by.js` | 188 | GroupBy/OrderBy computation utilities for SearchModel |
| `search/search_model.js` | 1,636 | Search state machine managing facets, domains, groupbys, favorites, and comparisons |
| `search/search_panel/search_panel.js` | 507 | Sidebar filter panel with category trees and grouped checkbox filters |
| `search/search_panel_fetch.js` | 110 | Search panel section tree creation utilities |
| `search/search_properties.js` | 228 | Property-field search logic for lazy-loading definitions and creating search items |
| `search/search_split_domain.js` | 149 | Domain-splitting logic that decomposes compound filters into individual search items |
| `search/search_state.js` | 150 | State serialization, shared constants, and section helpers for SearchModel |
| `search/utils/dates.js` | 413 | Date period/quarter/interval option definitions and domain generators for search filters |
| `search/utils/group_by.js` | 62 | Group-by descriptor parser and interval validation for search queries |
| `search/utils/misc.js` | 32 | Shared constants for search facet icons, colors, and groupable field types |
| `search/with_search/with_search.js` | 112 | Wrapper component that creates a SearchModel and injects it into the sub-environment |

## services/ (32 files, 5,825 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `services/commands/command_category.js` | 21 | (generated/vendored — no description) |
| `services/commands/command_hook.js` | 25 | useCommand hook to register/unregister commands with component lifecycle |
| `services/commands/command_palette.js` | 466 | Command palette dialog with fuzzy search, namespaces, and keyboard navigation |
| `services/commands/command_service.js` | 294 | Service that registers, manages, and opens the command palette |
| `services/commands/default_providers.js` | 155 | Default command palette providers: hotkey badges, clickable elements, setup registry |
| `services/currency.js` | 112 | Currency lookup, formatting, and exchange rate fetching |
| `services/debug/debug_context.js` | 151 | Debug context manager that collects and merges debug menu items by category |
| `services/debug/debug_menu.js` | 75 | Extended debug menu with command palette integration |
| `services/debug/debug_menu_basic.js` | 70 | Base debug menu dropdown grouped by section (Record, UI, Security, etc.) |
| `services/debug/debug_menu_items.js` | 114 | (generated/vendored — no description) |
| `services/debug/debug_providers.js` | 80 | (generated/vendored — no description) |
| `services/debug/debug_utils.js` | 23 | Opens a form view action for a given model/record in debug mode |
| `services/error_service.js` | 241 | Global error/rejection interceptor with UncaughtError classification and handler pipeline |
| `services/field_service.js` | 292 | Service for loading field definitions, paths, and property definitions from the ORM |
| `services/file_upload_service.js` | 188 | XHR-based file upload service with progress tracking and event bus |
| `services/frequent_emoji_service.js` | 60 | Tracks and retrieves frequently used emojis from localStorage |
| `services/hotkeys/hotkey_hook.js` | 23 | useHotkey hook to register/unregister keyboard shortcuts with component lifecycle |
| `services/hotkeys/hotkey_service.js` | 529 | Keyboard shortcut registration, dispatch, and overlay access-key management |
| `services/http_service.js` | 66 | Simple HTTP GET/POST helpers with status checking and FormData support |
| `services/index.js` | 7 | (generated/vendored — no description) |
| `services/install_scoped_app/install_scoped_app.js` | 63 | Public page component for installing scoped Progressive Web Apps |
| `services/localization_service.js` | 151 | Fetches translations and configures Luxon locale, numbering system, and date/number formats |
| `services/name_service.js` | 135 | Batched and cached display_name lookups across arbitrary models |
| `services/navigation/navigation.js` | 472 | Keyboard arrow-key navigation hook for selectable item lists |
| `services/orm_service.js` | 451 | ORM RPC client for CRUD, read_group, and x2many command helpers |
| `services/pwa/install_prompt.js` | 39 | Dialog showing Safari-specific PWA installation instructions (iOS and macOS) |
| `services/pwa/pwa_service.js` | 256 | PWA install service: manages beforeinstallprompt, manifest fetch, and Safari fallback |
| `services/scss_error_display.js` | 72 | Detects SCSS compilation errors in stylesheets and shows a sticky notification |
| `services/sortable_service.js` | 115 | Service for creating sortable drag-and-drop outside OWL component lifecycle |
| `services/title_service.js` | 90 | Manages the document title with named parts and notification counters |
| `services/tree_processor_service.js` | 608 | Converts domains to condition trees with human-readable descriptions and tooltips |
| `services/user.js` | 381 | (generated/vendored — no description) |

## ui/ (21 files, 2,677 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `ui/block/block_ui.js` | 104 | Full-screen overlay component that blocks UI during long-running operations |
| `ui/block/ui_service.js` | 276 | UI service: viewport size tracking, active element management, block/unblock, and focus trapping |
| `ui/bottom_sheet/bottom_sheet.js` | 358 | Mobile-friendly slide-up panel with drag-to-dismiss and snap points |
| `ui/bottom_sheet/bottom_sheet_service.js` | 79 | Service for programmatically showing mobile bottom sheet overlays |
| `ui/dialog/confirmation_dialog.js` | 119 | Standard confirm/cancel dialog with async button handling |
| `ui/dialog/dialog.js` | 172 | Modal dialog component with dragging, hotkey escape, and active element focus trap |
| `ui/dialog/dialog_service.js` | 117 | Service for programmatically opening, stacking, and closing modal dialogs |
| `ui/effects/effect_service.js` | 92 | Service that triggers visual effects (rainbow man) via the effects registry |
| `ui/effects/rainbow_man.js` | 82 | Animated rainbow celebration overlay with configurable message and fadeout |
| `ui/index.js` | 53 | (generated/vendored — no description) |
| `ui/notification/notification.js` | 101 | Individual notification toast with auto-close progress bar and action buttons |
| `ui/notification/notification_container.js` | 29 | Renders all active notifications with fade-out transitions |
| `ui/notification/notification_service.js` | 76 | Service that manages toast notifications displayed in the top-right corner |
| `ui/overlay/overlay_container.js` | 115 | Renders overlay entries (popovers, dialogs, effects) with nested click-away tracking |
| `ui/overlay/overlay_service.js` | 77 | Low-level service for adding/removing overlay components (popovers, dialogs, effects) |
| `ui/popover/popover.js` | 334 | Positioned popover component with click-away close, hotkey escape, and arrow rendering |
| `ui/popover/popover_hook.js` | 78 | usePopover hook for open/close lifecycle management within OWL components |
| `ui/popover/popover_service.js` | 87 | Service for programmatically attaching popover components to target elements |
| `ui/tooltip/tooltip.js` | 16 | Simple tooltip component rendered by the tooltip service |
| `ui/tooltip/tooltip_hook.js` | 20 | useTooltip hook to attach tooltips to OWL component refs |
| `ui/tooltip/tooltip_service.js` | 292 | Service for data-tooltip attribute-driven tooltips with hover/touch support |

## views/ (119 files, 25,314 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `views/action_helper.js` | 21 | Empty-state placeholder shown when a view has no records |
| `views/calendar/calendar_arch_parser.js` | 198 | Parses calendar view XML arch into field mappings, scales, filters, and popover config |
| `views/calendar/calendar_common/calendar_common_popover.js` | 150 | Popover for calendar events in day/week/month scales |
| `views/calendar/calendar_common/calendar_common_renderer.js` | 489 | FullCalendar renderer for day/week/month scales |
| `views/calendar/calendar_common/calendar_common_week_column.js` | 36 | Inserts week-number columns into FullCalendar grid headers and body rows |
| `views/calendar/calendar_controller.js` | 502 | Calendar view orchestrator: date navigation, event CRUD, quick-create, and multi-selection |
| `views/calendar/calendar_date_range.js` | 109 | Pure date range computation, range domain building, and filter domain assembly for calendar |
| `views/calendar/calendar_filter_section/calendar_filter_section.js` | 205 | Collapsible sidebar filter section for a calendar filter field (attendees, resources) |
| `views/calendar/calendar_model.js` | 1,020 | Calendar event data loading, filter sections, and timezone handling (delegates range/filter computation to calendar_date_range.js, normalization to calendar_record.js) |
| `views/calendar/calendar_record.js` | 84 | Calendar record normalization: raw ORM record to calendar event with duration, colors, and display flags |
| `views/calendar/calendar_renderer.js` | 67 | Top-level calendar renderer delegating to scale-specific sub-renderers |
| `views/calendar/calendar_side_panel/calendar_side_panel.js` | 65 | Side panel with date picker and filter sections for the calendar view |
| `views/calendar/calendar_utils.js` | 86 | Utility functions for calendar record-to-event conversion, color mapping, and date formatting |
| `views/calendar/calendar_view.js` | 38 | Calendar view descriptor registered in the view registry |
| `views/calendar/calendar_year/calendar_year_popover.js` | 109 | Popover listing grouped records when clicking a day cell in year view |
| `views/calendar/calendar_year/calendar_year_renderer.js` | 246 | Year-scale renderer displaying 12 mini month grids with background events |
| `views/calendar/hooks/calendar_popover_hook.js` | 71 | Hook managing calendar event popovers with desktop/mobile responsive behavior |
| `views/calendar/hooks/full_calendar_hook.js` | 74 | Hook managing FullCalendar instance lifecycle (load, render, refresh, destroy) |
| `views/calendar/hooks/square_selection_hook.js` | 280 | Drag-to-select date range hook for month-view calendar cells |
| `views/calendar/mobile_filter_panel/calendar_mobile_filter_panel.js` | 48 | Compact filter panel for mobile calendar with sidebar toggle |
| `views/calendar/quick_create/calendar_quick_create.js` | 90 | Lightweight dialog for creating a calendar event with just a title |
| `views/debug_items.js` | 518 | Debug menu entries: view arch inspection, field metadata, asset management, and technical info |
| `views/form/button_box/button_box.js` | 46 | Responsive stat-button container with overflow dropdown for form views |
| `views/form/form_arch_parser.js` | 74 | Parses form view XML arch into field/widget descriptors, active actions, and autofocus targets |
| `views/form/form_cog_menu/form_cog_menu.js` | 10 | Form-view variant of the cog menu with save-before-action behavior |
| `views/form/form_compiler.js` | 808 | Compiles form view XML arch into OWL template AST with layout, notebook, and field handling |
| `views/form/form_controller.js` | 721 | Form view lifecycle: record save, discard, duplicate, archive, pager navigation, and error recovery |
| `views/form/form_error_dialog/form_error_dialog.js` | 59 | Error dialog shown on form save failure with discard/redirect/stay options |
| `views/form/form_group/form_group.js` | 112 | OuterGroup and InnerGroup components for form view column layout |
| `views/form/form_label.js` | 74 | Label component for form fields with tooltip, validity, and company-dependent indicators |
| `views/form/form_renderer.js` | 175 | Compiles form arch into an OWL template and manages autofocus, sticky statusbar, and field ID uniqueness |
| `views/form/form_status_indicator/form_status_indicator.js` | 62 | Save/discard indicator shown when the form record is dirty or invalid |
| `views/form/form_utils.js` | 119 | Utility functions for form views (sub-view loading, discard hooks, toolbar setup) |
| `views/form/form_view.js` | 43 | View registry descriptor for the standard form view |
| `views/form/setting/setting.js` | 74 | Individual setting row with label, help text, and company-dependent icon |
| `views/form/status_bar_buttons/status_bar_buttons.js` | 29 | Renders action buttons in the form status bar with overflow dropdown |
| `views/graph/graph_arch_parser.js` | 127 | Parses graph view XML arch into chart mode, measures, groupBy, and display flags |
| `views/graph/graph_controller.js` | 81 | Controller wiring GraphModel to GraphRenderer with search bar and sample data support |
| `views/graph/graph_model.js` | 582 | Chart data fetching, groupBy processing, measure aggregation, and dataset preparation |
| `views/graph/graph_renderer.js` | 1,006 | Chart.js integration for rendering bar, line, and pie charts with tooltips and legends |
| `views/graph/graph_search_model.js` | 51 | SearchModel extension restoring graph_groupbys from saved favorites |
| `views/graph/graph_view.js` | 67 | Graph view descriptor registered in the view registry |
| `views/index.js` | 18 | (generated/vendored — no description) |
| `views/kanban/kanban_arch_parser.js` | 292 | Parses kanban view XML arch into card templates, field nodes, progress bars, and quick-create config |
| `views/kanban/kanban_cog_menu.js` | 24 | Kanban cog menu that hides registry items during multi-select operations |
| `views/kanban/kanban_column_examples_dialog.js` | 87 | Dialog showcasing example column layouts for kanban board setup |
| `views/kanban/kanban_column_quick_create.js` | 109 | Inline quick-create widget for adding new kanban columns (groups) |
| `views/kanban/kanban_compiler.js` | 212 | Template compiler transforming kanban card/menu arch into OWL-compatible templates |
| `views/kanban/kanban_controller.js` | 454 | Controller for the kanban view with grouping, quick-create, and progress bar support |
| `views/kanban/kanban_cover_image_dialog.js` | 103 | Dialog for selecting, uploading, or removing a cover image on a kanban record |
| `views/kanban/kanban_dropdown_menu_wrapper.js` | 34 | Wrapper adding keyboard navigation classes and close-on-click to kanban dropdown menus |
| `views/kanban/kanban_header.js` | 189 | Column header with group title, record count, progress bar, and fold/edit/delete cog menu |
| `views/kanban/kanban_record.js` | 449 | Individual kanban card component with compiled template, color strips, cover images, and action handling |
| `views/kanban/kanban_record_quick_create.js` | 327 | Inline mini-form for quick-creating records within a kanban column |
| `views/kanban/kanban_renderer.js` | 804 | Card layout, column grouping, drag-and-drop reorder, and quick-create for kanban view |
| `views/kanban/kanban_view.js` | 58 | Kanban view descriptor registered in the view registry |
| `views/kanban/progress_bar_hook.js` | 543 | Progress bar state computation, active bar filtering, and per-group aggregate tracking for kanban columns |
| `views/list/column_width_hook.js` | 611 | Column width calculation, min/max enforcement, and resize-freeze hook for list view |
| `views/list/export_all/export_all.js` | 46 | Cog-menu item triggering direct XLSX export of all records |
| `views/list/list_aggregates.js` | 332 | Hook computing column aggregates and multi-currency popovers for the list view |
| `views/list/list_aggregates_row.js` | 182 | Footer aggregate row component for ListRenderer |
| `views/list/list_arch_parser.js` | 358 | Parses list view XML arch into column definitions, groupby configs, buttons, and decorations |
| `views/list/list_cog_menu.js` | 23 | List-view cog menu that hides registry items when records are selected |
| `views/list/list_column_utils.js` | 83 | Column processing utilities for ListRenderer |
| `views/list/list_confirmation_dialog.js` | 135 | Confirmation dialog for multi-record bulk edits showing affected records and changed values |
| `views/list/list_controller.js` | 587 | List view orchestrator: pagination, selection, inline editing, multi-edit, and export |
| `views/list/list_grid_state.js` | 461 | Pure state object materializing flat row arrays for index-based list view grid navigation |
| `views/list/list_group_layout.js` | 144 | Group header layout utilities for ListRenderer |
| `views/list/list_keyboard_edit.js` | 369 | Edit-mode keyboard handlers (enter/escape, tab, multi-edit) for list view inline editing |
| `views/list/list_keyboard_nav.js` | 582 | Keyboard navigation hook for arrow, tab, and enter key traversal across list view cells |
| `views/list/list_optional_fields.js` | 143 | Hook managing localStorage-backed optional column visibility for the list view |
| `views/list/list_renderer.js` | 1,623 | Table rendering, inline editing, column resize, and drag-and-drop for list view |
| `views/list/list_selection.js` | 224 | Hook for checkbox selection, shift-range selection, and long-touch selection in list views |
| `views/list/list_view.js` | 57 | List (tree) view descriptor registered in the view registry |
| `views/list/list_virtualization.js` | 236 | Row virtualization hook rendering only visible rows plus buffer for large list views |
| `views/module_views.js` | 42 | Cog-menu item to reset ir.module.module installation state |
| `views/multi_record_controller.js` | 256 | Base controller class for multi-record views (list, kanban) |
| `views/pivot/pivot_arch_parser.js` | 125 | Parses pivot view XML arch into measures, row/column groupBy, and display flags |
| `views/pivot/pivot_controller.js` | 103 | Controller wiring PivotModel to PivotRenderer with search bar and scroll restoration |
| `views/pivot/pivot_group_tree.js` | 128 | Tree data structure for managing pivot table row/column group hierarchies |
| `views/pivot/pivot_measurements.js` | 155 | Builds measure specs (fieldName:aggregator) and data comparison logic for the pivot model |
| `views/pivot/pivot_model.js` | 1,038 | Pivot table data loading, group tree expansion, measure aggregation, and cell computation (delegates export formatting to pivot_export.js) |
| `views/pivot/pivot_export.js` | 70 | Pure formatting of pivot table data for Excel/spreadsheet export |
| `views/pivot/pivot_renderer.js` | 402 | Renders the pivot table HTML with expandable row/column headers, measures dropdown, and XLSX export |
| `views/pivot/pivot_search_model.js` | 52 | SearchModel extension restoring pivot_row_groupby from saved favorites |
| `views/pivot/pivot_table.js` | 157 | (generated/vendored — no description) |
| `views/pivot/pivot_value_utils.js` | 159 | GroupBy normalization, value sanitization, and header cell computation for the pivot model |
| `views/pivot/pivot_view.js` | 72 | Pivot view descriptor registered in the view registry |
| `views/standard_view_props.js` | 36 | Shared OWL props validation shape for all standard view controllers |
| `views/view.js` | 536 | Generic view loader: resolves arch, fields, and compiler then renders the appropriate view component |
| `views/view_button/multi_record_view_button.js` | 37 | ViewButton variant for list/kanban headers that operates on multiple selected records |
| `views/view_button/view_button.js` | 183 | Renders arch button elements with debouncing, tooltips, and Bootstrap class resolution |
| `views/view_button/view_button_hook.js` | 179 | Hook wiring view button click handling with confirmation dialogs and UI blocking |
| `views/view_buttons.js` | 75 | Parses arch button nodes into structured click-param descriptors |
| `views/view_compiler.js` | 505 | Base view compiler: transforms XML arch nodes into OWL template elements with attribute and slot helpers |
| `views/view_components/animated_number.js` | 108 | Numeric display with smooth CSS animation on value changes and optional multi-currency popover |
| `views/view_components/column_progress.js` | 27 | Progress bar with colored segments for kanban column group aggregates |
| `views/view_components/group_config_menu.js` | 125 | Dropdown menu on grouped column headers for editing/deleting the group's relational value |
| `views/view_components/multi_create_popover.js` | 106 | Popover with mini form and optional time range picker for quick-creating records |
| `views/view_components/multi_currency_popover.js` | 63 | Popover showing a monetary value converted into each active company currency |
| `views/view_components/multi_selection_buttons.js` | 277 | Floating toolbar with Add/Cancel/Delete for multi-record selection in calendar/gantt views |
| `views/view_components/report_view_measures.js` | 21 | Dropdown selector for choosing numeric measures in pivot/graph report views |
| `views/view_components/selection_box.js` | 53 | Banner with "Select all matching" and "Unselect" actions shown when records are selected |
| `views/view_components/view_scale_selector.js` | 30 | Dropdown for switching between time scales (day/week/month/year) in calendar and gantt views |
| `views/view_dialogs/export_data_dialog.js` | 535 | Export configuration dialog: field selection, template management, and format options |
| `views/view_dialogs/form_view_dialog.js` | 145 | Modal dialog embedding a full form view for creating or editing a single record |
| `views/view_dialogs/select_create_dialog.js` | 146 | Modal with embedded list/kanban for selecting existing records or creating new ones (Many2one/Many2many) |
| `views/view_hook.js` | 261 | Hooks for action links, record export, and record deletion in views |
| `views/view_measurements.js` | 120 | Computes available report measures from field definitions and active selections |
| `views/view_service.js` | 137 | Service that loads, caches, and invalidates view descriptions (arch, filters, action menus) |
| `views/view_utils.js` | 311 | Shared utilities for view controllers (class names, active actions, archive, formatting) |
| `views/widgets/attach_document/attach_document.js` | 101 | Widget button that uploads files as ir.attachment records and optionally calls a model action |
| `views/widgets/documentation_link/documentation_link.js` | 66 | Widget rendering a hyperlink to versioned Odoo documentation |
| `views/widgets/notification_alert/notification_alert.js` | 27 | Widget displaying a warning banner when browser push notifications are blocked |
| `views/widgets/ribbon/ribbon.js` | 70 | Decorative ribbon on the top-right corner of a form view with configurable label and color |
| `views/widgets/signature/signature.js` | 98 | Widget opening a signature drawing dialog and writing the captured image to a Binary field |
| `views/widgets/standard_widget_props.js` | 9 | Standard OWL prop definitions shared by all view widgets (record and readonly) |
| `views/widgets/week_days/week_days.js` | 62 | Widget rendering seven day-of-week checkboxes respecting the locale's week start day |
| `views/widgets/widget.js` | 154 | Generic widget component resolving view_widgets registry entries with props extraction and validation |

## webclient/ (70 files, 8,446 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `webclient/actions/action_button_executor.js` | 209 | Executes action buttons (type=object/action/special) with RPC, context filtering, and UI blocking |
| `webclient/actions/action_constants.js` | 43 | Constants (dialog sizes, context key regex, embedded action keys) and ID parsing for the action service |
| `webclient/actions/action_container.js` | 41 | Thin OWL wrapper rendering the current action's component inside the action manager div |
| `webclient/actions/action_dialog.js` | 37 | Dialog subclass for rendering action components (target="new") with debug menu integration |
| `webclient/actions/action_info_builders.js` | 239 | Builds props, config, and state for client action and view controllers |
| `webclient/actions/action_install_kiosk_pwa.js` | 43 | Client action dialog displaying a kiosk PWA installation URL |
| `webclient/actions/action_service.js` | 1,302 | Action manager that routes server/client actions to views, dialogs, and URL redirects |
| `webclient/actions/action_state.js` | 204 | URL state serialization/deserialization for the action service (router integration) |
| `webclient/actions/action_views.js` | 47 | View lookup and action display mode resolution for the action service |
| `webclient/actions/breadcrumb_manager.js` | 217 | Breadcrumb building, display-name loading, and virtual controller reconstruction for the action service |
| `webclient/actions/client_actions.js` | 127 | Built-in client actions (display_notification, soft_reload, reload_context) |
| `webclient/actions/debug_items.js` | 229 | Debug menu items for editing actions and views in the admin editor |
| `webclient/actions/reports/report_action.js` | 63 | Client action rendering an HTML report in an iframe with print button and action link enrichment |
| `webclient/actions/reports/report_executor.js` | 133 | Executes ir.actions.report as HTML preview or PDF/text download |
| `webclient/actions/reports/report_hook.js` | 76 | Hook enriching DOM elements with [res-id][res-model] into clickable action links |
| `webclient/actions/reports/utils.js` | 55 | Report URL generation and download helper for ir.actions.report |
| `webclient/actions/skeleton_view.js` | 40 | Shimmer loading placeholder shown during view transitions to replace blank screens |
| `webclient/burger_menu/burger_menu.js` | 77 | Fullscreen mobile menu displaying user menu, company switcher, and current app sub-menus |
| `webclient/burger_menu/burger_user_menu/burger_user_menu.js` | 20 | Mobile variant of the user menu shown inside the burger menu overlay |
| `webclient/burger_menu/mobile_switch_company_menu/mobile_switch_company_menu.js` | 32 | Mobile company switcher with collapsible toggle for many companies |
| `webclient/clickbot/clickbot.js` | 589 | Automated UI testing bot that clicks through all apps, views, and filters to verify stability |
| `webclient/clickbot/clickbot_loader.js` | 47 | Debug menu item that loads and runs the click-everywhere automated test bot |
| `webclient/currency_service.js` | 40 | Service that auto-reloads currencies when res.currency records are mutated |
| `webclient/debug/debug_items.js` | 72 | Debug menu items for running unit tests, opening views, and toggling technical data |
| `webclient/debug/profiling/profiling_item.js` | 38 | Debug menu dropdown item for toggling SQL/trace profiling collectors |
| `webclient/debug/profiling/profiling_qweb.js` | 395 | Field widget visualizing QWeb template profiling data as a flamegraph |
| `webclient/debug/profiling/profiling_service.js` | 129 | Service managing Python profiling session state, collector toggles, and systray indicator |
| `webclient/debug/profiling/profiling_systray_item.js` | 15 | Systray indicator icon shown when Python profiling is active |
| `webclient/density/density_service.js` | 73 | Service managing content density (default/compact/condensed) via body CSS class toggles |
| `webclient/density/density_toggle.js` | 49 | Systray toggle that cycles through content density modes (default/compact/condensed) |
| `webclient/errors/offline_fail_to_fetch_error_handler.js` | 39 | Error handler converting browser "Failed to fetch" TypeErrors into ConnectionLostError |
| `webclient/errors/visitor_error_handler.js` | 33 | Error handler that swallows all tracebacks for non-internal (portal/public) users |
| `webclient/index.js` | 28 | (generated/vendored — no description) |
| `webclient/loading_indicator/loading_indicator.js` | 72 | Loading indicator counting active RPCs and blocking the UI after a 3s delay |
| `webclient/menus/menu_helpers.js` | 95 | Utility functions to traverse the menu tree and compute flat app/menuItem lists for HomeMenu |
| `webclient/menus/menu_providers.js` | 99 | Command palette providers for app and menu item fuzzy search |
| `webclient/menus/menu_service.js` | 146 | Service that loads, caches, and navigates the Odoo menu tree |
| `webclient/navbar/navbar.js` | 287 | Main navigation bar with app switcher, sub-menus, systray items, and mobile sidebar |
| `webclient/reload_company_service.js` | 29 | Service that triggers a page reload when res.company records are modified |
| `webclient/res_user_group_ids_field/res_user_group_ids_field.js` | 303 | Field widget for visualizing and configuring res.users access rights (group_ids) |
| `webclient/res_user_group_ids_field/res_user_group_ids_popover.js` | 96 | Popover showing group implication details (implied-by, implies, disjoint) |
| `webclient/res_user_group_ids_field/res_user_group_ids_privilege_field.js` | 121 | Boolean/selection field for privilege toggles within the dynamically generated access rights form |
| `webclient/session_service.js` | 37 | Service that lazy-loads additional session info after the web client is ready |
| `webclient/settings_form_view/fields/settings_binary_field/settings_binary_field.js` | 32 | BinaryField variant resolving download URLs via the related field's relation |
| `webclient/settings_form_view/fields/upgrade_boolean_field.js` | 51 | Boolean field for settings that shows an Enterprise upgrade dialog when checked |
| `webclient/settings_form_view/fields/upgrade_dialog.js` | 31 | Dialog prompting the user to upgrade to Odoo Enterprise |
| `webclient/settings_form_view/highlight_text/form_label_highlight_text.js` | 23 | FormLabel variant with search-term highlighting and enterprise upgrade badge |
| `webclient/settings_form_view/highlight_text/highlight_text.js` | 25 | Component rendering text with the current search term highlighted via markup |
| `webclient/settings_form_view/highlight_text/settings_radio_field.js` | 26 | RadioField variant with search-term highlighting on option labels |
| `webclient/settings_form_view/settings/searchable_setting.js` | 66 | Setting variant with search-based visibility filtering and URL hash highlighting |
| `webclient/settings_form_view/settings/setting_header.js` | 36 | Setting variant for header-type fields displayed in the app header row |
| `webclient/settings_form_view/settings/settings_app.js` | 39 | Container for a single app's settings tab content, hidden when search yields no matches |
| `webclient/settings_form_view/settings/settings_block.js` | 79 | Collapsible group of settings within an app tab with search-based visibility toggling |
| `webclient/settings_form_view/settings/settings_page.js` | 119 | Top-level settings page with app tabs, swipe navigation, and URL hash-based tab/anchor selection |
| `webclient/settings_form_view/settings_confirmation_dialog.js` | 27 | Three-way dialog (Save/Discard/Stay) for unsaved settings changes |
| `webclient/settings_form_view/settings_form_compiler.js` | 143 | Compiler transforming settings arch (app/block elements) into SettingsPage/SettingsApp components |
| `webclient/settings_form_view/settings_form_controller.js` | 180 | Controller for res.config.settings with search filtering and save-via-Apply behavior |
| `webclient/settings_form_view/settings_form_renderer.js` | 42 | FormRenderer subclass registering settings-specific sub-components (search highlight, tabs) |
| `webclient/settings_form_view/settings_form_view.js` | 89 | View descriptor for the settings form view (base_setup) with custom record, model, and compiler |
| `webclient/settings_form_view/widgets/demo_data_service.js` | 23 | Service that checks whether demo data is active in the current database |
| `webclient/settings_form_view/widgets/res_config_dev_tool.js` | 58 | Developer Tools settings widget for toggling debug modes and installing demo data |
| `webclient/settings_form_view/widgets/res_config_edition.js` | 40 | About section settings widget showing Odoo version, expiration date, and copyrights |
| `webclient/settings_form_view/widgets/res_config_invite_users.js` | 164 | Settings widget for inviting users by email with validation and pending-invitation list |
| `webclient/settings_form_view/widgets/user_invite_service.js` | 23 | Service that fetches and caches pending user invitation data from /base_setup/data |
| `webclient/share_target/share_target_service.js` | 76 | Service receiving shared files from the PWA service worker (Web Share Target API) |
| `webclient/switch_company_menu/switch_company_item.js` | 50 | Single company row in the switch-company dropdown with toggle and log-into actions |
| `webclient/switch_company_menu/switch_company_menu.js` | 438 | Company switcher systray dropdown with multi-select, search, and access-rights verification |
| `webclient/user_menu/user_menu.js` | 54 | Systray dropdown displaying current user avatar and menu items from the user_menuitems registry |
| `webclient/user_menu/user_menu_items.js` | 191 | User menu item factories registered in user_menuitems registry (help, shortcuts, preferences, PWA install, log out) |
| `webclient/webclient.js` | 255 | Root OWL component bootstrapping the action manager, navbar, and main components container |

## (root) (4 files, 774 lines)

| File | Lines | Purpose |
|------|------:|---------|
| `env.js` | 277 | OWL environment factory, service dependency resolution, and app mounting |
| `module_loader.js` | 264 | Bootstrap module loader that resolves dependency graphs and defines odoo.loader |
| `service_worker.js` | 222 | PWA service worker handling Web Share Target file reception |
| `session.js` | 11 | Server-injected session info singleton (user, db, context) captured at page load |
