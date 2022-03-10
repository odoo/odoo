/** @odoo-module **/

import { clamp } from "@web/core/utils/numbers";

/**
 * @typedef SortableParams
 * @property {string} items defines draggable items
 * @property {string} [lists] defines parent lists of draggable items.
 *  This allows to add `onListEnter` and `onListLeave` callbacks to work
 *  on list elements during the dragging sequence.
 * @property {string} [cursor] cursor style during the dragging sequence.
 * @property {string} [handle] additional selector for when the dragging
 *  sequence must be initiated when dragging on a certain part of the element.
 * @property {boolean} [connectLists] whether elements can be dragged accross
 *  different parent lists. Note that it requires a `lists` param to work.
 * @property {"x" | "y" | false} [axis] locks the displacement of the dragged elements
 *  on a single axis (e.g. if axis="x" elements will only be able to move
 *  horizontally).
 */

/**
 * @typedef DropParams
 * @property {HTMLElement} item
 * @property {HTMLElement | null} list
 * @property {HTMLElement | null} previous
 * @property {HTMLElement | null} next
 * @property {HTMLElement | null} parent
 */

const { useEffect, useExternalListener, onWillUnmount } = owl;

const DRAG_START_THRESHOLD = 5 ** 2;

/**
 * Cancels the default behavior and propagation of a given event.
 * @param {Event} ev
 */
const cancelEvent = (ev) => {
    ev.stopPropagation();
    ev.stopImmediatePropagation();
    ev.preventDefault();
};

/**
 * Basic error builder for the sortable hook.
 * @param {string} reason
 * @returns {Error}
 */
const sortableError = (reason) => new Error(`Unable to use sortable feature: ${reason}.`);

/**
 * Serializes params given to the useEffect hook.
 * @param {SortableParams | false} object
 * @returns {([string, any] | false)[]}
 */
const toDependencies = (object) => (object ? Object.entries(object) : [false]);

/**
 * Deserializes params given by the useEffect hook.
 * @param {([string, any] | false)[]} deps
 * @returns {SortableParams | false}
 */
const fromDependencies = (deps) => deps[0] && Object.fromEntries(deps);

/**
 * Returns the square distance between 2 points (defined by x1,y1 and x2,y2).
 * @param {number} x1
 * @param {number} y1
 * @param {number} x2
 * @param {number} y2
 * @returns {number}
 */
const squareDistance = (x1, y1, x2, y2) => (x2 - x1) ** 2 + (y2 - y1) ** 2;

/**
 * @param {Document} activeElement
 * @param {DOMString} selector
 * @returns all selected and visible elements present in the activeElement
 */
export const getVisibleElements = (activeElement, selector) => {
    const visibleElements = [];
    for (const el of activeElement.querySelectorAll(selector)) {
        const isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;
        if (isVisible) {
            visibleElements.push(el);
        }
    }
    return visibleElements;
};

/**
 * Sortable feature hook.
 *
 * This hook needs 2 things to work:
 *
 * 1) a `ref` object (@see owl.useRef) which will be used as the root element
 *  to calculate boundaries of dragged elements;
 *
 * 2) a `setup` function, returning either a dictionnary of parameters or a
 *  falsy value. The hook will be completely disabled as long as a falsy value
 *  is returned, allowing the feature to be dynamically enabled by the caller.
 *
 * The return dictionnary of `setup` has one required parameter: `items`.
 * It is this string that will be used to determine which elements are draggable
 * in the reference element.
 *
 * All other parameters are optional and define the constraints of the dragged
 * elements (and the appearance of the cursor during a dragging sequence).
 * @see SortableParams
 *
 * The params can also take a series of `hook` callbacks that will be called
 * at key points during a dragging sequence:
 *
 * - onStart: called when a dragging sequence is initiated;
 * - onItemEnter: called when the cursor enters another draggable element;
 * - onItemLeave: called when the cursor leaves another draggable element;
 * - onListEnter, if a `lists` is specified: will be called when the cursor
 *      enters another list element;
 * - onListLeave, if a `lists` is specified: will be called when the cursor
 *      leaves another list element;
 * - onStop: called when the dragging sequence ends, regardless of the reason;
 * - onDrop: called when the dragging sequence ends on a mouseup action AND
 *      the dragged element has been moved elsewhere. The callback will be
 *      given an object with any useful element regarding the new position
 *      of the dragged element (@see DropParams).
 *
 * @param {Object} params
 * @param {{ el: HTMLElement | null }} params.ref
 * @param {() => false | null | undefined | SortableParams} params.setup
 * @param {(list: HTMLElement | null, item: HTMLElement) => any} [params.onStart]
 * @param {(item: HTMLElement) => any} [params.onItemEnter]
 * @param {(item: HTMLElement) => any} [params.onItemLeave]
 * @param {(list: HTMLElement) => any} [params.onListEnter]
 * @param {(list: HTMLElement) => any} [params.onListLeave]
 * @param {(list: HTMLElement | null, item: HTMLElement) => any} [params.onStop]
 * @param {(params: DropParams) => any} [params.onDrop]
 */
