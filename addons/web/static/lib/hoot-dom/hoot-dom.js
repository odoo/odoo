/** @odoo-module alias=@odoo/hoot-dom default=false */

/**
 * @typedef {import("./helpers/dom").QueryOptions} QueryOptions
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
    getFocusableElements,
    getNextFocusableElement,
    getPreviousFocusableElement,
    getRect,
    isDisplayed,
    isEditable,
    isEventTarget,
    isFocusable,
    isInDOM,
    isVisible,
    matches,
    observe,
    queryAll,
    queryAllAttributes,
    queryAllTexts,
    queryAllValues,
    queryAttribute,
    queryFirst,
    queryLast,
    queryOne,
    queryText,
    queryValue,
    registerPseudoClass,
    waitFor,
    waitForNone,
    waitUntil,
    watchKeys,
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
    on,
    pointerDown,
    pointerUp,
    press,
    resize,
    scroll,
    select,
    setInputFiles,
    uncheck,
} from "./helpers/events";
