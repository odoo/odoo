/** @odoo-module alias=@odoo/hoot default=false */

import { logger } from "./core/logger";
import { Runner } from "./core/runner";
import { bindConfigToUrl, urlParams } from "./core/url";
import { copyAndBind, exposeMethod } from "./hoot_utils";
import { mainRunner, setMainRunner } from "./main_runner";
import { setupHootUI } from "./ui/setup_hoot_ui";

/**
 * @typedef {import("../hoot-dom/helpers/dom").Dimensions} Dimensions
 * @typedef {import("../hoot-dom/helpers/dom").FormatXmlOptions} FormatXmlOptions
 * @typedef {import("../hoot-dom/helpers/dom").Position} Position
 * @typedef {import("../hoot-dom/helpers/dom").QueryOptions} QueryOptions
 * @typedef {import("../hoot-dom/helpers/dom").QueryRectOptions} QueryRectOptions
 * @typedef {import("../hoot-dom/helpers/dom").QueryTextOptions} QueryTextOptions
 * @typedef {import("../hoot-dom/helpers/dom").Target} Target
 *
 * @typedef {import("../hoot-dom/helpers/events").DragHelpers} DragHelpers
 * @typedef {import("../hoot-dom/helpers/events").DragOptions} DragOptions
 * @typedef {import("../hoot-dom/helpers/events").EventType} EventType
 * @typedef {import("../hoot-dom/helpers/events").FillOptions} FillOptions
 * @typedef {import("../hoot-dom/helpers/events").InputValue} InputValue
 * @typedef {import("../hoot-dom/helpers/events").KeyStrokes} KeyStrokes
 * @typedef {import("../hoot-dom/helpers/events").PointerOptions} PointerOptions
 *
 * @typedef {import("./mock/network").ServerWebSocket} ServerWebSocket
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const runner = new Runner(urlParams);

bindConfigToUrl(runner.config);
setMainRunner(runner);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

// Main test API (already configurable & bound to the runner)
export const describe = runner.describe;
export const expect = runner.expect;
export const test = runner.test;

// Test hooks
export const after = runner.exposeRuntimeHook("after");
export const afterEach = runner.exposeRuntimeHook("afterEach");
export const before = runner.exposeRuntimeHook("before");
export const beforeEach = runner.exposeRuntimeHook("beforeEach");
export const onError = runner.exposeRuntimeHook("onError");

// Fixture
export const getFixture = exposeMethod(runner.fixture, "getFixture");

// Other test runner functions
export const createJobScopedGetter = exposeMethod(runner, "createJobScopedGetter");
export const definePreset = exposeMethod(runner, "definePreset");
export const dryRun = exposeMethod(runner, "dryRun");
export const getCurrent = exposeMethod(runner, "getCurrent");
export const start = exposeMethod(runner, "start");
export const stop = exposeMethod(runner, "stop");

export { makeExpect } from "./core/expect";
export { defineTags } from "./core/tag";

// Constants
export const globals = copyAndBind(globalThis);
export const isHootReady = setupHootUI(runner);

// Mock
export { disableAnimations, enableTransitions } from "./mock/animation";
export { mockDate, mockLocale, mockTimeZone, onTimeZoneChange } from "./mock/date";
export { makeSeededRandom } from "./mock/math";
export { mockPermission, mockSendBeacon, mockUserAgent, mockVibrate } from "./mock/navigator";
export { mockFetch, mockLocation, mockWebSocket, mockWorker, withFetch } from "./mock/network";
export { flushNotifications } from "./mock/notification";
export {
    mockMatchMedia,
    mockTouch,
    watchAddedNodes,
    watchKeys,
    watchListeners,
} from "./mock/window";

// HOOT-DOM
export * from "@odoo/hoot-dom";

// Debug
export { exposeHelpers } from "../hoot-dom/hoot_dom_utils";
export const __debug__ = mainRunner;

/**
 * @param {...unknown} values
 */
export function registerDebugInfo(...values) {
    logger.logDebug(...values);
}
