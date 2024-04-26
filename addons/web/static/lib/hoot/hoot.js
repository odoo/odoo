/** @odoo-module alias=@odoo/hoot default=false */

import { logger } from "./core/logger";
import { Runner } from "./core/runner";
import { makeRuntimeHook } from "./hoot_utils";
import { setRunner } from "./main_runner";
import { setupHootUI } from "./ui/setup_hoot_ui";

/**
 * @typedef {{
 *  runner: Runner;
 *  ui: import("./ui/setup_hoot_ui").UiState
 * }} Environment
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const runner = new Runner();

setRunner(runner);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {unknown} value
 */
export function registerDebugInfo(value) {
    logger.logDebug("debug context provided:", value);
}

// Main test API
export const describe = runner.describe;
export const expect = runner.expect;
export const test = runner.test;

// Hooks
export const after = makeRuntimeHook("after");
export const afterEach = makeRuntimeHook("afterEach");
export const before = makeRuntimeHook("before");
export const beforeEach = makeRuntimeHook("beforeEach");
export const onError = makeRuntimeHook("onError");

// Fixture
export const getFixture = runner.fixture.get;
export const mountOnFixture = runner.fixture.mount;

// Other functions
export const dryRun = runner.exportFn(runner.dryRun);
export const getCurrent = runner.exportFn(runner.getCurrent);
export const registerPreset = runner.exportFn(runner.registerPreset);
export const start = runner.exportFn(runner.start);
export const stop = runner.exportFn(runner.stop);

export { makeExpect } from "./core/expect";
export { destroy } from "./core/fixture";
export { createJobScopedGetter } from "./hoot_utils";

// Constants
export const globals = {
    AbortController: globalThis.AbortController,
    Array: globalThis.Array,
    Boolean: globalThis.Boolean,
    DataTransfer: globalThis.DataTransfer,
    Date: globalThis.Date,
    Document: globalThis.Document,
    Element: globalThis.Element,
    Error: globalThis.Error,
    ErrorEvent: globalThis.ErrorEvent,
    EventTarget: globalThis.EventTarget,
    Map: globalThis.Map,
    MutationObserver: globalThis.MutationObserver,
    Number: globalThis.Number,
    Object: globalThis.Object,
    ProgressEvent: globalThis.ProgressEvent,
    Promise: globalThis.Promise,
    PromiseRejectionEvent: globalThis.PromiseRejectionEvent,
    Proxy: globalThis.Proxy,
    RegExp: globalThis.RegExp,
    Request: globalThis.Request,
    Response: globalThis.Response,
    Set: globalThis.Set,
    SharedWorker: globalThis.SharedWorker,
    String: globalThis.String,
    TypeError: globalThis.TypeError,
    URIError: globalThis.URIError,
    URL: globalThis.URL,
    URLSearchParams: globalThis.URLSearchParams,
    WebSocket: globalThis.WebSocket,
    Window: globalThis.Window,
    Worker: globalThis.Worker,
    XMLHttpRequest: globalThis.XMLHttpRequest,
    cancelAnimationFrame: globalThis.cancelAnimationFrame,
    clearInterval: globalThis.clearInterval,
    clearTimeout: globalThis.clearTimeout,
    console: globalThis.console,
    document: globalThis.document,
    fetch: globalThis.fetch,
    history: globalThis.history,
    JSON: globalThis.JSON,
    localStorage: globalThis.localStorage,
    location: globalThis.location,
    matchMedia: globalThis.matchMedia,
    Math: globalThis.Math,
    navigator: globalThis.navigator,
    ontouchstart: globalThis.ontouchstart,
    performance: globalThis.performance,
    requestAnimationFrame: globalThis.requestAnimationFrame,
    sessionStorage: globalThis.sessionStorage,
    setInterval: globalThis.setInterval,
    setTimeout: globalThis.setTimeout,
};
export const __debug__ = runner;

//-----------------------------------------------------------------------------
// Main
//-----------------------------------------------------------------------------

setupHootUI();
