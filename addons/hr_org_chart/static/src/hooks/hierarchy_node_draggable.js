/** @odoo-module */

import { onWillUnmount, reactive, useEffect, useExternalListener } from "@odoo/owl";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { pick } from "@web/core/utils/objects";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";

const hookParams = {
    name: "useHierarchyNodeDraggable",
    acceptedParams: {
        rows: [String],
    },
    defaultParams: {
        rows: null,
    },
    onComputeParams({ ctx, params }) {
        // Row selector
        ctx.rowSelector = params.rows || null;
        if (ctx.rowSelector) {
            ctx.fullSelector = `${ctx.rowSelector} ${ctx.fullSelector}`;
        }
    },
    onDragStart(params) {
        const { ctx, addListener, callHandler } = params;

        const onElementPointerEnter = (ev) => {
            const element = ev.currentTarget;
            current.hierarchyElement = element;
            callHandler("onElementEnter", { element });
        };

        const onElementPointerLeave = (ev) => {
            const element = ev.currentTarget;
            current.hierarchyElement = null;
            callHandler("onElementLeave", { element });
        };

        const onRowPointerEnter = (ev) => {
            const row = ev.currentTarget;
            current.hierarchyRow = row;
            callHandler("onRowEnter", { row });
        };

        const onRowPointerLeave = (ev) => {
            const row = ev.currentTarget;
            current.hierarchyRow = null;
            callHandler("onRowLeave", { row });
        };

        const { ref, current, elementSelector, rowSelector } = ctx;

        for (const rowEl of ref.el.querySelectorAll(rowSelector)) {
            addListener(rowEl, "pointerenter", onRowPointerEnter);
            addListener(rowEl, "pointerleave", onRowPointerLeave);
        }

        for (const siblingEl of ref.el.querySelectorAll(elementSelector)) {
            if (siblingEl !== current.element) {
                addListener(siblingEl, "pointerenter", onElementPointerEnter);
                addListener(siblingEl, "pointerleave", onElementPointerLeave);
            }
        }

        return pick(current, "element", "row");
    },
    onDragEnd({ ctx }) {
        return pick(ctx.current, "element", "row", "hierarchyRow");
    },
    onDrop({ ctx }) {
        const { current } = ctx;
        const rowElement = current.hierarchyRow;
        const element = current.hierarchyElement;
        if ((rowElement && rowElement !== current.row) || element) {
            return {
                element: current.element,
                row: current.row,
                nextRow: rowElement && current.row !== rowElement ? rowElement : null,
                newParentNode: element,
            };
        }
    },
    onWillStartDrag({ ctx }) {
        const { current, rowSelector } = ctx;

        if (rowSelector) {
            current.row = current.element.closest(rowSelector);
        }

        return pick(current, "element", "row");
    },
};

export function useHierarchyNodeDraggable(params) {
    const setupHooks = {
        addListener: useExternalListener,
        setup: useEffect,
        teardown: onWillUnmount,
        throttle: useThrottleForAnimation,
        wrapState: reactive,
    }
    return makeDraggableHook({ ...hookParams, setupHooks })(params);
}
