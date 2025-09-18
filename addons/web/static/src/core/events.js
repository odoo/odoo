// @ts-check

/** @module @web/core/events - Typed event constants for bus communication */

/**
 * Global application events dispatched on `env.bus`.
 *
 * Usage:
 *   import { AppEvent } from "@web/core/events";
 *   env.bus.trigger(AppEvent.WEB_CLIENT_READY);
 *   env.bus.addEventListener(AppEvent.MENUS_APP_CHANGED, handler);
 *
 * Existing string literals continue to work — adopt these constants in new
 * code for discoverability and refactoring safety.
 */
export const AppEvent = Object.freeze({
    // ── Lifecycle ───────────────────────────────────────────────────────────
    /** All services loaded and env is ready. Fired once at startup. */
    SERVICES_LOADED: "SERVICES-LOADED",
    /** WebClient component is mounted and ready. Fired once. */
    WEB_CLIENT_READY: "WEB_CLIENT_READY",

    // ── Action Manager ──────────────────────────────────────────────────────
    /** Action manager updated its current controller. */
    ACTION_MANAGER_UPDATE: "ACTION_MANAGER:UPDATE",
    /** Action manager finished UI rendering after an update. */
    ACTION_MANAGER_UI_UPDATED: "ACTION_MANAGER:UI-UPDATED",
    /** Request to load the default app (home menu). */
    WEBCLIENT_LOAD_DEFAULT_APP: "WEBCLIENT:LOAD_DEFAULT_APP",
    /** Request all controllers to save/discard unsaved changes. */
    CLEAR_UNCOMMITTED_CHANGES: "CLEAR-UNCOMMITTED-CHANGES",

    // ── Menu ────────────────────────────────────────────────────────────────
    /** Current app changed in the menu service. */
    MENUS_APP_CHANGED: "MENUS:APP-CHANGED",

    // ── UI ──────────────────────────────────────────────────────────────────
    /** Block the UI (show loading overlay). */
    BLOCK: "BLOCK",
    /** Unblock the UI. */
    UNBLOCK: "UNBLOCK",
    /** Active element (dialog/main) changed. */
    ACTIVE_ELEMENT_CHANGED: "active-element-changed",
    /** Window resized. */
    RESIZE: "resize",

    // ── Form ────────────────────────────────────────────────────────────────
    /** A form-in-dialog was opened. */
    FORM_DIALOG_ADD: "FORM-CONTROLLER:FORM-IN-DIALOG:ADD",
    /** A form-in-dialog was closed. */
    FORM_DIALOG_REMOVE: "FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE",
});

/**
 * Events dispatched on the RPC bus (`rpcBus`).
 *
 * Usage:
 *   import { RpcEvent } from "@web/core/events";
 *   import { rpcBus } from "@web/core/network/rpc";
 *   rpcBus.addEventListener(RpcEvent.REQUEST, handler);
 */
export const RpcEvent = Object.freeze({
    /** An RPC request was sent. */
    REQUEST: "RPC:REQUEST",
    /** An RPC response was received. */
    RESPONSE: "RPC:RESPONSE",
    /** Clear all client-side caches (ORM, name_get, etc.). */
    CLEAR_CACHES: "CLEAR-CACHES",
});

/**
 * Events dispatched on the router bus (`routerBus`).
 *
 * Usage:
 *   import { RouterEvent } from "@web/core/events";
 *   import { routerBus } from "@web/core/browser/router";
 *   routerBus.addEventListener(RouterEvent.ROUTE_CHANGE, handler);
 */
export const RouterEvent = Object.freeze({
    /** URL hash/search changed. */
    ROUTE_CHANGE: "ROUTE_CHANGE",
});
