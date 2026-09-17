# Directory Map

> **142 directories** under `static/src/` | **348 `.js` files** | Maps directory
> → runtime + responsibility.
>
> Two runtimes: **public** (visitor-facing Interaction framework) and
> **editor/backend** (the builder + client action). `.js` count = files directly
> in that directory (not recursive). See `ARCHITECTURE.md` for the runtime split
> and `INTERACTIONS.md` for the Interaction framework.

## Root & Shared

| Directory | Runtime | .js | Primary Responsibility |
|-----------|---------|----:|------------------------|
| `.` (static/src) | — | 0 | Container only |
| `@types/` | — | 0 | TS ambient type declarations (`.d.ts`) |
| `img/` (+8 subdirs) | — | 0 | Static images: backgrounds, snippet thumbnails/previews, loader |
| `svg/` | — | 0 | SVG assets |
| `scss/` (+ `options/`, `options/colors/`) | — | 0 | All frontend/backend/editor stylesheets + color-palette / user-value SCSS variables |
| `libs/bootstrap/` | public | 1 | Bootstrap frontend tweaks/overrides (`bootstrap.js`) |
| `libs/zoomodoo/` | public | 1 | Image zoom-on-hover library (`zoomodoo.js`) |
| `utils/` | both | 4 | Shared helpers: `google_maps.js` (API loading and validation), `images.js`, `videos.js`, `misc.js` (EventBus, UTM dataset) |
| `common/` (+ `@types/`) | both | 2 | Mail `Record` models shared public+backend: `website_model.js`, `website_visitor_model.js` |

## Public-Site Interaction Framework

| Directory | Runtime | .js | Primary Responsibility |
|-----------|---------|----:|------------------------|
| `interactions/` | public | 28 | Top-level public Interactions (popups, scroll, anchors, text highlight, lazy-load, ripple, animation) + `.edit.js` variants |
| `interactions/carousel/` | public | 5 | Bootstrap carousel slider + BS-upgrade fix (+ edit/preview) |
| `interactions/cookies/` | public | 4 | Cookie bar, approval, toggle, warning |
| `interactions/dropdown/` | public | 4 | Hoverable dropdown + mega-menu dropdown (+ edit) |
| `interactions/header/` | public | 8 | Header scroll behaviors: base, standard/fixed/top/disappears/fade-out, special |
| `interactions/parallax/` | public | 2 | Parallax scroll effect (+ preview) |
| `interactions/popup/` | public | 5 | Popup modal base + no-backdrop + shared popup (+ edit) |
| `interactions/video/` | public | 3 | Background video + media video (+ edit) |
| `core/` | public | 6 | Frontend services (`website_menus`, `website_page`, `website_cookies`, `website_map`) + edit-mode bridge (`website_edit_service.js`, `component_interaction_edit.js`) |
| `core/errors/` | public | 1 | `beforeunload_error_handler.js` — suppress errors during page unload |
| `js/content/` | public | 10 | Legacy `PublicRoot`/`publicWidget` layer: `website_root.js`, `snippets.animation.js`, minimal-bundle DOM helpers |
| `js/` | both | 7 | Frontend/shared utils: `utils.js`, `text_processing.js`, `highlight_utils.js`, `http_cookie.js`, form helpers, custom-JS injection |
| `js/editor/` | editor | 1 | `html_editor.js` — link-popover extension |
| `js/tours/` | both | 3 | Onboarding tours: homepage, configurator, `tour_utils.js` |
| `js/backend/view_hierarchy/` | backend | 2 | Backend view-hierarchy debug navbar |
| `snippets/` (+ ~66 `s_*` subdirs) | public | 0 (34‡) | Per-snippet public JS (Interaction / public widget) + `.edit.js`; most `s_*` dirs are SCSS/XML-only (0 js) |

> ‡ `snippets/` itself holds no direct `.js`; the **34** is the recursive total
> across its `s_*` subdirectories (20 runtime `.js` + 14 `.edit.js`).

