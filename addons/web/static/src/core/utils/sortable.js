/** @odoo-module **/

import { clamp } from "@web/core/utils/numbers";
import { debounce } from "@web/core/utils/timing";

const { useEffect, useEnv, useExternalListener, onWillUnmount } = owl;

/**
 * @typedef SortableParams
 *
 * MANDATORY
 *
 * @property {{ el: HTMLElement | null }} ref
 * @property {string} elements defines sortable elements
 *
 * OPTIONAL
 *
 * @property {boolean | () => boolean} [enable] whether the sortable system should
 *  be enabled.
 * @property {string | () => string} [groups] defines parent groups of sortable
 *  elements. This allows to add `onGroupEnter` and `onGroupLeave` callbacks to
 *  work on group elements during the dragging sequence.
 * @property {string | () => string} [handle] additional selector for when the dragging
 *  sequence must be initiated when dragging on a certain part of the element.
 * @property {string | () => string} [ignore] selector targetting elements that must
 *  initiate a drag.
 * @property {boolean | () => boolean} [connectGroups] whether elements can be dragged
 *  accross different parent groups. Note that it requires a `groups` param to work.
 * @property {string | () => string} [cursor] cursor style during the dragging sequence.
 *
 * HANDLERS (also optional)
 *
 * @property {(group: HTMLElement | null, element: HTMLElement) => any} [onStart]
 *  called when a dragging sequence is initiated.
 * @property {(element: HTMLElement) => any} [onElementEnter] called when the cursor
 *  enters another sortable element.
 * @property {(element: HTMLElement) => any} [onElementLeave] called when the cursor
 *  leaves another sortable element.
 * @property {(group: HTMLElement) => any} [onGroupEnter] (if a `groups` is specified):
 *  will be called when the cursor enters another group element.
 * @property {(group: HTMLElement) => any} [onGroupLeave] (if a `groups` is specified):
 *  will be called when the cursor leaves another group element.
 * @property {(group: HTMLElement | null, element: HTMLElement) => any} [onStop]
 *  called when the dragging sequence ends, regardless of the reason.
 * @property {(params: DropParams) => any} [onDrop] called when the dragging sequence
 *  ends on a mouseup action AND the dragged element has been moved elsewhere. The
 *  callback will be given an object with any useful element regarding the new position
 *  of the dragged element (@see DropParams ).
 */

/**
 * @typedef DropParams
 * @property {HTMLElement} element
 * @property {HTMLElement | null} group
 * @property {HTMLElement | null} previous
 * @property {HTMLElement | null} next
 * @property {HTMLElement | null} parent
 */

const LEFT_CLICK = 0;
const MANDATORY_SORTABLE_PARAMS = ["ref", "elements"];
const SORTABLE_PARAMS = {
    enable: ["boolean", "function"],
    ref: ["object"],
    elements: ["string"],
    groups: ["string", "function"],
    handle: ["string", "function"],
    ignore: ["string", "function"],
    connectGroups: ["boolean", "function"],
    cursor: ["string"],
};

/**
 * Cancels the default behavior and propagation of a given event.
 * @param {Event} ev
 */
function cancelEvent(ev) {
    ev.stopPropagation();
    ev.stopImmediatePropagation();
    ev.preventDefault();
}

/**
 * @param {SortableParams} params
 * @returns {[string, string | boolean][]}
 */
