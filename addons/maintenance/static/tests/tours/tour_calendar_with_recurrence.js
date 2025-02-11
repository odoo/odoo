/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_dblclick_event_from_calendar", {
    test: true,
    steps: () => [
        {
            content: "Enter event form",
            trigger: 'a[data-event-id="1"]',
            run: "dblclick",
        },
        {
            content: "Change the name of the form",
            trigger: "input#name_0",
            run: "text make your bed",
        },
        {
            content: "Return to calendar",
            trigger: ".o_back_button",
        },
        {
            content: "Move to next week",
            trigger: ".o_calendar_button_next"
        },
        {
            content: "Access occurrence",
            trigger: 'a[data-event-id="2"]',
            run: "dblclick",
        },
        {
            content: "Change equipment",
            trigger: "input#duration_0",
            run: "text 2:00"
        },
        {
            content: "Return to calendar",
            trigger: ".o_back_button",
        },
        {
            trigger: 'a[data-event-id="2"]',
            isCheck: true,
        }
    ],
});

registry.category("web_tour.tours").add("test_drag_and_drop_event_in_calendar", {
    test: true,
    steps: () => [
        {
            content: "Open calendar display selector",
            trigger: ".scale_button_selection",
        },
        {
            content: "Select monthly display",
            trigger: ".o_scale_button_month",
        },
        {
            trigger: '.fc-dayGridMonth-view',
            isCheck: true,
        },
        {
            content: "Move event to 15th of the month",
            trigger: 'a[data-event-id="1"]',
            run: 'drag_and_drop_native .fc-day.fc-widget-content[data-date$="15"]',
        },
        {
            content: "Move occurrence to 20th of the month (nothing should happen)",
            trigger: 'a[data-event-id="2"]',
            run: 'drag_and_drop_native .fc-day.fc-widget-content[data-date$="20"]',
        },
    ],
});
