/** @odoo-module **/

import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";
import { pick } from "@web/core/utils/objects";

/** @typedef {import("@web/core/utils/draggable_hook_builder").DraggableHandlerParams} DraggableHandlerParams */
/** @typedef {DraggableHandlerParams & { group: HTMLElement | null }} SortableHandlerParams */

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
 * @property {boolean | (() => boolean)} [enable] whether the sortable system should
 *  be enabled.
 * @property {string | (() => string)} [groups] defines parent groups of sortable
 *  elements. This allows to add `onGroupEnter` and `onGroupLeave` callbacks to
 *  work on group elements during the dragging sequence.
 * @property {string | (() => string)} [handle] additional selector for when the dragging
 *  sequence must be initiated when dragging on a certain part of the element.
 * @property {string | (() => string)} [ignore] selector targetting elements that must
 *  initiate a drag.
 * @property {boolean | (() => boolean)} [connectGroups] whether elements can be dragged
 *  accross different parent groups. Note that it requires a `groups` param to work.
 * @property {string | (() => string)} [cursor] cursor style during the dragging sequence.
 *
 * HANDLERS (also optional)
 *
 * @property {(params: SortableHandlerParams) => any} [onDragStart]
 *  called when a dragging sequence is initiated.
 * @property {(params: DraggableHandlerParams) => any} [onElementEnter] called when the cursor
 *  enters another sortable element.
 * @property {(params: DraggableHandlerParams) => any} [onElementLeave] called when the cursor
 *  leaves another sortable element.
 * @property {(params: SortableHandlerParams) => any} [onGroupEnter] (if a `groups` is specified):
 *  will be called when the cursor enters another group element.
 * @property {(params: SortableHandlerParams) => any} [onGroupLeave] (if a `groups` is specified):
 *  will be called when the cursor leaves another group element.
 * @property {(params: SortableHandlerParams) => any} [onDragEnd]
 *  called when the dragging sequence ends, regardless of the reason.
 * @property {(params: DropParams) => any} [onDrop] called when the dragging sequence
 *  ends on a pointerup action AND the dragged element has been moved elsewhere. The
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

/**
 * @typedef SortableState
 * @property {boolean} dragging
 */

/** @type {(params: SortableParams) => SortableState} */
export const useSortable = makeDraggableHook({
    name: "useSortable",
    acceptedParams: {
        groups: [String, Function],
        connectGroups: [Boolean, Function],
    },
    defaultParams: {
        connectGroups: false,
        edgeScrolling: { speed: 20, threshold: 60 },
        groupSelector: null,
    },

    // Build steps
    onComputeParams({ ctx, params }) {
        // Group selector
        ctx.groupSelector = params.groups || null;
        if (ctx.groupSelector) {
            ctx.fullSelector = [ctx.groupSelector, ctx.fullSelector].join(" ");
        }

        // Connection accross groups
        ctx.connectGroups = params.connectGroups;
    },

    // Runtime steps
    onDragStart({ ctx, addListener, addStyle, callHandler }) {
        /**
         * Element "pointerenter" event handler.
         * @param {PointerEvent} ev
         */
        const onElementPointerEnter = (ev) => {
            const element = ev.currentTarget;
            if (
                connectGroups ||
                !groupSelector ||
                current.group === element.closest(groupSelector)
            ) {
                const pos = current.placeHolder.compareDocumentPosition(element);
                if (pos === 2 /* BEFORE */) {
                    element.before(current.placeHolder);
                } else if (pos === 4 /* AFTER */) {
                    element.after(current.placeHolder);
                }
            }
            callHandler("onElementEnter", { element });
        };

        /**
         * Element "pointerleave" event handler.
         * @param {PointerEvent} ev
         */
        const onElementPointerLeave = (ev) => {
            const element = ev.currentTarget;
            callHandler("onElementLeave", { element });
        };

        /**
         * Group "pointerenter" event handler.
         * @param {PointerEvent} ev
         */
        const onGroupPointerEnter = (ev) => {
            const group = ev.currentTarget;
            group.appendChild(current.placeHolder);
            callHandler("onGroupEnter", { group });
        };

        /**
         * Group "pointerleave" event handler.
         * @param {PointerEvent} ev
         */
        const onGroupPointerLeave = (ev) => {
            const group = ev.currentTarget;
            callHandler("onGroupLeave", { group });
        };

        const { connectGroups, current, elementSelector, groupSelector, ref } = ctx;
        const { width, height } = current.elementRect;

        // Adjusts size for the placeholder element
        addStyle(current.placeHolder, {
            visibility: "hidden",
            display: "block",
            width: `${width}px`,
            height: `${height}px`,
        });

        // Binds handlers on eligible groups, if the elements are not confined to
        // their parents and a 'groupSelector' has been provided.
        if (connectGroups && groupSelector) {
            for (const siblingGroup of ref.el.querySelectorAll(groupSelector)) {
                addListener(siblingGroup, "pointerenter", onGroupPointerEnter);
                addListener(siblingGroup, "pointerleave", onGroupPointerLeave);
            }
        }

        // Binds handlers on eligible elements
        for (const siblingEl of ref.el.querySelectorAll(elementSelector)) {
            if (siblingEl !== current.element && siblingEl !== current.placeHolder) {
                addListener(siblingEl, "pointerenter", onElementPointerEnter);
                addListener(siblingEl, "pointerleave", onElementPointerLeave);
            }
        }

        // Placeholder is initially added right after the current element.
        current.element.after(current.placeHolder);

        return pick(current, "element", "group");
    },
    onDragEnd({ ctx }) {
        return pick(ctx.current, "element", "group");
    },
    onDrop({ ctx }) {
        const { current, groupSelector } = ctx;
        const previous = current.placeHolder.previousElementSibling;
        const next = current.placeHolder.nextElementSibling;
        if (previous !== current.element && next !== current.element) {
            return {
                element: current.element,
                group: current.group,
                previous,
                next,
                parent: groupSelector && current.placeHolder.closest(groupSelector),
            };
        }
    },
    onWillStartDrag({ ctx, addCleanup }) {
        const { connectGroups, current, groupSelector } = ctx;

        if (groupSelector) {
            current.group = current.element.closest(groupSelector);
            if (!connectGroups) {
                current.container = current.group;
            }
        }

        current.placeHolder = current.element.cloneNode(false);

        addCleanup(() => current.placeHolder.remove());

        return pick(current, "element", "group");
    },
});
