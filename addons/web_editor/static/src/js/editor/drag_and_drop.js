/** @odoo-module **/
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";
import { pick } from "@web/core/utils/objects";
import { reactive } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { closest, touching } from "@web/core/utils/ui";

/** @typedef {import("@web/core/utils/draggable_hook_builder").DraggableHandlerParams} DraggableHandlerParams */
/** @typedef {import("@web/core/utils/draggable_hook_builder").DraggableBuilderParams} DraggableBuilderParams */
/** @typedef {import("@web/core/utils/draggable").DraggableParams} DraggableParams */

/** @typedef {DraggableHandlerParams & { dropzone: HTMLElement | null, helper: HTMLElement }} DragAndDropHandlerParams */
/** @typedef {DraggableHandlerParams & { helper: HTMLElement }} DragAndDropStartParams */
/** @typedef {DraggableHandlerParams & { dropzone: HTMLElement }} DropzoneHandlerParams */
/**
 * @typedef DragAndDropParams
 * @extends {DraggableParams}
 *
 * MANDATORY
 * @property {(() => Array)} dropzones a function that returns the available dropzones
 * @property {(() => HTMLElement)} helper a function that returns a helper element
 * that will follow the cursor when dragging
 * @property {HTMLElement || (() => HTMLElement)} scrollingElement the element on
 * which a scroll should be triggered
 *
 * HANDLERS (Optional)
 * @property {(params: DragAndDropStartParams) => any} [onDragStart]
 * called when a dragging sequence is initiated
 * @property {(params: DropzoneHandlerParams) => any} [dropzoneOver]
 * called when an element is over a dropzone
 * @property {(params: DropzoneHandlerParams) => any} [dropzoneOut]
 * called when an element is leaving a dropzone
 * @property {(params: DragAndDropHandlerParams) => any} [onDrag]
 * called when an element is being dragged
 * @property {(params: DragAndDropHandlerParams) => any} [onDragEnd]
 * called when the dragging sequence is over
 */
/**
 * @typedef NativeDraggableState
 * @property {(params: DraggableParams) => any} update
 * method to update the params of the draggable
 * @property {import("@web/core/utils/draggable").DraggableState} state
 * state of the draggable component
 * @property {() => any} destroy
 * method to destroy and unbind the draggable component
 */
/**
 * Utility function to create a native draggable component
 *
 * @param {DraggableBuilderParams} hookParams
 * @param {DraggableParams} initialParams
 * @returns {NativeDraggableState}
 */
export function useNativeDraggable(hookParams, initialParams) {
    const setupFunctions = new Map();
    const cleanupFunctions = [];
    const currentParams = { ...initialParams };
    const setupHooks = {
        wrapState: reactive,
        throttle: throttleForAnimation,
        addListener: (el, type, callback, options) => {
            el.addEventListener(type, callback, options);
            cleanupFunctions.push(() => el.removeEventListener(type, callback));
        },
        setup: (setupFn, depsFn) => setupFunctions.set(setupFn, depsFn),
        teardown: (cleanupFn) => {
            cleanupFunctions.push(cleanupFn);
        }
    };
    // Compatibility for tests
    const el = initialParams.ref.el;
    // TODO this is probably to be removed in master: the received params
    // contain the selector that should be checked and it will be transferred
    // to the makeDraggableHook function. There should not be any need to add
    // the default selector class here.
    el.classList.add("o_draggable");
    cleanupFunctions.push(() => el.classList.remove("o_draggable"));

    const draggableState = makeDraggableHook({ setupHooks, ...hookParams})(currentParams);
    draggableState.enable = true;
    const draggableComponent = {
        state: draggableState,
        update: (newParams) => {
            Object.assign(currentParams, newParams);
            setupFunctions.forEach((depsFn, setupFn) => setupFn(...depsFn()));
        },
        destroy: () => {
            cleanupFunctions.forEach((cleanupFn) => cleanupFn());
        }
    };
    draggableComponent.update({});
    return draggableComponent;
}

