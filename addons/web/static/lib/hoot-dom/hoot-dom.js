/** @odoo-module alias=@odoo/hoot-dom default=false */

import * as dom from "./helpers/dom";
import * as events from "./helpers/events";
import * as time from "./helpers/time";
import { interactor } from "./hoot_dom_utils";

/**
 * @typedef {import("./helpers/dom").Dimensions} Dimensions
 * @typedef {import("./helpers/dom").FormatXmlOptions} FormatXmlOptions
 * @typedef {import("./helpers/dom").Position} Position
 * @typedef {import("./helpers/dom").QueryOptions} QueryOptions
 * @typedef {import("./helpers/dom").QueryRectOptions} QueryRectOptions
 * @typedef {import("./helpers/dom").QueryTextOptions} QueryTextOptions
 * @typedef {import("./helpers/dom").Target} Target
 *
 * @typedef {import("./helpers/events").DragHelpers} DragHelpers
 * @typedef {import("./helpers/events").DragOptions} DragOptions
 * @typedef {import("./helpers/events").EventType} EventType
 * @typedef {import("./helpers/events").FillOptions} FillOptions
 * @typedef {import("./helpers/events").InputValue} InputValue
 * @typedef {import("./helpers/events").KeyStrokes} KeyStrokes
 * @typedef {import("./helpers/events").PointerOptions} PointerOptions
 */

export {
    formatXml,
    getActiveElement,
    getFocusableElements,
    getNextFocusableElement,
    getParentFrame,
    getPreviousFocusableElement,
    isDisplayed,
    isEditable,
    isFocusable,
    isInDOM,
    isInViewPort,
    isScrollable,
    isVisible,
    matches,
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
} from "./helpers/dom";
export { on } from "./helpers/events";
export {
    animationFrame,
    cancelAllTimers,
    Deferred,
    delay,
    freezeTime,
    microTick,
    setFrameRate,
    tick,
    waitUntil,
} from "./helpers/time";

//-----------------------------------------------------------------------------
// Interactors
//-----------------------------------------------------------------------------

// DOM
export const $ = dom.queryFirst;
export const $$ = dom.queryAll;
export const $1 = dom.queryOne;
export const observe = interactor("query", dom.observe);
export const waitFor = interactor("query", dom.waitFor);
export const waitForNone = interactor("query", dom.waitForNone);

// Events
export const check = interactor("interaction", events.check);
export const clear = interactor("interaction", events.clear);
export const click = interactor("interaction", events.click);
export const dblclick = interactor("interaction", events.dblclick);
export const drag = interactor("interaction", events.drag);
export const edit = interactor("interaction", events.edit);
export const fill = interactor("interaction", events.fill);
export const hover = interactor("interaction", events.hover);
export const keyDown = interactor("interaction", events.keyDown);
export const keyUp = interactor("interaction", events.keyUp);
export const leave = interactor("interaction", events.leave);
export const manuallyDispatchProgrammaticEvent = interactor("interaction", events.dispatch);
export const middleClick = interactor("interaction", events.middleClick);
export const pointerDown = interactor("interaction", events.pointerDown);
export const pointerUp = interactor("interaction", events.pointerUp);
export const press = interactor("interaction", events.press);
export const resize = interactor("interaction", events.resize);
export const rightClick = interactor("interaction", events.rightClick);
export const scroll = interactor("interaction", events.scroll);
export const select = interactor("interaction", events.select);
export const setInputFiles = interactor("interaction", events.setInputFiles);
export const setInputRange = interactor("interaction", events.setInputRange);
export const uncheck = interactor("interaction", events.uncheck);
export const unload = interactor("interaction", events.unload);

// Time
export const advanceFrame = interactor("time", time.advanceFrame);
export const advanceTime = interactor("time", time.advanceTime);
export const runAllTimers = interactor("time", time.runAllTimers);

// Debug
export { exposeHelpers } from "./hoot_dom_utils";
