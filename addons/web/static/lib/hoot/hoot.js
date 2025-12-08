/** @odoo-module alias=@odoo/hoot default=false */

import { logger } from "./core/logger";
import { Runner } from "./core/runner";
import { urlParams } from "./core/url";
import { copyAndBind, makeRuntimeHook } from "./hoot_utils";
import { setRunner } from "./main_runner";
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
 *
 * @typedef {{
 *  runner: Runner;
 *  ui: import("./ui/setup_hoot_ui").UiState
 * }} Environment
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const runner = new Runner(urlParams);

setRunner(runner);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

// Main test API
export const describe = runner.describe;
export const expect = runner.expect;
export const test = runner.test;

// Test hooks
export const after = makeRuntimeHook("after");
export const afterEach = makeRuntimeHook("afterEach");
export const before = makeRuntimeHook("before");
export const beforeEach = makeRuntimeHook("beforeEach");
export const onError = makeRuntimeHook("onError");

// Fixture
export const getFixture = runner.fixture.get;

// Other test runner functions
export const definePreset = runner.exportFn(runner.definePreset);
export const dryRun = runner.exportFn(runner.dryRun);
export const getCurrent = runner.exportFn(runner.getCurrent);
export const start = runner.exportFn(runner.start);
export const stop = runner.exportFn(runner.stop);

export { makeExpect } from "./core/expect";
export { destroy } from "./core/fixture";
export { defineTags } from "./core/tag";
export { createJobScopedGetter } from "./hoot_utils";

// Constants
export const globals = copyAndBind(globalThis);
export const isHootReady = setupHootUI();

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
export {
    advanceFrame,
    advanceTime,
    animationFrame,
    cancelAllTimers,
    check,
    clear,
    click,
    dblclick,
    Deferred,
    delay,
    drag,
    edit,
    fill,
    formatXml,
    freezeTime,
    getActiveElement,
    getFocusableElements,
    getNextFocusableElement,
    getParentFrame,
    getPreviousFocusableElement,
    hover,
    isDisplayed,
    isEditable,
    isFocusable,
    isInDOM,
    isInViewPort,
    isScrollable,
    isVisible,
    keyDown,
    keyUp,
    leave,
    manuallyDispatchProgrammaticEvent,
    matches,
    microTick,
    middleClick,
    observe,
    on,
    pointerDown,
    pointerUp,
    press,
    queryAll,
    queryAllAttributes,
    queryAllProperties,
    queryAllRects,
    queryAllTexts,
    queryAllValues,
    queryAny,
    queryAttribute,
    queryFirst,
    queryOne,
    queryRect,
    queryText,
    queryValue,
    resize,
    rightClick,
    runAllTimers,
    scroll,
    select,
    setFrameRate,
    setInputFiles,
    setInputRange,
    tick,
    uncheck,
    unfreezeTime,
    unload,
    waitFor,
    waitForNone,
    waitUntil,
} from "@odoo/hoot-dom";

// Debug
export { exposeHelpers } from "../hoot-dom/hoot_dom_utils";
export const __debug__ = runner;

/**
 * @param {...unknown} values
 */
export function registerDebugInfo(...values) {
    logger.logDebug(...values);
}
