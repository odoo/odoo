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
            content: "Access recurrence",
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
            trigger: 'a[data-event-id="1"]',
        },
    ],
});

registry.category("web_tour.tours").add("test_drag_and_drop_event_in_calendar", {
    steps: () => [
        {
            content: "Move event to Wednesday 1 PM",
            trigger: 'a[data-event-id="1"]',
            run: 'drag_and_drop td.fc-timegrid-slot-lane[data-time="13:30:00"]',
        },
        {
            content: "Move recurrence to Wednesday 2.30 PM (nothing should happen)",
            trigger: 'a[data-event-id="2"]',
            run: 'drag_and_drop td.fc-timegrid-slot-lane[data-time="15:00:00"]',
        },
    ],
});
