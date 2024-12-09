/** @odoo-module alias=@odoo/hoot-dom default=false */

import * as dom from "./helpers/dom";
import * as events from "./helpers/events";
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
    queryAttribute,
    queryFirst,
    queryOne,
    queryRect,
    queryText,
    queryValue,
} from "./helpers/dom";
export { on } from "./helpers/events";
export {
    advanceFrame,
    advanceTime,
    animationFrame,
    cancelAllTimers,
    Deferred,
    delay,
    freezeTime,
    microTick,
    runAllTimers,
    setFrameRate,
    tick,
    waitUntil,
} from "./helpers/time";

//-----------------------------------------------------------------------------
// Interactors
//-----------------------------------------------------------------------------

// DOM
export const observe = interactor("query", dom.observe);
export const waitFor = interactor("query", dom.waitFor);
export const waitForNone = interactor("query", dom.waitForNone);

// Events
export const check = interactor("event", events.check);
export const clear = interactor("event", events.clear);
export const click = interactor("event", events.click);
export const dblclick = interactor("event", events.dblclick);
export const drag = interactor("event", events.drag);
export const edit = interactor("event", events.edit);
export const fill = interactor("event", events.fill);
export const hover = interactor("event", events.hover);
export const keyDown = interactor("event", events.keyDown);
export const keyUp = interactor("event", events.keyUp);
export const leave = interactor("event", events.leave);
export const manuallyDispatchProgrammaticEvent = interactor("event", events.dispatch);
export const middleClick = interactor("event", events.middleClick);
export const pointerDown = interactor("event", events.pointerDown);
export const pointerUp = interactor("event", events.pointerUp);
export const press = interactor("event", events.press);
export const resize = interactor("event", events.resize);
export const rightClick = interactor("event", events.rightClick);
export const scroll = interactor("event", events.scroll);
export const select = interactor("event", events.select);
export const setInputFiles = interactor("event", events.setInputFiles);
export const setInputRange = interactor("event", events.setInputRange);
export const uncheck = interactor("event", events.uncheck);
export const unload = interactor("event", events.unload);
