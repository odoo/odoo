#!/usr/bin/env node
/**
 * Generates SCSS that replaces Odoo's oi-* and fa-* icon fonts
 * with Lucide SVG icons via CSS mask-image.
 *
 * Usage: node scripts/generate_icon_css.mjs > static/src/scss/lucide_icons.scss
 */

import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Read the icon_data.js file and extract ICON_PATHS
const iconDataPath = resolve(
    __dirname,
    "../../odx_owl/static/src/components/icon/icon_data.js"
);
const raw = readFileSync(iconDataPath, "utf-8");

// Parse the JS object (quick and dirty: eval after stripping the export)
const stripped = raw
    .replace(/\/\*\*.*?\*\*\//s, "")
    .replace("export const ICON_PATHS =", "globalThis.__ICONS__ =");
new Function(stripped)();
const ICON_PATHS = globalThis.__ICONS__;

// ── Mapping: Odoo icon class → Lucide icon name ────────

const OI_MAP = {
    // Navigation & layout
    "oi-search": "search",
    "oi-apps": "layout-grid",
    "oi-panel-right": "panel-right",
    "oi-view-list": "list",
    "oi-view-kanban": "layout-grid",
    "oi-view-pivot": "table-2",
    "oi-view-cohort": "git-branch",
    "oi-view": "eye",
    // Chevrons
    "oi-chevron-down": "chevron-down",
    "oi-chevron-left": "chevron-left",
    "oi-chevron-right": "chevron-right",
    "oi-chevron-up": "chevron-up",
    // Arrows
    "oi-arrow-down": "arrow-down",
    "oi-arrow-up": "arrow-up",
    "oi-arrow-left": "arrow-left",
    "oi-arrow-right": "arrow-right",
    "oi-arrow-down-left": "arrow-down-left",
    "oi-arrow-down-right": "arrow-down-right",
    "oi-arrow-up-left": "arrow-up-left",
    "oi-arrow-up-right": "arrow-up-right",
    "oi-arrows-h": "move-horizontal",
    "oi-arrows-v": "move-vertical",
    // Actions
    "oi-plus": "plus",
    "oi-minus": "minus",
    "oi-close": "x",
    "oi-launch": "external-link",
    "oi-archive": "archive",
    "oi-unarchive": "archive-restore",
    "oi-merge": "git-merge",
    "oi-record": "circle-dot",
    "oi-draggable": "grip-vertical",
    // Users & social
    "oi-user": "user",
    "oi-user-plus": "user-plus",
    "oi-users": "users",
    "oi-smile-add": "smile-plus",
    // UI elements
    "oi-ellipsis-h": "ellipsis",
    "oi-ellipsis-v": "ellipsis-vertical",
    "oi-star-plus": "star",
    "oi-settings-adjust": "settings",
    "oi-group": "folder",
    "oi-studio": "wand-2",
    "oi-numpad": "grid-3x3",
    // Text
    "oi-text-break": "text",
    "oi-text-inline": "type",
    "oi-text-wrap": "wrap-text",
    "oi-text-effect": "sparkles",
    "oi-subtitle": "subtitles",
    // Communication
    "oi-voip": "phone",
    "oi-threads": "message-square",
    "oi-activity": "activity",
    "oi-activity-plus": "activity",
    // Business
    "oi-suitcase": "briefcase",
    "oi-suitcase-plus": "briefcase",
    "oi-transfer": "arrow-left-right",
    "oi-food-delivery": "utensils",
    // Schedule
    "oi-schedule-today": "calendar-check",
    "oi-schedule-tomorrow": "calendar-clock",
    "oi-schedule-later": "calendar-plus",
    // Misc
    "oi-gif-picker": "image",
    "oi-backspace-o": "delete",
    "oi-x": "x",
    "oi-x-square": "square-x",
    // Social (brand icons – use generic fallbacks)
    "oi-kickstarter": "rocket",
    "oi-tiktok": "video",
    "oi-bluesky": "cloud",
    "oi-google-play": "play",
    "oi-strava": "activity",
    "oi-discord": "message-circle",
    "oi-odoo": "hexagon",
};

const FA_MAP = {
    // CRUD & common actions
    "fa-plus": "plus",
    "fa-minus": "minus",
    "fa-trash": "trash-2",
    "fa-trash-o": "trash-2",
    "fa-pencil": "pencil",
    "fa-check": "check",
    "fa-times": "x",
    "fa-times-circle": "x-circle",
    "fa-save": "save",
    "fa-undo": "undo-2",
    "fa-copy": "copy",
    "fa-paste": "clipboard-paste",
    "fa-print": "printer",
    "fa-download": "download",
    "fa-upload": "upload",
    "fa-refresh": "refresh-cw",
    "fa-repeat": "refresh-cw",
    // Navigation
    "fa-bars": "menu",
    "fa-search": "search",
    "fa-home": "home",
    "fa-arrow-left": "arrow-left",
    "fa-arrow-right": "arrow-right",
    "fa-arrow-up": "arrow-up",
    "fa-arrow-down": "arrow-down",
    "fa-long-arrow-right": "arrow-right",
    "fa-long-arrow-left": "arrow-left",
    "fa-caret-down": "chevron-down",
    "fa-caret-up": "chevron-up",
    "fa-caret-right": "chevron-right",
    "fa-caret-left": "chevron-left",
    "fa-chevron-down": "chevron-down",
    "fa-chevron-up": "chevron-up",
    "fa-chevron-left": "chevron-left",
    "fa-chevron-right": "chevron-right",
    "fa-expand": "maximize-2",
    "fa-compress": "minimize-2",
    "fa-external-link": "external-link",
    // Status & feedback
    "fa-exclamation-triangle": "alert-triangle",
    "fa-exclamation": "alert-triangle",
    "fa-warning": "alert-triangle",
    "fa-info-circle": "info",
    "fa-question-circle": "help-circle",
    "fa-check-circle": "check-circle",
    "fa-circle": "circle",
    "fa-circle-o": "circle",
    "fa-star": "star",
    "fa-star-o": "star",
    "fa-heart": "heart",
    "fa-thumbs-up": "thumbs-up",
    "fa-thumbs-down": "thumbs-down",
    "fa-bell": "bell",
    "fa-bell-o": "bell",
    // Communication
    "fa-envelope": "mail",
    "fa-envelope-o": "mail",
    "fa-phone": "phone",
    "fa-comments": "message-square",
    "fa-comments-o": "message-square",
    "fa-comment": "message-circle",
    "fa-comment-o": "message-circle",
    "fa-paper-plane-o": "send",
    "fa-paperclip": "paperclip",
    "fa-share": "share-2",
    "fa-share-alt": "share-2",
    // Files & data
    "fa-file": "file",
    "fa-file-o": "file",
    "fa-file-text": "file-text",
    "fa-file-text-o": "file-text",
    "fa-folder": "folder",
    "fa-folder-o": "folder",
    "fa-folder-open": "folder-open",
    "fa-database": "database",
    "fa-hashtag": "hash",
    // Settings
    "fa-cog": "settings",
    "fa-cogs": "settings",
    "fa-gear": "settings",
    "fa-gears": "settings",
    "fa-wrench": "wrench",
    "fa-sliders": "sliders-horizontal",
    // User
    "fa-user": "user",
    "fa-user-o": "user",
    "fa-users": "users",
    "fa-sign-in": "log-in",
    "fa-sign-out": "log-out",
    "fa-lock": "lock",
    "fa-unlock": "unlock",
    "fa-unlock-alt": "unlock",
    // Charts
    "fa-area-chart": "area-chart",
    "fa-bar-chart": "bar-chart-2",
    "fa-line-chart": "trending-up",
    "fa-pie-chart": "pie-chart",
    // View & visibility
    "fa-eye": "eye",
    "fa-eye-slash": "eye-off",
    "fa-filter": "filter",
    "fa-sort": "arrow-up-down",
    "fa-sort-asc": "arrow-up",
    "fa-sort-desc": "arrow-down",
    "fa-columns": "columns-2",
    // Media
    "fa-camera": "camera",
    "fa-image": "image",
    "fa-video-camera": "video",
    "fa-microphone": "mic",
    "fa-microphone-slash": "mic-off",
    "fa-volume-up": "volume-2",
    "fa-volume-off": "volume-x",
    // Time
    "fa-clock-o": "clock",
    "fa-calendar": "calendar",
    "fa-calendar-o": "calendar",
    // Location & web
    "fa-map-marker": "map-pin",
    "fa-globe": "globe",
    "fa-link": "link",
    "fa-unlink": "unlink",
    // Tags & labels
    "fa-tag": "tag",
    "fa-tags": "tags",
    "fa-bookmark": "bookmark",
    "fa-bookmark-o": "bookmark",
    "fa-thumb-tack": "pin",
    // Cloud / Save
    "fa-cloud": "cloud",
    "fa-cloud-upload": "save",
    "fa-cloud-download": "download",
    // Spinner
    "fa-spinner": "loader",
    "fa-circle-o-notch": "loader",
    // Code & technical
    "fa-code": "code",
    "fa-terminal": "terminal",
    // Misc
    "fa-hand-paper-o": "hand",
    "fa-deaf": "ear-off",
    "fa-address-card": "contact",
};

// ── SVG generation ──────────────────────────────────────

function shapeToSvg(shape) {
    const { type, ...attrs } = shape;
    const attrStr = Object.entries(attrs)
        .map(([k, v]) => `${k}="${v}"`)
        .join(" ");
    return `<${type} ${attrStr}/>`;
}

function iconToSvgDataUri(iconName) {
    const paths = ICON_PATHS[iconName];
    if (!paths) return null;

    const inner = paths.map(shapeToSvg).join("");
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;

    // Encode for CSS url()
    const encoded = svg
        .replace(/"/g, "'")
        .replace(/#/g, "%23")
        .replace(/</g, "%3C")
        .replace(/>/g, "%3E");

    return `url("data:image/svg+xml,${encoded}")`;
}

// ── Generate SCSS ───────────────────────────────────────

const lines = [];
lines.push("// Auto-generated: Lucide icon replacements for Odoo icon fonts");
lines.push("// Generated by: scripts/generate_icon_css.mjs");
lines.push("// Do not edit manually.");
lines.push("");

// Collect valid OI mappings first
const validOi = [];
for (const [oiClass, lucideName] of Object.entries(OI_MAP)) {
    const dataUri = iconToSvgDataUri(lucideName);
    if (dataUri) validOi.push({ oiClass, lucideName, dataUri });
}

// Base styles — only for mapped OI icons
lines.push("// ── Odoo UI Icons (oi-*) base override ─────────────────");
lines.push("// Only mapped icons get the mask treatment; unmapped keep font fallback.");
for (let i = 0; i < validOi.length; i += 4) {
    const chunk = validOi.slice(i, i + 4);
    const selectors = chunk.map((e) => `.${e.oiClass}::before`).join(",\n");
    const isLast = i + 4 >= validOi.length;
    lines.push(selectors + (isLast ? " {" : ","));
}
lines.push("    font-family: inherit !important;");
lines.push("    content: '' !important;");
lines.push("    display: inline-block;");
lines.push("    width: 1em;");
lines.push("    height: 1em;");
lines.push("    background: currentColor;");
lines.push("    vertical-align: -0.125em;");
lines.push("    -webkit-mask-size: contain;");
lines.push("    mask-size: contain;");
lines.push("    -webkit-mask-repeat: no-repeat;");
lines.push("    mask-repeat: no-repeat;");
lines.push("    -webkit-mask-position: center;");
lines.push("    mask-position: center;");
lines.push("}");
lines.push("");

// OI icon mappings
lines.push("// ── OI icon mappings ────────────────────────────────────");
let oiCount = 0;
for (const { oiClass, lucideName, dataUri } of validOi) {
    lines.push(`.${oiClass}::before {`);
    lines.push(`    -webkit-mask-image: ${dataUri};`);
    lines.push(`    mask-image: ${dataUri};`);
    lines.push(`}`);
    oiCount++;
}
lines.push("");

// Base styles for FA icons
lines.push("// ── FontAwesome (fa-*) base override ───────────────────");
lines.push("// Only override mapped icons, leave unmapped ones as font fallback");
const faClasses = Object.keys(FA_MAP)
    .map((cls) => {
        const dataUri = iconToSvgDataUri(FA_MAP[cls]);
        return dataUri ? `.fa.${cls}::before` : null;
    })
    .filter(Boolean);

// Generate selector list for base styles
for (let i = 0; i < faClasses.length; i += 5) {
    const chunk = faClasses.slice(i, i + 5);
    const isLast = i + 5 >= faClasses.length;
    lines.push(chunk.join(",\n") + (isLast ? " {" : ","));
}
lines.push("    font-family: inherit !important;");
lines.push("    content: '' !important;");
lines.push("    display: inline-block;");
lines.push("    width: 1em;");
lines.push("    height: 1em;");
lines.push("    background: currentColor;");
lines.push("    vertical-align: -0.125em;");
lines.push("    -webkit-mask-size: contain;");
lines.push("    mask-size: contain;");
lines.push("    -webkit-mask-repeat: no-repeat;");
lines.push("    mask-repeat: no-repeat;");
lines.push("    -webkit-mask-position: center;");
lines.push("    mask-position: center;");
lines.push("}");
lines.push("");

// FA icon mappings
lines.push("// ── FA icon mappings ────────────────────────────────────");
let faCount = 0;
for (const [faClass, lucideName] of Object.entries(FA_MAP)) {
    const dataUri = iconToSvgDataUri(lucideName);
    if (!dataUri) {
        lines.push(`// SKIP: .fa.${faClass} → ${lucideName} (not found in Lucide)`);
        continue;
    }
    lines.push(`.fa.${faClass}::before {`);
    lines.push(`    -webkit-mask-image: ${dataUri};`);
    lines.push(`    mask-image: ${dataUri};`);
    lines.push(`}`);
    faCount++;
}

// Spinner animation for loader icons
lines.push("");
lines.push("// ── Spinner animation for loader icons ─────────────────");
lines.push(".fa.fa-spinner::before,");
lines.push(".fa.fa-circle-o-notch::before {");
lines.push("    animation: odx-icon-spin 1s linear infinite;");
lines.push("}");
lines.push("");
lines.push("@keyframes odx-icon-spin {");
lines.push("    to { transform: rotate(360deg); }");
lines.push("}");

lines.push("");
lines.push(`// Total: ${oiCount} OI icons + ${faCount} FA icons replaced`);

console.log(lines.join("\n"));
