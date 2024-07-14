/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { useComponent, useEffect, useEnv, useState } from "@odoo/owl";

/**
 * Common code between common and year renderer for our calendar.
 */
export function useAppointmentRendererHook(getFcElements) {
    const component = useComponent();
    const env = useEnv();
    useState(env.calendarState);

    /**
     * Display an overlay when using the slots selection mode that
     * encompasses the past time.
     */
    useEffect(
        (fcEls, calendarMode) => {
            if (calendarMode === "slots-creation") {
                for (const fcEl of fcEls) {
                    const daysToDisable = fcEl.querySelectorAll(".fc-past, .fc-today");
                    for (const el of daysToDisable) {
                        el.classList.add("o_calendar_slot_selection");
                    }
                    const todayColumn = fcEl.querySelectorAll(".fc-today")[2];
                    // Create a block for today to have the overlay size based on the current hour
                    if (todayColumn && todayColumn.childElementCount === 0 && ['timeGridWeek', 'timeGridDay'].includes(component.fc.api.state.viewType)) {
                        const deltaTodayNow = component.fc.api.view.timeGrid.computeDateTop(component.fc.api.getInitialDate());
                        const childEl = document.createElement("div");
                        childEl.classList.add("o_calendar_slot_selection_now");
                        childEl.style.height = `${deltaTodayNow - 13}px`;
                        todayColumn.appendChild(childEl);
                    }
                }
                return () => {
                    for (const fcEl of fcEls) {
                        const daysToDisable = fcEl.querySelectorAll(".fc-past, .fc-today");
                        for (const el of daysToDisable) {
                            el.classList.remove("o_calendar_slot_selection");
                        }
                        const todayColumn = fcEl.querySelectorAll(".fc-today")[2];
                        if (todayColumn) {
                            const childEl = todayColumn.querySelector(".o_calendar_slot_selection_now");
                            childEl && childEl.remove();
                        }
                    }
                };
            }
        },
        () => [getFcElements(), env.calendarState.mode],
    );
    return {
        isSlotCreationMode() {
            return env.calendarState.mode === "slots-creation";
        },

        getEventTimeFormat() {
            const format12Hour = {
                hour: 'numeric',
                minute: '2-digit',
                omitZeroMinute: true,
                meridiem: 'short'
            };
            const format24Hour = {
                hour: 'numeric',
                minute: '2-digit',
                hour12: false,
            };
            return localization.timeFormat.search("HH") === 0 ? format24Hour : format12Hour;
        },
    }
}