function updateElementPosition(el, { x, y }, styleFn, offset = { x: 0, y: 0 }) {
    return styleFn(el, { top: `${y - offset.y}px`, left: `${x - offset.x}px`});
}
/** @type DraggableBuilderParams */
const dragAndDropHookParams = {
    name: "useDragAndDrop",
    acceptedParams: {
        dropzones: [Function],
        scrollingElement: [Object, Function],
        helper: [Function],
        extraWindow: [Object, Function],
    },
    edgeScrolling: { enabled: true },
    onComputeParams({ ctx, params }) {
        // The helper is mandatory and will follow the cursor instead
        ctx.followCursor = false;
        ctx.scrollingElement = params.scrollingElement;
        ctx.getHelper = params.helper;
        ctx.getDropZones = params.dropzones;
    },
    onWillStartDrag: ({ ctx }) => {
        ctx.current.container = ctx.scrollingElement;
        ctx.current.helperOffset = { x: 0, y: 0 };
    },
    onDragStart: ({ ctx, addStyle, addCleanup }) => {
        // Use the helper as the tracking element to properly update scroll values.
        ctx.current.element = ctx.getHelper({ ...ctx.current, ...ctx.pointer });
        ctx.current.helper = ctx.current.element;
        ctx.current.helper.style.position = "fixed";
        // We want the pointer events on the helper so that the cursor
        // is properly displayed.
        ctx.current.helper.classList.remove("o_dragged");
        ctx.current.helper.style.cursor = ctx.cursor;
        ctx.current.helper.style.pointerEvents = "auto";

        // If the helper is inside the iframe, we want pointer events on the
        // frame element so that they reach the window and properly apply
        // the cursor.
        const frameElement = ctx.current.helper.ownerDocument.defaultView.frameElement;
        if (frameElement) {
            addStyle(frameElement, { pointerEvents: "auto" });
        }

        addCleanup(() => ctx.current.helper.remove());

        updateElementPosition(ctx.current.helper, ctx.pointer, addStyle, ctx.current.helperOffset);

        return pick(ctx.current, "element", "helper");
    },
    onDrag: ({ ctx, addStyle, callHandler }) => {
        ctx.current.helper.classList.add("o_draggable_dragging");

        updateElementPosition(ctx.current.helper, ctx.pointer, addStyle, ctx.current.helperOffset);
        // Unfortunately, DOMRect is not an Object, so spreading operator from
        // `touching` does not work, so convert DOMRect to plain object.
        let helperRect = ctx.current.helper.getBoundingClientRect();
        helperRect = {
            x: helperRect.x,
            y: helperRect.y,
            width: helperRect.width,
            height: helperRect.height,
        };
        const dropzoneEl = closest(touching(ctx.getDropZones(), helperRect), helperRect);
        // Update the drop zone if it's in grid mode
        if (ctx.current.dropzone?.el && ctx.current.dropzone.el.classList.contains("oe_grid_zone")) {
            ctx.current.dropzone.rect = ctx.current.dropzone.el.getBoundingClientRect();
        }
        if (
            ctx.current.dropzone &&
            (
                ctx.current.dropzone.el === dropzoneEl
                || (
                    !dropzoneEl
                    && touching([ctx.current.helper], ctx.current.dropzone.rect).length > 0
                )
            )
        ) {
            // If no new dropzone but old one is still valid, return early.
            return pick(ctx.current, "element", "dropzone", "helper");
        }

        if (ctx.current.dropzone && dropzoneEl !== ctx.current.dropzone.el) {
            callHandler("dropzoneOut", { dropzone: ctx.current.dropzone });
            delete ctx.current.dropzone;
        }

        if (dropzoneEl) {
            // Save rect information prior to calling the over function
            // to keep a consistent dropzone even if content was added.
            const rect = DOMRect.fromRect(dropzoneEl.getBoundingClientRect());
            ctx.current.dropzone = {
                el: dropzoneEl,
                rect: {
                    x: rect.x, y: rect.y, width: rect.width, height: rect.height
                }
            };
            callHandler("dropzoneOver", { dropzone: ctx.current.dropzone });
        }
        return pick(ctx.current, "element", "dropzone", "helper");
    },
    onDragEnd({ ctx }) {
        return pick(ctx.current, "element", "dropzone", "helper");
    }
};
/**
 * Function to start a drag and drop handler
 *
 * @param {DragAndDropParams} initialParams params given to the drag and drop
 * component
 * @returns {NativeDraggableState}
 */
export function useDragAndDrop(initialParams) {
    return useNativeDraggable(dragAndDropHookParams, initialParams);
}
