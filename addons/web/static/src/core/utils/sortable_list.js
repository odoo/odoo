/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";

/** @typedef {import("@web/core/utils/draggable_hook_builder").DraggableHandlerParams} DraggableHandlerParams */
/** @typedef {DraggableHandlerParams & { group: HTMLElement | null }} SortableListHandlerParams */

/**
 *
 * MANDATORY
 *
 * @property {{ el: HTMLElement | null }} ref
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
 * @property {boolean | () => boolean} [nest] whether elements are nested or not.
 * @property {string | () => string} [lisType] type of lists ("ul" or "ol").
 * @property {number | () => number} [nestInterval] Horizontal distance needed to trigger
 * a change in the list hierarchy (i.e. changing parent when moving horizontally)
 *
 * HANDLERS (also optional)
 *
 * @property {(params: SortableListHandlerParams) => any} [onDragStart] called when a
 * dragging sequence is initiated.
 * @property {(params: MoveParams) => any} [onMove] called when the element has moved
 * (changed position) (@see MoveParams).
 * @property {(params: SortableListHandlerParams) => any} [onGroupEnter] called when
 * the element enters a group.
 * @property {(params: SortableListHandlerParams) => any} [onGroupLeave] called when
 * the element leaves a group.
 * @property {(params: MoveParams) => any} [onDrop] called when the dragging sequence
 *  ends on a mouseup action AND the dragged element has been moved elsewhere. The
 *  callback will be given an object with any useful element regarding the new position
 *  of the dragged element (@see MoveParams).
 * @property {(params: SortableListHandlerParams) => any} [onDragEnd] called when the
 * dragging sequence ends, regardless of the reason.
 */

/**
 * @typedef MoveParams
 * @property {HTMLElement} element
 * @property {HTMLElement | null} group
 * @property {HTMLElement | null} previous
 * @property {HTMLElement | null} next
 * @property {HTMLElement | null} newGroup
 * @property {HTMLElement | null} parent
 * @property {HTMLElement} placeholder
 */

/**
 * @typedef SortableState
 * @property {boolean} dragging
 */

