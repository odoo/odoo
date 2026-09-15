# Directory Map

> **249 entries** (248 subdirectories + `(root)`) | Maps directory → layer + responsibility
>
> Layers (Feature-Sliced Design): shared → entities → features → widgets → pages
>
> `Files` counts `*.js` directly in the directory, not recursively.
> A directory whose name matches a sibling `<name>.js` one level up is fronted by
> that **module face**: the face re-exports the directory's published surface, and
> consumers import the face. See `ARCHITECTURE.md` → *Module faces*.

| Directory | Layer | Files | Primary Responsibility |
|-----------|-------|------:|----------------------|
| `(root)` | misc | 4 | `env.js`, `session.js`, `module_loader.js` (loader shim, no `@ts-check`), `service_worker.js` (classic script) |
| `@types/` | misc | 0 | Ambient `.d.ts` declarations: env, context, fields, models, registries, services, views, owl, user |
| `@types/models/` | misc | 0 | Model-layer ambient types (`_runtime.d.ts`) |
| `@types/registries/` | misc | 0 | Registry ambient types (fields, services, views, command, debug, view_widgets) |
| `boot/` | misc | 2 | `main.js` / `start.js` — backend entry points that build the env and mount `WebClient` |
| `components/` | features | 33 | Module faces for the component directories below (barcode, datetime, dropdown, dropzone, editor_dialog, file_upload, file_viewer, model_field_selector, record_selectors, signature, tree_editor) |
| `components/action_swiper/` | features | 1 | Touch swipe component that triggers actions on left/right swipe gestures |
| `components/autocomplete/` | features | 2 | Generic autocomplete dropdown with multi-source results and keyboard navigation, plus the shared quick-search core (`name_search.js`) both record autocompletes consume |
| `components/barcode/` | features | 4 | Camera barcode scanning: video scanner, its dialog, a draggable crop overlay, and a ZXing `BarcodeDetector` polyfill |
| `components/checkbox/` | features | 1 | Accessible checkbox component with label slot and hotkey support |
| `components/code_editor/` | features | 2 | Ace-based code editor component with syntax highlighting and theme support |
| `components/color_picker/` | features | 1 | Color picker shell hosting the tabs registered in `color_picker_tabs` |
| `components/color_picker/custom_color_picker/` | features | 1 | HSL/RGB picker with canvas gradient, sliders, and hex input |
| `components/color_picker/tabs/` | features | 2 | The two registered tabs: a solid palette and a custom colour input |
| `components/colorlist/` | features | 1 | Expandable swatch picker over the predefined Odoo colour indices |
| `components/copy_button/` | features | 1 | Clipboard copy button with success tooltip feedback |
| `components/datetime/` | features | 5 | Date/time picking: calendar picker, hosting popover, text input, the binding hook, and the `datetime_picker` service |
| `components/domain_selector/` | features | 3 | Visual domain builder converting between string domains and tree editors |
| `components/domain_selector_dialog/` | features | 1 | Modal dialog for editing and validating an Odoo domain |
| `components/dropdown/` | features | 6 | Dropdown system: toggler, menu items (plain, checkbox, accordion), grouping, shared open/close state hooks |
| `components/dropdown/_behaviours/` | features | 3 | Dropdown internals: group membership, parent/child nesting and peer closing, the hosting popover |
| `components/dropzone/` | features | 2 | Visual drop target overlay tracking drag enter/leave and firing `onDrop` |
| `components/editor_dialog/` | features | 1 | Base for a dialog around one validated value; `DomainSelectorDialog` and `ExpressionEditorDialog` derive from it |
| `components/emoji_picker/` | features | 3 | Emoji data (generated), the picker UI, and the `web.frequent.emoji` frequency service |
| `components/errors/` | features | 2 | Error dialog components (RPC, client, network, validation) and the `connection_recovery` handler service |
| `components/expression_editor/` | features | 2 | Visual tree editor for Python expressions with field-path selection |
| `components/expression_editor_dialog/` | features | 1 | Modal dialog for editing Python expressions with validation preview |
| `components/file_input/` | features | 1 | File upload input with route-based server upload and multi-file support |
| `components/file_upload/` | features | 3 | Upload progress UI: the bar with its cancel action plus the per-record and container wrappers for kanban/list |
| `components/file_viewer/` | features | 3 | Attachment viewer with zoom/rotate, the hook that mounts it, and `FileModelMixin` |
| `components/model_field_selector/` | features | 2 | Field-path selector with breadcrumb display and popover field browser |
| `components/model_selector/` | features | 1 | Autocomplete for searching and selecting Odoo model names |
| `components/notebook/` | features | 1 | Tabbed notebook rendering one page at a time |
| `components/pager/` | features | 2 | Pagination with editable range input, and the transient small-screen indicator |
| `components/record_selectors/` | features | 6 | Record pickers over `AutoComplete`: single and multi selectors, shared display-name loading, tag keyboard navigation |
| `components/resizable_panel/` | features | 2 | Side panel with a drag handle for interactive width resizing |
| `components/select_menu/` | features | 1 | Searchable select menu with multi-select tags and keyboard navigation |
| `components/signature/` | features | 3 | Signature pad with draw, auto-generate, and load modes (lazy `signature_pad` import) |
| `components/tags_list/` | features | 1 | Renders coloured tags with an optional visibility limit and overflow counter |
| `components/time_picker/` | features | 1 | Time input with dropdown hour/minute selection and configurable rounding |
| `components/tree_editor/` | features | 5 | UI-layer tree editor components. Data-only tree manipulation lives in `core/tree/` |
| `components/user_switch/` | features | 1 | Login-page component for switching between recently connected accounts |
| `core/` | shared | 33 | Namespace-root primitives: registry, domain, context, parsers/formatters, templates, events, asset loading, translation, feature flags, user, currency, the compiled-template cache, and the `field` / `name` / `allowed_qweb_expressions` / `multi_company_recovery` services |
| `core/avatar/` | shared | 0 | Avatar component styles (SCSS only) |
| `core/badge/` | shared | 1 | Badge colour helpers plus component styles |
| `core/browser/` | shared | 8 | Browser abstraction: the `browser` indirection object, cookies, storage, router, hotkey key normalisation, anchor-scroll suppression, feature detection, and the `title` service |
| `core/colors/` | shared | 1 | Shared colour palettes, allocation policies and public colour operations |
| `core/debug/` | shared | 4 | Debug context manager merging `debug` registry items by category, plus its utilities |
| `core/errors/` | shared | 6 | The `error` service, uncaught-error handlers, traceback formatting, native stack-frame parsing, and the `/web/observability/js_error` beacon |
| `core/file_upload/` | shared | 2 | `FileHandler` component and the `file_upload` service (XHR upload with progress) |
| `core/flow_editor/` | shared | 7 | The node-graph editor: store, canvas, node/port/connection components and the structural connection validator |
| `core/flow_editor/geometry/` | shared | 6 | Its geometry: coordinate transforms, node rects, port anchors and the orthogonal router that avoids other nodes |
| `core/hotkeys/` | shared | 2 | The `hotkey` service and the `useHotkey` registration hook |
| `core/l10n/` | shared | 8 | Luxon-based date/datetime parsing, formatting, serialization, and the `localization` service |
| `core/l10n/utils/` | shared | 5 | Locale helpers: `Intl.ListFormat` list formatting, locale codes, normalisation, unaccent + its table |
| `core/lib/` | shared | 3 | Lazy ESM loaders for import-map libraries: `chartjs.js` (`loadChartJS`) and `fullcalendar.js` (`loadFullCalendar`) |
| `core/navigation/` | shared | 1 | Keyboard arrow-key navigation hook for selectable item lists |
| `core/network/` | shared | 12 | RPC stack: `rpc.js`, the x2many command constants, the RAM/IndexedDB cache, in-flight dedup, model-mutation constants, download helper, Content-Disposition parser, and the `orm` / `http` / `slow_rpc` / `result_set_cache_invalidator` services |
| `core/network/web_vitals/` | shared | 1 | `web_vitals` service — `PerformanceObserver` capture of LCP/FCP/CLS/TTFB/INP, beaconed to `/web/observability/cwv` on `pagehide` |
| `core/position/` | shared | 2 | Hook and geometry utilities for repositioning a popper element against a target |
| `core/py_js/` | shared | 17 | Python expression tokenizer, parser and interpreter used by `domain=` / `context=` evaluation |
| `core/tree/` | shared | 17 | Data-only condition-tree primitives: AST, domain ↔ tree ↔ Python-expression conversions, virtual operators, and the `tree_processor` service |
| `core/utils/` | shared | 28 | Cross-cutting utilities: reactivity (`SignalStore`, `effect`, `derived`), `patch`, concurrency, hooks, timing, IndexedDB, URLs, macros, PDF.js loader, render instrumentation |
| `core/utils/collections/` | shared | 3 | Array/object helpers: groupBy, sortBy, unique, intersection, cartesian, zip |
| `core/utils/dnd/` | shared | 11 | Drag-and-drop hook builders (`useDraggable`, `useSortable`, nested sortable) and the `sortable` service. The builder is split by what each part must know: `drag_session.js` holds the pointer state machine, `drag_geometry.js` the pure rect/pointer maths, `draggable_hook_params.js` parameter validation and context construction; only `draggable_hook_builder.js` touches OWL |
| `core/utils/dom/` | shared | 10 | DOM helpers: autoresize, class names, click-away, viewport units, events, HTML/Markup sanitisation, scrolling, XML, and the layout read/write batch mount hooks measure through |
| `core/utils/format/` | shared | 5 | Value formatting primitives: binary sizes, colours, digit precision, numbers, strings |
| `fields/` | features | 19 | Field infrastructure: `registerField()` / `registerFallbackField()`, the `Field` component, standard props, widths, tooltips, dirty signal, translation button/dialog, input hooks |
| `fields/basic/` | features | 5 | Shared bases for the basic widgets: numeric, text, trimming inputs, plus the `boolean_toggle` face |
| `fields/basic/boolean/` | features | 1 | Checkbox field widget for Boolean columns |
| `fields/basic/boolean_favorite/` | features | 1 | Star toggle field for marking records as favourites |
| `fields/basic/boolean_icon/` | features | 1 | Clickable icon field that toggles a Boolean value |
| `fields/basic/boolean_toggle/` | features | 2 | Toggle switch field widget for Boolean columns |
| `fields/basic/char/` | features | 1 | Single-line text input field for Char columns |
| `fields/basic/color/` | features | 1 | Native colour picker input field for Char columns |
| `fields/basic/copy_clipboard/` | features | 1 | Wrapper field adding a copy-to-clipboard button to Char/URL fields |
| `fields/basic/email/` | features | 1 | Email input field with mailto link in readonly mode |
| `fields/basic/float/` | features | 1 | Numeric input field for Float columns with locale-aware formatting |
| `fields/basic/float_factor/` | features | 1 | Float field applying a multiplication factor for display and storage |
| `fields/basic/float_time/` | features | 1 | Duration input storing hours as a float (1.5 = 1h30) |
| `fields/basic/float_toggle/` | features | 1 | Cyclic button stepping through a list of float values on click |
| `fields/basic/html/` | features | 1 | Simple HTML field widget extending TextField for Html columns |
| `fields/basic/integer/` | features | 1 | Numeric input field for Integer columns with locale-aware formatting |
| `fields/basic/json/` | features | 1 | Read-only display field for JSON columns |
| `fields/basic/json_checkboxes/` | features | 1 | Checkbox group backed by a JSON object of boolean flags |
| `fields/basic/monetary/` | features | 1 | Currency-aware numeric input field for Monetary columns |
| `fields/basic/percentage/` | features | 1 | Numeric input field displaying and parsing percentage values |
| `fields/basic/phone/` | features | 1 | Phone number input field with tel: link in readonly mode |
| `fields/basic/text/` | features | 1 | Multi-line textarea input field for Text columns |
| `fields/basic/url/` | features | 1 | URL input field with clickable hyperlink in readonly mode |
| `fields/display/` | features | 1 | Face for the read-only display widgets in the child directories |
| `fields/display/badge/` | features | 1 | Read-only badge pill for Selection and Many2one columns |
| `fields/display/contact_statistics/` | features | 1 | Read-only contact statistics summary widget |
| `fields/display/gauge/` | features | 1 | Chart.js doughnut gauge visualisation for numeric fields |
| `fields/display/handle/` | features | 1 | Drag handle icon for manual record reordering in list views |
| `fields/display/percent_pie/` | features | 1 | Pie chart showing a percentage value (registry key `percentpie`) |
| `fields/display/progress_bar/` | features | 2 | Progress-bar field and its kanban variant |
| `fields/display/stat_info/` | features | 1 | Stat button content showing a formatted value with a label (key `statinfo`) |
| `fields/display/statusbar/` | features | 1 | Horizontal pipeline status bar for Selection and Many2one columns |
| `fields/hooks/` | features | 2 | OWL hooks shared across field widgets (`record_observer.js`) |
| `fields/media/` | features | 0 | Widget category parent — see the child directories |
| `fields/media/attachment_image/` | features | 1 | Read-only image display field for Many2one attachment references |
| `fields/media/binary/` | features | 1 | File upload/download field for Binary columns |
| `fields/media/contact_image/` | features | 1 | Image field variant falling back to a preview image when empty |
| `fields/media/image/` | features | 2 | Image upload, preview, and zoom field for Binary image columns |
| `fields/media/image_url/` | features | 1 | Image display field loading from a URL stored in a Char column |
| `fields/media/pdf_viewer/` | features | 1 | Embedded PDF viewer field for Binary columns using PDF.js |
| `fields/media/signature/` | features | 1 | Signature pad field capturing and storing handwritten signatures |
| `fields/relational/` | features | 9 | Shared relational machinery: the `many2x` autocomplete, x2many CRUD/dialog plumbing, special-data loading, active-action resolution, plus the `many2one` / `many2many_tags` / `x2many` faces |
| `fields/relational/many2many_binary/` | features | 1 | File attachment list field for Many2many relations to `ir.attachment` |
| `fields/relational/many2many_checkboxes/` | features | 1 | Checkbox group field for Many2many relations |
| `fields/relational/many2many_tags/` | features | 2 | Many2many tags field and its kanban colour-only variant |
| `fields/relational/many2many_tags_avatar/` | features | 1 | Avatar tag list field for Many2many relations with user images |
| `fields/relational/many2one/` | features | 2 | Many2one field and the autocomplete component behind it |
| `fields/relational/many2one_avatar/` | features | 2 | Many2one field rendering an avatar image, plus its kanban variant |
| `fields/relational/many2one_barcode/` | features | 1 | Many2one field with barcode scanner support |
| `fields/relational/many2one_reference/` | features | 1 | Many2one field for Many2oneReference columns with dynamic relation model |
| `fields/relational/many2one_reference_integer/` | features | 1 | Integer display field for Many2oneReference columns showing the record ID |
| `fields/relational/reference/` | features | 1 | Reference field combining a model selector with a Many2one picker |
| `fields/relational/x2many/` | features | 2 | x2many field (`one2many` + `many2many`) and its list-view variant |
| `fields/selection/` | features | 1 | Shared base for selection-like fields with special data loading |
| `fields/selection/badge_selection/` | features | 2 | Clickable badge group field for Selection and Many2one columns |
| `fields/selection/badge_selection_with_filter/` | features | 1 | Badge selection filtered by an allowed-values field |
| `fields/selection/label_selection/` | features | 1 | Coloured label display field for Selection columns |
| `fields/selection/priority/` | features | 1 | Star rating field for priority Selection columns |
| `fields/selection/radio/` | features | 1 | Radio button group field for Selection and Many2one columns |
| `fields/selection/selection/` | features | 2 | Selection dropdown with whitelist/blacklist value filtering |
| `fields/selection/state_selection/` | features | 1 | Kanban-style coloured state dot dropdown for Selection columns |
| `fields/specialized/` | features | 1 | Face for the `properties` widget family |
| `fields/specialized/ace/` | features | 1 | Code editor field using the Ace/CodeEditor component (keys `ace` + `code`) |
| `fields/specialized/color_picker/` | features | 1 | Predefined colour palette picker field for Integer columns |
| `fields/specialized/domain/` | features | 1 | Domain expression editor field with record count and selector UI |
| `fields/specialized/field_selector/` | features | 1 | Model field-path selector field for Char columns |
| `fields/specialized/google_slide_viewer/` | features | 1 | Embedded Google Slides presentation viewer field |
| `fields/specialized/iframe_wrapper/` | features | 1 | Iframe wrapper rendering HTML field content inside an isolated iframe |
| `fields/specialized/ir_ui_view_ace/` | features | 2 | Ace field for `ir.ui.view` arch, highlighting invalid XPath locators (key `code_ir_ui_view`) |
| `fields/specialized/journal_dashboard_graph/` | features | 1 | Chart.js graph field for accounting journal dashboard data |
| `fields/specialized/kanban_color_picker/` | features | 1 | Inline colour palette picker for kanban card colour selection |
| `fields/specialized/properties/` | features | 10 | Properties widget family: the field, its card/calendar variants, definition editors, per-type value components, layout and sorting hook |
| `fields/specialized/properties/icons/` | features | 0 | Property-field type icons (PNG assets) |
| `fields/specialized/user_groups/` | features | 3 | `res.users` access-rights widget (`group_ids`), implication popover, per-privilege boolean field |
| `fields/temporal/` | features | 1 | Face for the `datetime` field family |
| `fields/temporal/datetime/` | features | 2 | Date and datetime field widget with inline editing and picker integration |
| `fields/temporal/remaining_days/` | features | 1 | Deadline countdown field with colour-coded urgency |
| `fields/temporal/timezone_mismatch/` | features | 1 | Timezone selection field warning when browser and user timezones differ |
| `libs/` | misc | 2 | Vendored-in-src glue: the Bootstrap entry point and `popper_compat.js` (the in-house shim Bootstrap resolves as `@popperjs/core`) |
| `libs/fontawesome7/` | misc | 0 | Vendored FontAwesome 7 — icon CSS + webfonts |
| `libs/fontawesome7/css/` | misc | 0 | FontAwesome 7 stylesheets |
| `libs/fontawesome7/webfonts/` | misc | 0 | FontAwesome 7 webfont files |
| `model/` | entities | 10 | `Model` base + `useReactiveModel`, the sample-data server/generators/coordinator, search-param schema, shared model types |
| `model/relational_model/` | entities | 42 | Relational data model: `RelationalModel`, `RelationalRecord`, lists and groups, save/validation orchestration, edit-state ownership |
| `public/` | pages | 17 | Public (anonymous) page runtime: the `public.interactions` service, `Interaction`/`Colibri`, frontend boot (`public_boot.js`, `public_boot_instance.js`), early-boot `lazyloader.js` / `minimal_dom.js`, login-page interactions, database manager |
| `scss/` | misc | 0 | Shared SCSS base (variables, mixins, backend styles) — 32 `.scss`, no JS |
| `search/` | widgets | 18 | Search model and its mixins (domain, group-by, favorites, properties, query, split-domain), search facets/state/context, arch parser, layout, pager hook |
| `search/action_menus/` | widgets | 1 | Action/Print dropdown menus executing server actions on selected records |
| `search/breadcrumbs/` | widgets | 1 | Breadcrumb trail over the action stack with back-navigation |
| `search/cog_menu/` | widgets | 3 | Cog dropdown merging Action, Print, and registry-based menu items |
| `search/control_panel/` | widgets | 1 | Control panel shell: search bar, breadcrumbs, filter/group-by menus |
| `search/custom_favorite_item/` | widgets | 1 | Dropdown form saving the current search as a named favorite |
| `search/custom_group_by_item/` | widgets | 1 | Dropdown item selecting a custom field to group by |
| `search/embedded_actions_bar/` | widgets | 3 | Embedded-action tabs; visibility and order persisted via `res.users.settings` |
| `search/properties_group_by_item/` | widgets | 1 | Group-by item lazily loading property definitions |
| `search/search_bar/` | widgets | 2 | Search bar with autocomplete suggestions, facet display, keyboard navigation |
| `search/search_bar_menu/` | widgets | 1 | Dropdown grouping Filter, Group By, Favorites, and search panels |
| `search/search_panel/` | widgets | 3 | Sidebar filter panel with category trees and grouped checkbox filters |
| `search/utils/` | widgets | 3 | Search option definitions and domain generators: date periods, group-by descriptors, misc |
| `search/with_search/` | widgets | 1 | Wrapper creating a `SearchModel` and injecting it into the sub-environment |
| `ui/` | shared | 13 | Overlay-layer root: the `ui` service (active element, block UI), viewport tracking, the activation stack, `MainComponentsContainer`, the `scss_error_display` service, `describeNode` for the loggers, plus the `commands` / `dialog` / `notification` / `popover` / `tooltip` faces |
| `ui/alert/` | shared | 1 | `dismiss_alert` service: one delegated click listener dismissing arch-declared alerts |
| `ui/block/` | shared | 1 | Full-screen overlay blocking the UI during long operations |
| `ui/bottom_sheet/` | shared | 2 | Mobile slide-up panel with drag-to-dismiss and snap points, and its service |
| `ui/carousel/` | shared | 1 | Hook wrapping Bootstrap's carousel lifecycle for OWL components |
| `ui/collapse/` | shared | 1 | Animated expand/collapse panel component |
| `ui/commands/` | shared | 6 | Command palette (Ctrl+K): the `command` service, palette component, the item and footer components beside their templates, registration hook, categories, default providers |
| `ui/dialog/` | shared | 4 | `dialog` service, the `Dialog` component, and the standard confirmation dialog |
| `ui/effects/` | shared | 2 | `effect` service and the rainbow-man effect |
| `ui/notification/` | shared | 3 | `notification` service, the toast component, and its container |
| `ui/offcanvas/` | shared | 1 | Slide-in off-canvas panel component |
| `ui/overlay/` | shared | 4 | `overlay` service, the overlay container, and the presenter that renders entries with nested click-away |
| `ui/popover/` | shared | 4 | `popover` service, the component, its hook, and the detached-target watcher |
| `ui/pwa/` | shared | 2 | `pwa` service (install prompt) and the Safari install-instructions dialog |
| `ui/tooltip/` | shared | 2 | `tooltip` service driven by `data-tooltip` attributes, and its component |
| `views/` | widgets | 34 | View infrastructure: the `view` service, `View` component, arch compiler, view utilities/measurements, standard props, action helper, view buttons, the shared multi-record renderer layer (`multi_record_selection.js`, `multi_record_group.js`), and the per-view faces (form, list, kanban, calendar, graph, pivot) |
| `views/calendar/` | widgets | 9 | Calendar view: arch parser, model, controller, renderer, record wrapper, date-range and utility helpers |
| `views/calendar/calendar_common/` | widgets | 3 | Day/week/month renderer and its event popover |
| `views/calendar/calendar_filter_section/` | widgets | 1 | Collapsible sidebar filter section for one calendar filter field |
| `views/calendar/calendar_side_panel/` | widgets | 1 | Side panel with date picker and filter sections |
| `views/calendar/calendar_year/` | widgets | 2 | Year-scale renderer and the popover listing a day cell's records |
| `views/calendar/hooks/` | widgets | 3 | Calendar hooks: popover management, responsive behaviour, scale wiring |
| `views/calendar/mobile_filter_panel/` | widgets | 1 | Compact mobile filter panel with sidebar toggle |
| `views/calendar/quick_create/` | widgets | 1 | Lightweight dialog for creating an event with just a title |
| `views/form/` | widgets | 10 | Form view: arch parser, compiler, controller, renderer, label, `FormSaveCoordinator`, dirty-field hook, the `form_dialog_stack` service, utilities |
| `views/form/button_box/` | widgets | 1 | Responsive stat-button container with overflow dropdown |
| `views/form/form_cog_menu/` | widgets | 1 | Form-view cog menu with save-before-action behaviour |
| `views/form/form_error_dialog/` | widgets | 1 | Save-failure dialog offering discard / redirect / stay |
| `views/form/form_group/` | widgets | 1 | `OuterGroup` / `InnerGroup` column layout components |
| `views/form/form_status_indicator/` | widgets | 1 | Save/discard indicator reading `FormSaveCoordinator.status` and the dirty signal |
| `views/form/setting/` | widgets | 1 | Individual setting row with label, help text, company-dependent icon |
| `views/form/status_bar_buttons/` | widgets | 1 | Status-bar action buttons with overflow dropdown |
| `views/form_with_html_expander/` | widgets | 3 | Form view whose HTML description field grows to fill the sheet on XXL viewports: controller, renderer, view definition |
| `views/graph/` | widgets | 8 | Graph view: arch parser, model, controller, renderer (lazy `loadChartJS`), chart config, search model |
| `views/ir/` | widgets | 1 | The view IR on the client: `view_ir.js` (`irToElement` builds the Element the parsers and compilers walk from the tree `get_view()` ships; `elementToIR` is its inverse) and the generated `view_ir_schema.d.ts` types (from `odoo/tools/view_ir/schema.json` via `python -m odoo.tools.view_ir._generate`) |
| `views/kanban/` | widgets | 17 | Kanban view: arch parser, compiler, model wiring, renderer, record and header components, quick creates, progress-bar hook with local drag-move reconcile, sortable/keyboard hooks (selection now via the shared multi-record layer) |
| `views/list/` | widgets | 21 | List view: arch parser, controller, renderer, per-row `ListRecordRow`, column widths and utilities, aggregates, grouping, sorting, selection, virtualization, keyboard nav/edit, focus geometry, styling |
| `views/list/export_all/` | widgets | 1 | Cog-menu item triggering direct XLSX export of all records |
| `views/pivot/` | widgets | 12 | Pivot view: arch parser, model, controller, renderer, group tree, aggregation, measurements, value utilities, XLSX export trigger |
| `views/section_list/` | widgets | 2 | List renderer and one2many field rendering `line_section` records as a full-width bold title row |
| `views/settings/` | pages | 5 | Settings form view: compiler, controller, renderer, view definition, and the Save/Discard/Stay dialog |
| `views/settings/fields/` | pages | 2 | Settings-specific fields, including the Enterprise upgrade-prompt boolean |
| `views/settings/fields/settings_binary_field/` | pages | 1 | BinaryField variant resolving download URLs via the related field's relation |
| `views/settings/highlight_text/` | pages | 3 | Search-term highlighting: form label variant, highlight component, radio field |
| `views/settings/settings/` | pages | 5 | Settings page structure: app, page, block, header, searchable setting |
| `views/settings/widgets/` | pages | 5 | Settings dashboard widgets: dev tool, edition, invite users, plus the `demo_data` and `user_invite` services |
| `views/view_button/` | widgets | 3 | `ViewButton`, its multi-record variant, and the execution hook |
| `views/view_components/` | widgets | 8 | Cross-view components: selection box, multi-selection buttons, scale selector, group config menu, multi-create and multi-currency popovers, report measures |
| `views/view_dialogs/` | widgets | 3 | Cross-view dialogs: export configuration, form-view dialog, select-or-create dialog |
| `views/widgets/` | widgets | 2 | View-widget infrastructure: the `Widget` component and standard widget props |
| `views/widgets/attach_document/` | widgets | 1 | Button uploading files as `ir.attachment` records and optionally calling a method |
| `views/widgets/documentation_link/` | widgets | 1 | Hyperlink to versioned Odoo documentation |
| `views/widgets/notification_alert/` | widgets | 1 | Warning banner when browser push notifications are blocked |
| `views/widgets/ribbon/` | widgets | 1 | Decorative form-view corner ribbon with configurable label and colour |
| `views/widgets/signature/` | widgets | 1 | Opens a signature dialog and writes the captured image to a field |
| `views/widgets/week_days/` | widgets | 1 | Seven day-of-week checkboxes respecting the locale's week start |
| `webclient/` | pages | 7 | App shell root: `WebClient`, the `currency` / `reloadCompany` / `lazy_session` / `service_worker` services, swipe navigation, and the `actions` face |
| `webclient/actions/` | pages | 25 | Action manager: the `action` service, the navigation clock (`navigation_token.js`), dispatch and loading, button executor, container and controller components, breadcrumb manager/cache, URL and storage state, cache invalidation |
| `webclient/actions/action_executors/` | pages | 5 | One executor per action type: `act_url`, `act_window`, `client`, `close`, `server` |
| `webclient/actions/reports/` | pages | 4 | Report client action: HTML report in an iframe, its executor and hook |
| `webclient/actions/reports/layout_assets/` | pages | 0 | Report layout SCSS assets |
| `webclient/burger_menu/` | pages | 1 | Fullscreen mobile menu hosting the user menu, company switcher, and current app |
| `webclient/burger_menu/burger_user_menu/` | pages | 1 | Mobile variant of the user menu inside the burger overlay |
| `webclient/burger_menu/mobile_switch_company_menu/` | pages | 1 | Mobile company switcher with collapsible toggle |
| `webclient/clickbot/` | pages | 3 | Click-everywhere bot walking apps, views, and filters |
| `webclient/color_scheme/` | pages | 1 | `color_scheme` service — resolves light/dark from the user setting and the OS media query |
| `webclient/dark_mode_toggle/` | pages | 1 | Systray toggle switching the active colour scheme |
| `webclient/debug/` | pages | 7 | Debug menu: the menu component, its basic variant, registered items and providers, field-widgets dialog |
| `webclient/debug/profiling/` | pages | 4 | Profiling: the `profiling` service, systray item, menu item, QWeb view |
| `webclient/density/` | pages | 2 | `density` service (default/compact/condensed) and its systray control |
| `webclient/home_menu/` | pages | 13 | Home menu (app launcher): `HomeMenu`, the `home_menu` service and its `menu` client action, `QuickLauncher` (the popover the navbar opens on hover intent over its home toggle, with pinned and recent tiles and a search box), the `home_menu_badges` loader, the `enterprise_subscription` service, expiration and sysadmin banners, the home-menu background shared with the login page |
| `webclient/errors/` | pages | 2 | Webclient error handlers: offline "Failed to fetch", visitor-facing errors |
| `webclient/install_scoped_app/` | pages | 1 | Public page component for installing scoped PWAs |
| `webclient/loading_indicator/` | pages | 1 | Counts active RPCs and blocks the UI after a 3 s delay |
| `webclient/menus/` | pages | 5 | `menu` service, tree helpers, the home menu layout parser, command providers, the localStorage menu cache, and the per-user usage table that ranks the palette's `/` namespace and the home menu's recent row |
| `webclient/navbar/` | pages | 1 | Navigation bar: home-menu toggle, app brand, sub-menus, systray, mobile sidebar |
| `webclient/promote_studio/` | pages | 4 | Studio upsell: the install dialog, its systray item, the "Add Custom Field" entry patched into the list optional-columns menu and the "Automations" entry patched into the group config menu |
| `webclient/settings_form_view/` | pages | 0 | Template extension stamping the edition, licence and expiration date on the Settings about block |
| `webclient/share_target/` | pages | 1 | `shareTarget` service receiving files from the PWA service worker |
| `webclient/share_url/` | pages | 1 | `navigator.share` of the current URL: a user-menu item and the burger-menu button, shown only in a standalone (PWA) display |
| `webclient/switch_company_menu/` | pages | 3 | Company switcher dropdown, its rows, and the toggle/log-into actions |
| `webclient/user_menu/` | pages | 2 | Systray dropdown with the user avatar and `user_menuitems` entries |
</content>
</invoke>
