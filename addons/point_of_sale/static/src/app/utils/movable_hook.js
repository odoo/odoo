/** @odoo-module */

import { useRefListener } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";

/**
 * constrains a number to the given bounds.
 *
 * @param {number} num the number to constrain
 * @param {number} min the lower bound for the number
 * @param {number} max the upper bound for the number
 * @returns {number} the constrained number
 */
export function constrain(num, min, max) {
    return Math.min(Math.max(num, min), max);
}

/**
 * Gives the minimum and maximum x and y value for an element to prevent it from
 * overflowing outside of another element.
 *
 * @param {HTMLElement} el the element for which we want to get the position
 *  limits
 * @param {HTMLElement} limitEl the element outside of which the main element
 *  shouldn't overflow
 * @returns {{ minX: number, maxX: number, minY: number, maxY: number }} limits
 */
export function getLimits(el, limitEl) {
    const { width, height } = el.getBoundingClientRect();
    const limitRect = limitEl.getBoundingClientRect();
    const offsetParentRect = el.offsetParent.getBoundingClientRect();
    return {
        minX: limitRect.left - offsetParentRect.left,
        maxX: limitRect.left - offsetParentRect.left + limitRect.width - width,
        minY: limitRect.top - offsetParentRect.top,
        maxY: limitRect.top - offsetParentRect.top + limitRect.height - height,
    };
}

/**
 * Make a ref's element draggable, when the dragging starts, calls the
 * `onMoveStart` param. Calls the `onMove` param when the cursor moves with the
 * difference in position since the start of the dragging motion. This hook does
 * not add any style to the element being dragged, this is the responsibility of
 * the caller.
 *
 * @param {object} param0
 * @param {{ el: HTMLElement | null }} param0.ref
 * @param {() => unknown} param0.onMoveStart
 * @param {({dx, dy}: {dx: number, dy: number}) => unknown} param0.onMove
 */
export function useMovable({ ref, onMoveStart, onMove }) {
    let startPosition;
    function registerMovingMethod({ startEv, moveEv, endEv, getPos }) {
        const moveHandler = (ev) => {
            const { x, y } = getPos(ev);
            onMove({ dx: x - startPosition.x, dy: y - startPosition.y });
        };
        useRefListener(ref, startEv, (ev) => {
            ev.stopImmediatePropagation();
            startPosition = getPos(ev);
            onMoveStart();
            document.addEventListener(moveEv, moveHandler);
            document.addEventListener(
                endEv,
                () => document.removeEventListener(moveEv, moveHandler),
                { once: true, capture: true }
            );
        });
        onWillUnmount(() => document.removeEventListener(moveEv, moveHandler));
    }
    registerMovingMethod({
        startEv: "mousedown",
        moveEv: "mousemove",
        endEv: "mouseup",
        getPos: (ev) => ({ x: ev.clientX, y: ev.clientY }),
    });
    registerMovingMethod({
        startEv: "touchstart",
        moveEv: "touchmove",
        endEv: "touchend",
        getPos: (ev) => ({ x: ev.touches[0].clientX, y: ev.touches[0].clientY }),
    });
}