function computeParams(params) {
    const computedParams = { enable: true };
    for (const prop in SORTABLE_PARAMS) {
        if (prop in params) {
            computedParams[prop] = params[prop];
            if (typeof params[prop] === "function") {
                computedParams[prop] = computedParams[prop]();
            }
        }
    }
    return Object.entries(computedParams);
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 * @param {string} val
 * @returns {number}
 */
function cssValueToNumber(val) {
    return Number(val.slice(0, -2));
}

/**
 * Basic error builder for the sortable hook.
 * @param {string} reason
 * @returns {Error}
 */
function sortableError(reason) {
    return new Error(`Unable to use sortable feature: ${reason}.`);
}

/**
 * Sortable feature hook.
 *
 * This hook needs 2 things to work:
 *
 * 1) a `ref` object (@see owl.useRef) which will be used as the root element to
 * calculate boundaries of dragged elements;
 *
 * 2) an `elements` selector string or function that will determine which elements
 * are sortable in the reference element.
 *
 * All other parameters are optional and define the constraints of the dragged elements
 * (and the appearance of the cursor during a dragging sequence), or the different
 * available handlers triggered during the drag sequence.
 * @see SortableParams
 *
 * @param {SortableParams} params
 */
export function useSortable(params) {
    const env = useEnv();
    const { ref } = params;
    /** @type {(() => any)[]} */
    const cleanups = [];

    // Basic error handling asserting that the parameters are valid.
    for (const prop in SORTABLE_PARAMS) {
        if (params[prop] && !SORTABLE_PARAMS[prop].includes(typeof params[prop])) {
            throw sortableError(`invalid type for property "${prop}" in parameters`);
        } else if (!params[prop] && MANDATORY_SORTABLE_PARAMS.includes(prop)) {
            throw sortableError(`missing required property "${prop}" in parameters`);
        }
    }

    /**
     * Stores the current element selector.
     * @type {string | null}
     */
    let groupSelector = null;
    /**
     * Stores the current group selector (optional).
     * @type {string | null}
     */
    let elementSelector = null;
    /**
     * Stores the full selector used to initiate a drag sequence.
     * @type {string | null}
     */
    let ignoreSelector = null;
    /**
     * Stores the full selector used to initiate a drag sequence.
     * @type {string | null}
     */
    let fullSelector = null;

    /**
     * Stores the style of the cursor, if defined.
     * @type {string | null}
     */
    let cursor = null;
    /**
     * Stores whether the sortable elements can be dragged in different groups.
     * @type {boolean}
     */
    let connectGroups = false;
    /**
     * Stores the position and dimensions of the confining element (ref or
     * parent).
     * @type {DOMRect | null}
     */
    let currentContainerRect = null;

    /**
     * Stores the current dragged element.
     * @type {HTMLElement | null}
     */
    let currentElement = null;
    /**
     * Stores the dimensions and position of the dragged element.
     * @type {DOMRect | null}
     */
    let currentElementRect = null;
    /**
     * Stores the group in which the current element originated.
     * @type {HTMLElement | null}
     */
    let currentGroup = null;
    /**
     * Stores the ghost element taking place of the actual dragged element.
     * @type {HTMLElement | null}
     */
    let ghost = null;

    /**
     * Stores whether a drag sequence can be initiated.
     * This is determined by both the given ref being in the document and the
     * `setup` function returning the required params (namely: `elements`).
     * @type {boolean}
     */
    let enabled = false;
    /**
     * Stores whether a drag sequence has been initiated.
     * @type {boolean}
     */
    let started = false;

    /**
     * These 2 variables store the initial offset between the initial mousedown
     * position and the top-left corner of the dragged element.
     */
    /** @type {number} */
    let offsetX = 0;
    /** @type {number} */
    let offsetY = 0;

    /**
     * Adds an event listener to be cleaned up after the next drag sequence
     * has stopped. An additionnal `timeout` param allows the handler to be
     * delayed after a timeout.
     * @param {EventTarget} el
     * @param {string} event
     * @param {(...args: any[]) => any} callback
     * @param {boolean | Record<string, boolean>} [options]
     */
    const addListener = (el, event, callback, options) => {
        el.addEventListener(event, callback, options);
        cleanups.push(() => el.removeEventListener(event, callback, options));
    };

    /**
     * Adds style to an element to be cleaned up after the next drag sequence has
     * stopped.
     * @param {HTMLElement} el
     * @param {Record<string, string | number>} style
     */
    const addStyle = (el, style) => {
        const originalStyle = el.getAttribute("style");
        cleanups.push(() =>
            originalStyle ? el.setAttribute("style", originalStyle) : el.removeAttribute("style")
        );
        for (const key in style) {
            el.style[key] = style[key];
        }
    };

    /**
     * Safely executes a handler from the `params`, so that the drag sequence can
     * be interrupted if an error occurs.
     * @param {string} callbackName
     * @param  {...any} args
     */
    const execHandler = (callbackName, ...args) => {
        if (typeof params[callbackName] === "function") {
            try {
                params[callbackName](...args);
            } catch (err) {
                dragStop(true, true);
                throw err;
            }
        }
    };

    /**
     * Element "mouseenter" event handler.
     * @param {MouseEvent} ev
     */
    const onElementMouseenter = (ev) => {
        const element = ev.currentTarget;
        if (connectGroups || !groupSelector || currentGroup === element.closest(groupSelector)) {
            const pos = ghost.compareDocumentPosition(element);
            if (pos === 2 /* BEFORE */) {
                element.before(ghost);
            } else if (pos === 4 /* AFTER */) {
                element.after(ghost);
            }
        }
        execHandler("onElementEnter", element);
    };

    /**
     * Element "mouseleave" event handler.
     * @param {MouseEvent} ev
     */
    const onElementMouseleave = (ev) => {
        const element = ev.currentTarget;
        execHandler("onElementLeave", element);
    };

    /**
     * Group "mouseenter" event handler.
     * @param {MouseEvent} ev
     */
    const onGroupMouseenter = (ev) => {
        const group = ev.currentTarget;
        group.appendChild(ghost);
        execHandler("onGroupEnter", group);
    };

    /**
     * Group "mouseleave" event handler.
     * @param {MouseEvent} ev
     */
    const onGroupMouseleave = (ev) => {
        const group = ev.currentTarget;
        execHandler("onGroupLeave", group);
    };

    /**
     * Window "keydown" event handler.
     * @param {KeyboardEvent} ev
     */
    const onKeydown = (ev) => {
        if (!enabled || !started) {
            return;
        }
        switch (ev.key) {
            case "Escape":
            case "Tab": {
                cancelEvent(ev);
                dragStop(true);
            }
        }
    };

    /**
     * Global (= ref) "mousedown" event handler.
     * @param {MouseEvent} ev
     */
    const onMousedown = (ev) => {
        // A drag sequence can still be in progress if the mouseup occurred
        // outside of the window.
        dragStop(true);

        if (
            ev.button !== LEFT_CLICK ||
            !enabled ||
            !ev.target.closest(fullSelector) ||
            (ignoreSelector && ev.target.closest(ignoreSelector))
        ) {
            return;
        }

        currentElement = ev.target.closest(elementSelector);
        currentGroup = groupSelector && ev.target.closest(groupSelector);
        offsetX = ev.clientX;
        offsetY = ev.clientY;
    };

    /**
     * Window "mousemove" event handler.
     * @param {MouseEvent} ev
     */
    const onMousemove = (ev) => {
        if (!enabled || !currentElement) {
            return;
        }
        if (started) {
            // Updates the position of the dragged element.
            currentElement.style.left = `${clamp(
                ev.clientX - offsetX,
                currentContainerRect.x,
                currentContainerRect.x + currentContainerRect.width - currentElementRect.width
            )}px`;
            currentElement.style.top = `${clamp(
                ev.clientY - offsetY,
                currentContainerRect.y,
                currentContainerRect.y + currentContainerRect.height - currentElementRect.height
            )}px`;
        } else {
            dragStart();
        }
    };

    /**
     * Window "mouseup" event handler.
     */
    const onMouseup = () => dragStop(false);

    /**
     * Main entry function to start a drag sequence.
     */
    const dragStart = () => {
        started = true;

        // Calculates the bounding rectangles of the current element, and of the
        // container element (`parentElement` or `ref.el`).
        const container = connectGroups || !groupSelector ? ref.el : currentGroup;
        const containerStyle = getComputedStyle(container);
        const [pleft, pright, ptop, pbottom] = [
            "padding-left",
            "padding-right",
            "padding-top",
            "padding-bottom",
        ].map((prop) => cssValueToNumber(containerStyle.getPropertyValue(prop)));

        currentElementRect = currentElement.getBoundingClientRect();
        currentContainerRect = container.getBoundingClientRect();
        const { x, y, width, height } = currentElementRect;

        // Reduces the container's dimensions according to its padding.
        currentContainerRect.x += pleft;
        currentContainerRect.width -= pleft + pright;
        currentContainerRect.y += ptop;
        currentContainerRect.height -= ptop + pbottom;

        // Prepares the ghost element
        ghost = currentElement.cloneNode(false);
        ghost.style = `visibility: hidden; display: block; width: ${width}px; height:${height}px;`;
        cleanups.push(() => ghost.remove());

        // Binds handlers on eligible groups, if the elements are not confined to
        // their parents and a 'groupSelector' has been provided.
        if (connectGroups && groupSelector) {
            for (const siblingGroup of ref.el.querySelectorAll(groupSelector)) {
                addListener(siblingGroup, "mouseenter", onGroupMouseenter);
                addListener(siblingGroup, "mouseleave", onGroupMouseleave);
                addStyle(siblingGroup, { "pointer-events": "auto" });
            }
        }

        // Binds handlers on eligible elements
        for (const siblingElement of ref.el.querySelectorAll(elementSelector)) {
            if (siblingElement !== currentElement && siblingElement !== ghost) {
                addListener(siblingElement, "mouseenter", onElementMouseenter);
                addListener(siblingElement, "mouseleave", onElementMouseleave);
                addStyle(siblingElement, { "pointer-events": "auto" });
            }
        }

        execHandler("onStart", currentGroup, currentElement);

        // Ghost is initially added right after the current element.
        currentElement.after(ghost);

        // Adjusts the offset
        offsetX -= x;
        offsetY -= y;

        addStyle(currentElement, {
            position: "fixed",
            "pointer-events": "none",
            "z-index": 1000,
            width: `${width}px`,
            height: `${height}px`,
            left: `${x}px`,
            top: `${y}px`,
        });

        const bodyStyle = {
            "pointer-events": "none",
            "user-select": "none",
        };
        if (cursor) {
            bodyStyle.cursor = cursor;
        }
        addStyle(document.body, bodyStyle);
    };

    /**
     * Main exit function to stop a drag sequence. Note that it can be called
     * even if a drag sequence did not start yet to perform a cleanup of all
     * current context variables.
     * @param {boolean} cancelled
     * @param {boolean} [inErrorState] can be set to true when an error
     *  occurred to avoid falling into an infinite loop if the error
     *  originated from one of the handlers.
     */
    const dragStop = (cancelled, inErrorState) => {
        if (started) {
            if (!inErrorState) {
                execHandler("onStop", currentGroup, currentElement);
                const previous = ghost.previousElementSibling;
                const next = ghost.nextElementSibling;
                if (!cancelled && previous !== currentElement && next !== currentElement) {
                    execHandler("onDrop", {
                        group: currentGroup,
                        element: currentElement,
                        previous,
                        next,
                        parent: groupSelector && ghost.closest(groupSelector),
                    });
                }
            }
        }

        // Performes all registered clean-ups.
        while (cleanups.length) {
            cleanups.pop()();
        }

        currentContainerRect = null;

        currentElement = null;
        currentElementRect = null;
        currentGroup = null;
        ghost = null;

        started = false;
    };

    // OWL HOOKS

    // Effect depending on the params to update them.
    useEffect(
        (...deps) => {
            const actualParams = Object.fromEntries(deps);
            enabled = Boolean(ref.el && !env.isSmall && actualParams.enable);
            if (!enabled) {
                return;
            }

            // Selectors
            elementSelector = actualParams.elements;
            groupSelector = actualParams.groups || null;
            if (!elementSelector) {
                throw sortableError(`no value found by "elements" selector: ${elementSelector}`);
            }
            const allSelectors = [elementSelector];
            cursor = actualParams.cursor;
            if (groupSelector) {
                allSelectors.unshift(groupSelector);
            }
            if (actualParams.handle) {
                allSelectors.push(actualParams.handle);
            }
            if (actualParams.ignore) {
                ignoreSelector = actualParams.ignore;
            }
            fullSelector = allSelectors.join(" ");

            // Connection accross groups
            connectGroups = actualParams.connectGroups;
        },
        () => computeParams(params)
    );
    // Effect depending on the `ref.el` to add triggering mouse events listener.
    useEffect(
        (el) => {
            if (el) {
                el.addEventListener("mousedown", onMousedown);
                return () => el.removeEventListener("mousedown", onMousedown);
            }
        },
        () => [ref.el]
    );
    // Other global mouse event listeners.
    const debouncedMousemove = debounce(onMousemove, "animationFrame", true);
    useExternalListener(window, "mousemove", debouncedMousemove);
    useExternalListener(window, "mouseup", onMouseup);
    useExternalListener(window, "keydown", onKeydown, true);
    onWillUnmount(() => dragStop(true));
}
