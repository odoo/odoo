// @ts-check

/** @module @web/core/utils/dnd/draggable - useDraggable OWL hook for free-form element dragging */

import { pick } from "@web/core/utils/collections/objects";
import { makeDraggableHook } from "@web/core/utils/dnd/draggable_hook_builder_owl";

/** @import { DraggableHandlerParams } from "@web/core/utils/dnd/draggable_hook_builder" */

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
 * @property {boolean | (() => boolean)} [enable] whether the draggable system should
 *  be enabled.
 * @property {string | (() => string)} [handle] additional selector for when the dragging
 *  sequence must be initiated when dragging on a certain part of the element.
 * @property {string | (() => string)} [ignore] selector targetting elements that must
 *  initiate a drag.
 * @property {string | (() => string)} [cursor] cursor style during the dragging sequence.
 *
 * HANDLERS (also optional)
 *
 * @property {(params: DraggableHandlerParams) => any} [onDragStart]
 *  called when a dragging sequence is initiated.
 * @property {(params: DraggableHandlerParams) => any} [onDrag]
 *  called on each "mousemove" during the drag sequence.
 * @property {(params: DraggableHandlerParams) => any} [onDragEnd]
 *  called when the dragging sequence ends, regardless of the reason.
 * @property {(params: DraggableHandlerParams) => any} [onDrop] called when the dragging sequence
 *  ends on a mouseup action.
 */

/**
 * @typedef DraggableState
 * @property {boolean} dragging
 */

/** @type {(params: DraggableParams) => DraggableState} */
export const useDraggable = /** @type {any} */ (
    makeDraggableHook(
        /** @type {any} */ ({
            name: "useDraggable",
            onWillStartDrag: ({ ctx }) => pick(ctx.current, "element"),
            onDragStart: ({ ctx }) => pick(ctx.current, "element"),
            onDrag: ({ ctx }) => pick(ctx.current, "element"),
            onDragEnd: ({ ctx }) => pick(ctx.current, "element"),
            onDrop: ({ ctx }) => pick(ctx.current, "element"),
        }),
    )
);