export const useSortable = (params) => {
    const { ref, setup } = params;
    /** @type {{ x: boolean, y: boolean }} */
    const lockedAxis = { x: false, y: false };
    /** @type {(() => any)[]} */
    const cleanups = [];

    // Basic error handling asserting that the required params are set.
    if (!ref) {
        throw sortableError(`missing required property "ref" in parameters`);
    }
    if (typeof setup !== "function") {
        throw sortableError(`missing required function "setup" in parameters`);
    }

    /**
     * Stores the current item selector.
     * @type {string | null}
     */
    let listSelector = null;
    /**
     * Stores the current list selector (optional).
     * @type {string | null}
     */
    let itemSelector = null;
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
     * Stores whether the draggable elements can be dragged in different lists.
     * @type {boolean}
     */
    let connectLists = false;
    /**
     * Stores the position and dimensions of the confining element (ref or
     * parent).
     * @type {DOMRect | null}
     */
    let currentContainerRect = null;

    /**
     * Stores the current dragged item.
     * @type {HTMLElement | null}
     */
    let currentItem = null;
    /**
     * Stores the dimensions and position of the dragged item.
     * @type {DOMRect | null}
     */
    let currentItemRect = null;
    /**
     * Stores the list in which the current item originated.
     * @type {HTMLElement | null}
     */
    let currentList = null;
    /**
     * Stores the ghost item taking place of the actual dragged item.
     * @type {HTMLElement | null}
     */
    let ghost = null;

    /**
     * Stores whether a drag sequence can be initiated.
     * This is determined by both the given ref being in the document and the
     * `setup` function returning the required params (namely: `items`).
     * @type {boolean}
     */
    let enabled = false;
    /**
     * Stores whether a drag sequence has been initiated.
     * @type {boolean}
     */
    let started = false;
    /**
     * Use to debounce the drag ticks on mousemove.
     * @type {boolean}
     */
    let updatingDrag = false;

    /**
     * These 2 variables store the initial offset between the initial mousedown
     * position and the top-left corner of the dragged item.
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
     * @param {boolean} [timeout]
     */
    const addListener = (el, event, callback, options, timeout) => {
        el.addEventListener(event, callback, options);
        const cleanup = () => el.removeEventListener(event, callback, options);
        cleanups.push(timeout ? () => setTimeout(cleanup) : cleanup);
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
     * Safely executes a hook function from the `params`, so that the drag
     * sequence can be interrupted if an error occurs.
     * @param {string} callbackName
     * @param  {...any} args
     */
    const execHook = (callbackName, ...args) => {
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
     * Item "mouseenter" event handler.
     * @param {MouseEvent} ev
     */
    const onItemMouseenter = (ev) => {
        const item = ev.currentTarget;
        if (connectLists || !listSelector || currentList === item.closest(listSelector)) {
            const pos = ghost.compareDocumentPosition(item);
            if (pos === 2 /* BEFORE */) {
                item.before(ghost);
            } else if (pos === 4 /* AFTER */) {
                item.after(ghost);
            }
        }
        execHook("onItemEnter", item);
    };

    /**
     * Item "mouseleave" event handler.
     * @param {MouseEvent} ev
     */
    const onItemMouseleave = (ev) => {
        const item = ev.currentTarget;
        execHook("onItemLeave", item);
    };

    /**
     * List "mouseenter" event handler.
     * @param {MouseEvent} ev
     */
    const onListMouseenter = (ev) => {
        const list = ev.currentTarget;
        list.appendChild(ghost);
        execHook("onListEnter", list);
    };

    /**
     * List "mouseleave" event handler.
     * @param {MouseEvent} ev
     */
    const onListMouseleave = (ev) => {
        const list = ev.currentTarget;
        execHook("onListLeave", list);
    };

    /**
     * Main entry function to start a drag sequence.
     */
    const dragStart = () => {
        started = true;

        // Calculates the bounding rectangles of the current item, and of the
        // container element (`parentElement` or `ref.el`).
        currentItemRect = currentItem.getBoundingClientRect();
        if (connectLists || !listSelector) {
            currentContainerRect = ref.el.getBoundingClientRect();
        } else {
            currentContainerRect = currentList.getBoundingClientRect();
        }
        const { x, y, width, height } = currentItemRect;

        // Adjusts the offset
        offsetX -= x;
        offsetY -= y;

        // Prepares the ghost item
        ghost = currentItem.cloneNode(true);
        ghost.style.visibility = "hidden";
        cleanups.push(() => ghost.remove());

        // Cancels all click events targetting the current item
        // A timeout is added so that all handlers can be executed without
        // original click events getting in the way.
        addListener(currentItem, "click", cancelEvent, true, true);

        // Binds handlers on eligible lists, if the items are not confined to
        // their parents and a 'listSelector' has been provided.
        if (connectLists && listSelector) {
            for (const siblingList of ref.el.querySelectorAll(listSelector)) {
                addListener(siblingList, "mouseenter", onListMouseenter);
                addListener(siblingList, "mouseleave", onListMouseleave);
            }
        }

        // Binds handlers on eligible items
        for (const siblingItem of ref.el.querySelectorAll(itemSelector)) {
            if (siblingItem !== currentItem && siblingItem !== ghost) {
                addListener(siblingItem, "mouseenter", onItemMouseenter);
                addListener(siblingItem, "mouseleave", onItemMouseleave);
            }
        }

        execHook("onStart", currentList, currentItem);

        // Ghost is initially added right after the current item.
        currentItem.after(ghost);

        addStyle(currentItem, {
            position: "fixed",
            "pointer-events": "none",
            "z-index": 1000,
            width: `${width}px`,
            height: `${height}px`,
            left: `${x}px`,
            top: `${y}px`,
        });

        const bodyStyle = { "user-select": "none" };
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
     *  originated from one of hooks.
     */
    const dragStop = (cancelled, inErrorState) => {
        if (started) {
            if (!inErrorState) {
                execHook("onStop", currentList, currentItem);
                const previous = ghost.previousElementSibling;
                const next = ghost.nextElementSibling;
                if (!cancelled && previous !== currentItem && next !== currentItem) {
                    execHook("onDrop", {
                        list: currentList,
                        item: currentItem,
                        previous,
                        next,
                        parent: listSelector && ghost.closest(listSelector),
                    });
                }
            }
        }

        // Performes all registered clean-ups.
        while (cleanups.length) {
            cleanups.pop()();
        }

        currentContainerRect = null;

        currentItem = null;
        currentItemRect = null;
        currentList = null;
        ghost = null;

        started = false;
    };

    // OWL HOOKS

    useEffect(
        (...deps) => {
            const params = fromDependencies(deps);
            enabled = Boolean(ref.el && params);
            if (!params || !enabled) {
                return;
            }

            // Selectors
            itemSelector = params.items;
            listSelector = params.lists || null;
            if (!itemSelector) {
                throw sortableError(`missing required property "items" in setup`);
            }
            const allSelectors = [itemSelector];
            cursor = params.cursor;
            if (listSelector) {
                allSelectors.unshift(listSelector);
            }
            if (params.handle) {
                allSelectors.push(params.handle);
            }
            fullSelector = allSelectors.join(" ");

            // Connection accross lists
            connectLists = params.connectLists;

            // Axes
            if (params.axis) {
                lockedAxis.x = params.axis === "y";
                lockedAxis.y = params.axis === "x";
            }
        },
        () => toDependencies(setup())
    );
    useEffect(
        (el) => {
            const handler = (ev) => {
                if (!enabled || !ev.target.closest(fullSelector)) {
                    return;
                }

                // A drag sequence can still be in progress if the mouseup occurred
                // outside of the window.
                dragStop(true);

                currentItem = ev.target.closest(itemSelector);
                currentList = listSelector && ev.target.closest(listSelector);
                offsetX = ev.clientX;
                offsetY = ev.clientY;
            };
            el.addEventListener("mousedown", handler);
            return () => el.removeEventListener("mousedown", handler);
        },
        () => [ref.el]
    );
    useExternalListener(window, "mousemove", (ev) => {
        if (!enabled || !currentItem || updatingDrag) {
            return;
        }
        updatingDrag = true;
        if (started) {
            // Updates the position of the dragged item.
            if (!lockedAxis.x) {
                currentItem.style.left = `${clamp(
                    ev.clientX - offsetX,
                    currentContainerRect.x,
                    currentContainerRect.x + currentContainerRect.width - currentItemRect.width
                )}px`;
            }
            if (!lockedAxis.y) {
                currentItem.style.top = `${clamp(
                    ev.clientY - offsetY,
                    currentContainerRect.y,
                    currentContainerRect.y + currentContainerRect.height - currentItemRect.height
                )}px`;
            }
        } else if (
            // The drag sequence starts as soon as the mouse has travelled a
            // certain amount of pixels from the initial mousedown position
            // (`DRAG_START_THRESHOLD` = squared distance required to travel).
            squareDistance(offsetX, offsetY, ev.clientX, ev.clientY) >= DRAG_START_THRESHOLD
        ) {
            dragStart();
        }
        requestAnimationFrame(() => (updatingDrag = false));
    });
    useExternalListener(window, "mouseup", () => dragStop(false), true);
    useExternalListener(
        window,
        "keydown",
        (ev) => {
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
        },
        true
    );
    onWillUnmount(() => dragStop(true));
};