/** @type {(params: SortableParams) => SortableState} */
export const useSortableList = makeDraggableHook({
    name: "useSortableList",
    acceptedParams: {
        groups: [String, Function],
        connectGroups: [Boolean, Function],
        nest: [Boolean],
        listType: [String],
        nestInterval: [Number],
    },
    defaultParams: {
        connectGroups: false,
        currentGroup: null,
        cursor: "grabbing",
        edgeScrolling: { speed: 20, threshold: 60 },
        elements: "li",
        groupSelector: null,
        nest: false,
        listType: "ul",
        nestInterval: 15,
    },

    // Set the parameters.
    onComputeParams({ ctx, params }) {
        // Group selector
        ctx.groupSelector = params.groups || null;
        if (ctx.groupSelector) {
            ctx.fullSelector = [ctx.groupSelector, ctx.fullSelector].join(" ");
        }
        // Connection accross groups
        ctx.connectGroups = params.connectGroups;
        // Nested elements
        ctx.nest = params.nest;
        // List type
        ctx.listType = params.listType;
        // Horizontal distance needed to trigger a change in the list hierarchy
        // (i.e. changing parent when moving horizontally)
        ctx.nestInterval = params.nestInterval;
        ctx.isRTL = localization.direction === "rtl";
    },

    // Set the current group and create the placeholder row that will take the
    // place of the moving row.
    onWillStartDrag({ ctx, addCleanup }) {
        if (ctx.groupSelector) {
            ctx.currentGroup = ctx.current.element.closest(ctx.groupSelector);
            if (!ctx.connectGroups) {
                ctx.current.container = ctx.currentGroup;
            }
        }
        ctx.current.placeHolder = ctx.current.element.cloneNode(false);
        ctx.current.placeHolder.style = `display: block; width: 100%; height: 5px; background-color: deepskyblue`;
        addCleanup(() => ctx.current.placeHolder.remove());
    },

    // Make the placeholder take the place of the moving row, and add style on
    // different elements to provide feedback that there is an ongoing dragging
    // sequence.
    onDragStart({ ctx, addStyle }) {
        // Horizontal position which will be used to detect row changes when moving vertically, so that
        // we do not need to be on the row to trigger row changes (only the vertical position matters).
        // Nested rows are shorter than "root" rows, and do not start at the same horizontal position.
        // However, every row spans until the end of the container. Therefore, we use the end of the
        // container - 1 as horizontal position.
        ctx.selectorX = ctx.isRTL
            ? ctx.current.containerRect.left + 1
            : ctx.current.containerRect.right - 1;

        // Placeholder is initially added right after the current element.
        ctx.current.element.after(ctx.current.placeHolder);
        addStyle(ctx.current.element, { opacity: 0.5 });

        // Remove pointer-events style added by draggable_hook_builder and set
        // it on the view elements instead as in our case we want to show the
        // ctx.cursor style on the whole screen, not only in the ref el.
        addStyle(document.body, { "pointer-events": "auto" });
        addStyle(document.querySelector(".o_navbar"), { "pointer-events": "none" });
        addStyle(document.querySelector(".o_action_manager"), { "pointer-events": "none" });
        addStyle(ctx.current.container, { "pointer-events": "auto" });

        ctx.prevNestX = ctx.pointer.x;

        // Calls "onDragStart" handler
        return {
            element: ctx.current.element,
            group: ctx.currentGroup,
        };
    },
    // Check if the cursor moved enough to trigger a move. If it did, move the
    // placeholder accordingly.
    onDrag({ ctx, callHandler }) {
        const onMove = (prevPos) => {
            callHandler("onMove", {
                element: ctx.current.element,
                previous: ctx.current.placeHolder.previousElementSibling,
                next: ctx.current.placeHolder.nextElementSibling,
                parent: ctx.nest
                    ? ctx.current.placeHolder.parentElement.closest(ctx.elementSelector)
                    : false,
                group: ctx.currentGroup,
                newGroup: ctx.connectGroups
                    ? ctx.current.placeHolder.closest(ctx.groupSelector)
                    : ctx.currentGroup,
                prevPos,
                placeholder: ctx.current.placeHolder,
            });
        };
        /**
         * Get the list element inside an element, or create one if it does not
         * exists.
         * @param {HTMLElement} el
         * @return {HTMLElement} list
         */
        const getChildList = (el) => {
            let list = el.querySelector(ctx.listType);
            if (!list) {
                list = document.createElement(ctx.listType);
                el.appendChild(list);
            }
            return list;
        };

        const position = {
            previous: ctx.current.placeHolder.previousElementSibling,
            next: ctx.current.placeHolder.nextElementSibling,
            parent: ctx.nest
                ? ctx.current.placeHolder.parentElement.closest(ctx.elementSelector)
                : false,
            group: ctx.groupSelector ? ctx.current.placeHolder.closest(ctx.groupSelector) : false,
        };
        /** If nesting elements is allowed, horizontal moves may change the
         * parent of the placeholder element (the placeholder does not move
         * above or under an element, but it changes parent):
         *
         * - Moving to the left makes the placeholder a child of the previous
         *   element up in the nested hierarchy, only if the placeholder is the
         *   last child of its current parent:
         *
         *                    Allowed:
         *    el                           el
         *     ┣ parent                     ┣ parent
         *     ┃  ┣ child           -->     ┃  ┗ child
         *     ┃  ┗ placeholder             ┣ placeholder
         *     ┗ el                         ┗ el
         *
         *                  Not Allowed:
         *    el                           el
         *     ┣ parent                     ┣ parent
         *     ┃  ┣ placeholder     -->     ┣ p┃laceholder   <-- error
         *     ┃  ┗ child                   ┃  ┗ child
         *     ┗ el                         ┗ el
         *
         *
         * - Moving to the right makes the placeholder the last child of the
         * next element down in the nested hierarchy:
         *
         *    el                           el
         *     ┣ parent                    ┣ parent
         *     ┃  ┗ child           -->    ┃  ┣ child
         *     ┣ placeholder               ┃  ┗ placeholder
         *     ┗ el                        ┗ el
         */
        if (ctx.nest) {
            const xInterval = ctx.prevNestX - ctx.pointer.x;
            if (ctx.nestInterval - (-1) ** ctx.isRTL * xInterval < 0) {
                // Place placeholder after its parent in its parent's list only
                // if the placeholder is the last child of its parent
                // (ignoring the current element which is in the dom)
                let nextElement = position.next;
                if (nextElement === ctx.current.element) {
                    nextElement = nextElement.nextElementSibling;
                }
                if (!nextElement) {
                    const newSibling = position.parent;
                    if (newSibling) {
                        newSibling.after(ctx.current.placeHolder);
                        onMove(position);
                    }
                }
                // Recenter the pointer coordinates to this step
                ctx.prevNestX = ctx.pointer.x;
            } else if (ctx.nestInterval + (-1) ** ctx.isRTL * xInterval < 0) {
                // Place placeholder as the last child of its previous sibling,
                // (ignoring the current element which is in the dom)
                let parent = position.previous;
                if (parent === ctx.current.element) {
                    parent = parent.previousElementSibling;
                }
                if (parent) {
                    getChildList(parent).appendChild(ctx.current.placeHolder);
                    onMove(position);
                }
                // Recenter the pointer coordinates to this step
                ctx.prevNestX = ctx.pointer.x;
            }
        }
        const closestEl = document.elementFromPoint(ctx.selectorX, ctx.pointer.y);
        if (!closestEl) {
            // Cursor outside of viewport
            return;
        }
        const element = closestEl.closest(ctx.elementSelector);
        // Vertical moves should move the placeholder element up or down.
        if (element && element !== ctx.current.placeHolder) {
            const eRect = element.getBoundingClientRect();
            const pos = ctx.current.placeHolder.compareDocumentPosition(element);
            // Place placeholder before the hovered element in its parent's
            // list. If the cursor is in the upper part of the element and
            // if the placeholder is currently after or inside the hovered
            // element. If the position is not allowed but nesting is allowed,
            // place the placeholder as the last child of the previous sibling
            // instead.
            if (ctx.pointer.y - eRect.y < 10) {
                if (pos === 2 || pos === 10) {
                    element.before(ctx.current.placeHolder);
                    onMove(position);
                    // Recenter the pointer coordinates to this step
                    ctx.prevNestX = ctx.pointer.x;
                }
            } else if (ctx.pointer.y - eRect.y > 15 && pos === 4) {
                // Place placeholder after the hovered element in its parent's
                // list if the cursor is not in the upper part of the
                // element and if the placeholder is currently before the
                // hovered element.
                // If nesting is allowed, place the placeholder as the first
                // child of the hovered element instead.
                if (ctx.nest) {
                    getChildList(element).prepend(ctx.current.placeHolder);
                    onMove(position);
                    // Recenter the pointer coordinates to this step
                    ctx.prevNestX = ctx.pointer.x;
                } else {
                    element.after(ctx.current.placeHolder);
                    onMove(position);
                }
            }
        } else {
            const group = closestEl.closest(ctx.groupSelector);
            if (group && group !== position.group) {
                if (group.compareDocumentPosition(position.group) === 2) {
                    getChildList(group).prepend(ctx.current.placeHolder);
                    onMove(position);
                } else {
                    getChildList(group).appendChild(ctx.current.placeHolder);
                    onMove(position);
                }
                // Recenter the pointer coordinates to this step
                ctx.prevNestX = ctx.pointer.x;
                callHandler("onGroupEnter", { group, element: ctx.current.placeHolder });
                callHandler("onGroupLeave", {
                    group: position.group,
                    element: ctx.current.placeHolder,
                });
            }
        }
    },
    // If the drop position is different from the starting position, run the
    // onDrop handler from the parameters.
    onDrop({ ctx }) {
        const previous = ctx.current.placeHolder.previousElementSibling;
        const next = ctx.current.placeHolder.nextElementSibling;
        if (previous !== ctx.current.element && next !== ctx.current.element) {
            return {
                element: ctx.current.element,
                group: ctx.currentGroup,
                previous,
                next,
                newGroup: ctx.groupSelector && ctx.current.placeHolder.closest(ctx.groupSelector),
                parent: ctx.current.placeHolder.parentElement.closest(ctx.elementSelector),
                placeholder: ctx.current.placeHolder,
            };
        }
    },
    // Run the onDragEnd handler from the parameters.
    onDragEnd({ ctx }) {
        return {
            element: ctx.current.element,
            group: ctx.currentGroup,
        };
    },
});