> **Snippet directories.** The 66 `s_*` directories under `snippets/` are
> per-snippet asset folders (`.scss` / `.xml` templates); only a subset carry
> JS. Those with runtime JS include `s_countdown`, `s_chart`,
> `s_dynamic_snippet(_carousel)`, `s_google_map`, `s_map`, `s_facebook_page`,
> `s_instagram_page`, `s_embed_code`, `s_floating_blocks`,
> `s_announcement_scroll`, `s_image_gallery`, `s_searchbar`,
> `s_table_of_content`, `s_website_form`, `s_faq_horizontal`, `s_share` — each
> typically a `.js` (Interaction) + `.edit.js` pair.

## Builder (Editor) Integration

| Directory | Runtime | .js | Primary Responsibility |
|-----------|---------|----:|------------------------|
| `builder/` | editor | 5 | Builder entry: `website_builder.js` (assembles plugins), `snippet_model.js`, `snippet_viewer.js`, `option_sequence.js`, `builder_urlpicker.js` |
| `builder/plugins/` | editor | 28 | Website-level `Plugin`s (carousel, collapse, translation, visibility, customize-website, menu-data, switchable-views) |
| `builder/plugins/options/` | editor | 78 | Snippet-option `BaseOptionComponent`s + their `*_option_plugin.js` registrars (background, card, chart, countdown, cover, dynamic-snippet, footer, …) |
| `builder/plugins/options/header/` | editor | 11 | Header option components/plugins (box, elements, font, navigation, icon-bg) |
| `builder/plugins/options/google_maps_option/` | editor | 4 | Google-maps snippet option |
| `builder/plugins/options/pricelist_option/` | editor | 4 | Pricelist snippet option |
| `builder/plugins/floating_blocks/` | editor | 4 | Floating-blocks snippet options |
| `builder/plugins/font/` | editor | 2 | Font option plugin |
| `builder/plugins/form/` | editor | 8 | Website-form builder options |
| `builder/plugins/highlight/` | editor | 4 | Text-highlight builder plugin/options |
| `builder/plugins/image/` | editor | 3 | Image option plugins |
| `builder/plugins/layout_option/` | editor | 8 | Layout/grid/columns options |
| `builder/plugins/navbar_link_popover/` | editor | 1 | Navbar-link popover in editor |
| `builder/plugins/theme/` | editor | 7 | Theme-tab options (colors, fonts, buttons, page layout) |
| `builder/plugins/translation_tab/` | editor | 3 | Translation customize-tab plugin/components |
| `builder/translation_components/` | editor | 3 | Reusable translate-mode components |

## Client Actions & Backend Components

| Directory | Runtime | .js | Primary Responsibility |
|-----------|---------|----:|------------------------|
| `client_actions/website_preview/` | backend | 12 | The `website_preview` client action (iframe preview + editor) **and its systray items** (edit, publish, mobile, new-content, switcher) |
| `client_actions/website_dashboard/` | backend | 1 | Website analytics dashboard action |
| `client_actions/configurator/` | backend | 1 | First-run configurator wizard |
| `client_actions/open_custom_menu/` | backend | 1 | Action opening a website custom-menu dialog |
| `components/` | frontend | 1 | `user_switch.js` (public user-switch component) |
| `components/views/` | backend | 6 | Backend views: page kanban/list, page search-model + hook, theme-preview form/kanban |
| `components/dialog/` | backend | 5 | Editor dialogs: add-page, edit-menu, page-properties, SEO |
| `components/fields/` | backend | 4 | Backend form fields: publish button, redirect field, iframe widget |
| `components/resource_editor/` | backend | 3 | Embedded HTML/CSS resource (ACE) editor |
| `components/autocomplete_with_pages/` | both | 2 | Autocomplete suggesting website pages |
| `components/navbar/` | backend | 1 | Editor navbar component |
| `components/burger_menu/` | backend | 1 | Mobile burger-menu component (editor) |
| `components/media_dialog/` | backend | 1 | Media-dialog extension (documents tab) |
| `components/edit_head_body_dialog/` | backend | 1 | Edit `<head>`/`<body>` code dialog |
| `components/fullscreen_indication/` | backend | 1 | "Press ESC to exit fullscreen" hint |
| `components/website_loader/` | backend | 1 | Full-page loading overlay component |
| `components/editor/` | backend | 0 | `editor.scss` only |
| `services/` | backend | 2 | `website_service.js` (reactive backend state), `website_custom_menus.js` (contextual editor dialogs) |
| `systray_items/` | backend | 0 | **SCSS only** — the systray button JS lives in `client_actions/website_preview/` |
