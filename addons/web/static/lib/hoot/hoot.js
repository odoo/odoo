/** @odoo-module alias=@odoo/hoot default=false */

import { logger } from "./core/logger";
import { TestRunner } from "./core/runner";
import { setupHootUI } from "./ui/setup_hoot_ui";

/**
 * @typedef {{
 *  runner: TestRunner;
 *  ui: import("./ui/setup_hoot_ui").UiState
 * }} Environment
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

// - Instantiate the test runner
const runner = new TestRunner();

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
export const after = runner.exportFn(runner.after);
export const afterAll = runner.exportFn(runner.afterAll);
export const afterEach = runner.exportFn(runner.afterEach);
export const before = runner.exportFn(runner.before);
export const beforeAll = runner.exportFn(runner.beforeAll);
export const beforeEach = runner.exportFn(runner.beforeEach);
export const onError = runner.exportFn(runner.onError);

// Fixture
export const destroy = runner.fixture.destroy;
export const getFixture = runner.fixture.get;
export const mountOnFixture = runner.fixture.mount;

// Other functions
export const createJobScopedGetter = runner.exportFn(runner.createJobScopedGetter);
export const dryRun = runner.exportFn(runner.dryRun);
export const getCurrent = runner.exportFn(runner.getCurrent);
export const registerPreset = runner.exportFn(runner.registerPreset);
export const start = runner.exportFn(runner.start);

export { makeExpect } from "./core/expect";

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

setupHootUI(runner);
