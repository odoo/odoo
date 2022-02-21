/** @odoo-module **/

import { useListener } from "@web/core/utils/hooks";
import { clamp } from "@web/core/utils/numbers";

const { useEffect, useExternalListener, onWillUnmount } = owl;

const DRAG_START_THRESHOLD = 5 ** 2;

const cancelEvent = (ev) => {
    ev.stopPropagation();
    ev.stopImmediatePropagation();
    ev.preventDefault();
};

const sortableError = (reason) => new Error(`Unable to use sortable feature: ${reason}.`);

const toDependencies = (object) => (object ? Object.entries(object) : [false]);

const fromDependencies = (deps) => deps[0] && Object.fromEntries(deps);

const squareDistance = (x1, y1, x2, y2) => (x2 - x1) ** 2 + (y2 - y1) ** 2;

export const useSortable = (params) => {
    const {
        ref,
        setup,
        onItemEnter,
        onItemLeave,
        onListEnter,
        onListLeave,
        onStart,
        onStop,
        onDrop,
    } = params;
    const lockedAxis = { x: false, y: false };
    const cleanups = [];

    if (typeof setup !== "function") {
        throw sortableError(`missing required function "setup" in parameters`);
    }

    let listSelector = false;
    let itemSelector = false;
    let fullSelector = "";

    let cursor;
    let confinedToParent;
    let currentContainerRect = null;

    let currentItem = null;
    let currentItemRect = null;
    let currentList = null;
    let ghost = null;

    let enabled = false;
    let started = false;
    let updatingDrag = false;

    let offsetX = 0;
    let offsetY = 0;

    if (!Object.getOwnPropertyDescriptor(window, "draggable")) {
        Object.defineProperty(window, "draggable", {
            get: () => ({
                confinedToParent,
                currentContainerRect,
                currentItem,
                currentItemRect,
                currentList,
                ghost,
                offsetX,
                offsetY,
            }),
        });
    }

    const addListener = (el, event, callback, options, timeout) => {
        el.addEventListener(event, callback, options);
        const cleanup = () => el.removeEventListener(event, callback, options);
        cleanups.push(() => (timeout ? setTimeout(cleanup) : cleanup()));
    };

    const addStyle = (el, style) => {
        const originalStyle = el.getAttribute("style");
        cleanups.push(() =>
            originalStyle ? el.setAttribute("style", originalStyle) : el.removeAttribute("style")
        );
        for (const key in style) {
            el.style[key] = style[key];
        }
    };

    const onItemMouseenter = (ev) => {
        const item = ev.currentTarget;
        if (!confinedToParent || item.parentElement === currentItem.parentElement) {
            const pos = ghost.compareDocumentPosition(item);
            if (pos === 2 /* BEFORE */) {
                item.before(ghost);
            } else if (pos === 4 /* AFTER */) {
                item.after(ghost);
            }
        }
        if (onItemEnter) {
            onItemEnter(item);
        }
    };

    const onItemMouseleave = (ev) => {
        onItemLeave(ev.currentTarget);
    };

    const onListMouseenter = (ev) => {
        const list = ev.currentTarget;
        list.appendChild(ghost);
        if (onListEnter) {
            onListEnter(list);
        }
    };

    const onListMouseleave = (ev) => {
        onListLeave(ev.currentTarget);
    };

    const dragStart = () => {
        // Calculates the bounding rectangles of the current item, and of the
        // parent element if items are confined to their parents.
        currentItemRect = currentItem.getBoundingClientRect();
        if (confinedToParent && currentItem.parentElement) {
            currentContainerRect = currentItem.parentElement.getBoundingClientRect();
        } else {
            currentContainerRect = ref.el.getBoundingClientRect();
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
        addListener(currentItem, "click", cancelEvent, true, true);

        // Binds handlers on eligible lists, if the items are not confined to
        // their parents and a 'listSelector' has been provided.
        if (listSelector && !confinedToParent) {
            for (const siblingList of ref.el.querySelectorAll(listSelector)) {
                addListener(siblingList, "mouseenter", onListMouseenter);
                if (onListLeave) {
                    addListener(siblingList, "mouseleave", onListMouseleave);
                }
            }
        }

        // Binds handlers on eligible items
        for (const siblingItem of ref.el.querySelectorAll(itemSelector)) {
            if (siblingItem !== currentItem && siblingItem !== ghost) {
                addListener(siblingItem, "mouseenter", onItemMouseenter);
                if (onItemLeave) {
                    addListener(siblingItem, "mouseleave", onItemMouseleave);
                }
            }
        }

        if (onStart) {
            onStart(currentList, currentItem);
        }

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

        addStyle(document.body, { "user-select": "none" });
        if (cursor) {
            addStyle(document.body, { cursor });
        }
    };

    const dragStop = (cancelled = false) => {
        if (started) {
            if (onStop) {
                onStop(currentList, currentItem);
            }
            if (
                onDrop &&
                !cancelled &&
                ghost.previousElementSibling !== currentItem &&
                ghost.nextElementSibling !== currentItem
            ) {
                const previous = ghost.previousElementSibling;
                const parent = ghost.parentNode;
                onDrop({ list: currentList, item: currentItem, previous, parent });
            }
            for (const cleanup of cleanups.reverse()) {
                cleanup();
            }
        }

        currentContainerRect = null;

        currentItem = null;
        currentItemRect = null;
        currentList = null;
        ghost = null;

        started = false;
    };

    useEffect(
        (...deps) => {
            const params = fromDependencies(deps);
            enabled = Boolean(ref.el && params);
            if (!enabled) {
                return;
            }

            // Selectors
            itemSelector = params.itemSelector;
            listSelector = params.listSelector;
            if (!itemSelector) {
                throw sortableError(`missing required property "itemSelector" in setup`);
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

            // Containment
            confinedToParent = params.containment === "parent";

            // Axes
            if (params.axis) {
                lockedAxis.x = params.axis === "y";
                lockedAxis.y = params.axis === "x";
            }
        },
        () => toDependencies(setup())
    );
    useListener("mousedown", (ev) => {
        if (!enabled || !ev.target.closest(fullSelector)) {
            return;
        }
        currentItem = ev.target.closest(itemSelector);
        currentList = listSelector && ev.target.closest(listSelector);
        offsetX = ev.clientX;
        offsetY = ev.clientY;
    });
    useExternalListener(window, "mousemove", (ev) => {
        if (!enabled || !currentItem || updatingDrag) {
            return;
        }
        updatingDrag = true;
        if (started) {
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
            squareDistance(offsetX, offsetY, ev.clientX, ev.clientY) >= DRAG_START_THRESHOLD
        ) {
            started = true;
            dragStart();
        }
        requestAnimationFrame(() => (updatingDrag = false));
    });
    useExternalListener(window, "mouseup", () => dragStop(), true);
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
