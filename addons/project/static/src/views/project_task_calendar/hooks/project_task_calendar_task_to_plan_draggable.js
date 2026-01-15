import { onWillUnmount, reactive, useEffect, useExternalListener } from "@odoo/owl";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder";
import { pick } from "@web/core/utils/objects";
import { useThrottleForAnimation } from "@web/core/utils/timing";

const hookParams = {
    name: "useCalendarTaskToPlanDraggable",
    onDragStart(params) {
        const { ctx, addClass, addListener, addStyle, callHandler, getRect, removeClass, removeStyle } = params;

        const onElementPointerEnter = (ev) => {
            const element = ev.currentTarget;
            current.calendarCell = element;
            if (current.timeSlotElement) {
                current.timeSlotElement = null;
            }
            callHandler("onElementEnter", { element });
        };

        const onElementPointerLeave = (ev) => {
            const element = ev.currentTarget;
            current.calendarCell = null;
            callHandler("onElementLeave", { element });
        };

        const onTimeSlotElementPointerEnter = (ev) => {
            const element = ev.currentTarget;
            current.timeSlotElement = element;
            callHandler("onElementEnter", { element });
        }

        const onTimeSlotElementPointerLeave = (ev) => {
            const element = ev.currentTarget;
            current.timeSlotElement = null;
            callHandler("onElementLeave", { element })
        }

        const { ref, current } = ctx;
        const containerSelector = ".o_calendar_renderer .o_calendar_widget";
        let selector = `${containerSelector} .fc-timegrid-slot.fc-timegrid-slot-lane`;
        const slotElements = ref.el.querySelectorAll(selector);
        if (slotElements.length) {
            const eventContainer = ref.el.querySelector(".o_calendar_renderer .o_task_event_to_plan_container");

            const onTimeGridPointerMove = (ev) => {
                current.calendarCell = null;
                const nodes = document.elementsFromPoint(ev.clientX, ev.clientY);
                for (const node of nodes) {
                    if (node.classList.contains("fc-day")) {
                        if (!(current.calendarCell && node.isEqualNode(current.calendarCell))) {
                            current.calendarCell = node;
                        }
                        break;
                    }
                }
                if (eventContainer && current.calendarCell && current.timeSlotElement) {
                    const { bottom, height } = getRect(current.timeSlotElement, { adjust: true });
                    const { left, width } = getRect(current.calendarCell, { adjust: true });
                    addStyle(eventContainer, {
                        bottom: `${document.documentElement.clientHeight - bottom - height}px`,
                        width:`${width}px`,
                        left: `${left}px`,
                        height: `${height * 2}px`,
                    });
                    removeClass(eventContainer, "d-none");
                } else if (eventContainer) {
                    removeStyle(eventContainer, "bottom", "width", "left", "height");
                    addClass(eventContainer, "d-none");
                }
            }

            const onTimeGridPointerCancel = (ev) => {
                current.calendarCell = null;
                if (eventContainer) {
                    removeStyle(eventContainer, "bottom", "width", "left", "height");
                    addClass(eventContainer, "d-none");
                }
            }

            for (const timeSlotCalendarCell of slotElements) {
                addListener(timeSlotCalendarCell, "pointerenter", onTimeSlotElementPointerEnter);
                addListener(timeSlotCalendarCell, "pointerleave", onTimeSlotElementPointerLeave);
            }
            const timeSlotContainerEl = ref.el.querySelector(`${containerSelector} .fc-timegrid-body`);
            addListener(timeSlotContainerEl, "pointermove", onTimeGridPointerMove);
            addListener(timeSlotContainerEl, "pointercancel", onTimeGridPointerCancel);
        }
        selector = `${containerSelector} .fc-day`;
        for (const calendarCell of ref.el.querySelectorAll(selector)) {
            addListener(calendarCell, "pointerenter", onElementPointerEnter);
            addListener(calendarCell, "pointerleave", onElementPointerLeave);
        }
        return pick(current, "element");
    },
    onDragEnd({ ctx }) {
        return pick(ctx.current, "element", "calendarCell");
    },
    onDrop({ ctx}) {
        const { element, calendarCell, timeSlotElement } = ctx.current;
        if (element && calendarCell) {
            return {
                element,
                calendarCell,
                timeSlotElement,
            }
        }
    },
};
export function useCalendarTaskToPlanDraggable(params) {
    const setupHooks = {
        addListener: useExternalListener,
        setup: useEffect,
        teardown: onWillUnmount,
        throttle: useThrottleForAnimation,
        wrapState: reactive,
    };
    return makeDraggableHook({ ...hookParams, setupHooks })(params);
}
