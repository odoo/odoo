/** @odoo-module alias=@odoo/hoot-dom default=false */

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
    observe,
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
    waitFor,
    waitForNone,
} from "./helpers/dom";
export {
    check,
    clear,
    click,
    dblclick,
    drag,
    edit,
    fill,
    hover,
    keyDown,
    keyUp,
    leave,
    dispatch as manuallyDispatchProgrammaticEvent,
    middleClick,
    on,
    pointerDown,
    pointerUp,
    press,
    resize,
    rightClick,
    scroll,
    select,
    setInputFiles,
    setInputRange,
    uncheck,
    unload,
} from "./helpers/events";
export {
    Deferred,
    advanceFrame,
    advanceTime,
    animationFrame,
    cancelAllTimers,
    delay,
    freezeTime,
    microTick,
    runAllTimers,
    setFrameRate,
    tick,
    waitUntil,
} from "./helpers/time";
