/** @odoo-module **/

import { useListener } from "@web/core/utils/hooks";

const { hooks } = owl;
const { onWillUnmount, useComponent, useExternalListener } = hooks;

const cancelEvent = (ev) => {
    ev.stopPropagation();
    ev.stopImmediatePropagation();
    ev.preventDefault();
};

export const useSortable = (params) => {
    const {
        listSelector,
        itemSelector,
        containment,
        cursor,
        handle,
        axis,
        // Events
        onItemEnter,
        onItemLeave,
        onListEnter,
        onListLeave,
        onStart,
        onStop,
        onDrop,
    } = params;
    const selectors = [itemSelector];
    if (listSelector) {
        selectors.unshift(listSelector);
    }
    if (handle) {
        selectors.push(handle);
    }
    const fullSelector = selectors.join(" ");
    const lockedAxis = { x: false, y: false };
    if (axis === "x") {
        lockedAxis.y = true;
    } else if (axis === "y" || containment === "parent") {
        lockedAxis.x = true;
    }

    let currentItem = null;
    let currentList = null;
    let ghost = null;

    let started = false;
    let locked = false;

    let offsetX = 0;
    let offsetY = 0;

    const component = useComponent();
    const cleanups = [];

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

    const debounce = (callback) => {
        if (locked) {
            return;
        }
        locked = true;
        callback();
        requestAnimationFrame(() => (locked = false));
    };

    const onItemMouseenter = (ev) => {
        const item = ev.currentTarget;
        if (containment !== "parent" || item.closest(listSelector) === currentList) {
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
        if (containment !== "parent") {
            list.appendChild(ghost);
        }
        if (onListEnter) {
            onListEnter(list);
        }
    };

    const onListMouseleave = (ev) => {
        onListLeave(ev.currentTarget);
    };

    const dragStart = () => {
        if (started) {
            return;
        }
        started = true;
        const { x, y, width, height } = currentItem.getBoundingClientRect();
        offsetX -= x;
        offsetY -= y;

        ghost = currentItem.cloneNode(true);
        ghost.style.opacity = 0;
        cleanups.push(() => ghost.remove());
        addListener(currentItem, "click", cancelEvent, true, true);

        const lists = listSelector ? component.el.querySelectorAll(listSelector) : [component.el];

        for (const siblingList of lists) {
            addListener(siblingList, "mouseenter", onListMouseenter);
            if (onListLeave) {
                addListener(siblingList, "mouseleave", onListMouseleave);
            }

            for (const siblingItem of component.el.querySelectorAll(itemSelector)) {
                if (siblingItem !== currentItem && siblingItem !== ghost) {
                    addListener(siblingItem, "mouseenter", onItemMouseenter);
                    if (onItemLeave) {
                        addListener(siblingItem, "mouseleave", onItemMouseleave);
                    }
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
            width: `${width}px`,
            height: `${height}px`,
        });

        if (cursor) {
            addStyle(document.body, { cursor });
        }
    };

    const drag = (x, y) => {
        debounce(() => {
            if (!lockedAxis.x) {
                currentItem.style.left = `${x - offsetX}px`;
            }
            if (!lockedAxis.y) {
                currentItem.style.top = `${y - offsetY}px`;
            }
        });
    };

    const dragStop = (cancelled = false) => {
        if (!started) {
            return;
        }
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
            onDrop({ previous, parent });
        }
        for (const cleanup of cleanups) {
            cleanup();
        }
        currentItem = null;
        ghost = null;
        started = false;
    };

    useListener("mousedown", fullSelector, (ev) => {
        currentItem = ev.target.closest(itemSelector);
        currentList = listSelector ? ev.target.closest(listSelector) : component.el;
        offsetX = ev.clientX;
        offsetY = ev.clientY;
    });
    useExternalListener(window, "mousemove", (ev) => {
        if (!currentItem) {
            return;
        }
        dragStart();
        drag(ev.clientX, ev.clientY);
    });
    useExternalListener(window, "mouseup", () => dragStop(), true);
    useExternalListener(
        window,
        "keydown",
        (ev) => {
            switch (ev.key) {
                case "Escape":
                case "Tab": {
                    if (started) {
                        cancelEvent(ev);
                    }
                    dragStop(true);
                }
            }
        },
        true
    );
    onWillUnmount(() => dragStop(true));
};
