/** @odoo-module **/

import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";

/**
 * @typedef DraggableParams
 *
 * MANDATORY
 *
 * @property {{ el: HTMLElement | null }} ref
 * @property {string} elements defines draggable elements
 *
 * OPTIONAL
 *
 * @property {boolean | () => boolean} [enable] whether the draggable system should
 *  be enabled.
 * @property {string | () => string} [handle] additional selector for when the dragging
 *  sequence must be initiated when dragging on a certain part of the element.
 * @property {string | () => string} [ignore] selector targetting elements that must
 *  initiate a drag.
 * @property {string | () => string} [cursor] cursor style during the dragging sequence.
 *
 * HANDLERS (also optional)
 *
 * @property {(DraggableHandlerParams) => any} [onDragStart]
 *  called when a dragging sequence is initiated.
 * @property {(DraggableHandlerParams) => any} [onDrag]
 *  called on each "mousemove" during the drag sequence.
 * @property {(DraggableHandlerParams) => any} [onDragEnd]
 *  called when the dragging sequence ends, regardless of the reason.
 * @property {(DraggableHandlerParams) => any} [onDrop] called when the dragging sequence
 *  ends on a mouseup action.
 */

/**
 * @typedef DraggableHandlerParams
 * @property {number} x current mouse position on the X axis
 * @property {number} y current mouse position on the Y axis
 * @property {HTMLElement} element
 */

/**
 * @typedef DraggableState
 * @property {boolean} dragging
 */

/** @type {(params: DraggableParams) => DraggableState} */
export const useDraggable = makeDraggableHook({
    name: "useDraggable",
    onDragStart({ ctx, helpers }) {
        helpers.execHandler("onDragStart", { element: ctx.currentElement });
    },
    onDrag({ ctx, helpers }) {
        helpers.execHandler("onDrag", { element: ctx.currentElement });
    },
    onDragEnd({ ctx, helpers }) {
        helpers.execHandler("onDragEnd", { element: ctx.currentElement });
    },
    onDrop({ ctx, helpers }) {
        helpers.execHandler("onDrop", { element: ctx.currentElement });
    },
});
