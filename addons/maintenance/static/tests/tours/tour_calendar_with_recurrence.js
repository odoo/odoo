/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_dblclick_event_from_calendar", {
    steps: () => [
        {
            content: "Enter event form",
            trigger: 'a[data-event-id="1"]',
            run: "dblclick",
        },
        {
            content: "Change the name of the form",
            trigger: "input#name_0",
            run: "edit make your bed",
        },
        {
            content: "Save name change",
            trigger: 'button[data-hotkey="s"]',
            run: "click",
        },
        {
            content: "Return to calendar",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "Move to next week",
            trigger: ".o_calendar_button_next",
            run: "click",
        },
        {
            content: "Access occurrence",
            trigger: 'a[data-event-id="2"]',
            run: "dblclick",
        },
        {
            content: "Change equipment",
            trigger: "input#duration_0",
            run: "edit 2:00",
        },
        {
            content: "Save duration change",
            trigger: 'button[data-hotkey="s"]',
            run: "click",
        },
        {
            content: "Return to calendar",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            trigger: 'a[data-event-id="2"]',
        },
    ],
});

registry.category("web_tour.tours").add("test_drag_and_drop_event_in_calendar", {
    steps: () => [
        {
            content: "Open calendar display selector",
            trigger: ".scale_button_selection",
            run: "click",
        },
        {
            content: "Select monthly display",
            trigger: ".o_scale_button_month",
            run: "click",
        },
        {
            content: "Wait the view is month",
            trigger: ".fc-dayGridMonth-view",
        },
        {
            content: "Move event to 15th of the month",
            trigger: 'a[data-event-id="1"]',
            run: 'drag_and_drop .fc-daygrid-day[data-date$="15"] .fc-daygrid-day-events',
        },
        {
            content: "Move occurrence to 20th of the month (nothing should happen)",
            trigger: 'a[data-event-id="2"]',
            run: 'drag_and_drop .fc-daygrid-day[data-date$="20"] .fc-daygrid-day-events',
        },
    ],
});
