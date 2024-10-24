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
<<<<<<< saas-17.4
            trigger: 'a[data-event-id="1"]',
        },
||||||| 23c4587dcbca7ad874ff84a3f4151eeae2edf145
            trigger: 'a[data-event-id="1"]',
            isCheck: true,
        }
=======
            trigger: 'a[data-event-id="2"]',
            isCheck: true,
        }
>>>>>>> f960c373651b15748971a7f2cd107328f36c1a06
    ],
});

registry.category("web_tour.tours").add("test_drag_and_drop_event_in_calendar", {
    test: true,
    steps: () => [
        {
<<<<<<< saas-17.4
            content: "Move event to Wednesday 1 PM",
            trigger: 'a[data-event-id="1"]',
            run: 'drag_and_drop td.fc-timegrid-slot-lane[data-time="13:30:00"]',
||||||| 23c4587dcbca7ad874ff84a3f4151eeae2edf145
            content: "Move event to Wednesday 1.15 PM",
            trigger: 'a[data-event-id="1"]',
            run: 'drag_and_drop_native td.fc-timegrid-slot-lane[data-time="13:30:00"]',
=======
            content: "Open calendar display selector",
            trigger: ".scale_button_selection",
>>>>>>> f960c373651b15748971a7f2cd107328f36c1a06
        },
        {
<<<<<<< saas-17.4
            content: "Move recurrence to Wednesday 2.30 PM (nothing should happen)",
||||||| 23c4587dcbca7ad874ff84a3f4151eeae2edf145
            content: "Move recurrence to Wednesday 2.45 PM (nothing should happen)",
=======
            content: "Select monthly display",
            trigger: ".o_scale_button_month",
        },
        {
            content: "Move event to 15th of the month",
            trigger: 'a[data-event-id="1"]',
            run: 'drag_and_drop_native .fc-daygrid-day[data-date$="15"]',
        },
        {
            content: "Move occurrence to 20th of the month (nothing should happen)",
>>>>>>> f960c373651b15748971a7f2cd107328f36c1a06
            trigger: 'a[data-event-id="2"]',
<<<<<<< saas-17.4
            run: 'drag_and_drop td.fc-timegrid-slot-lane[data-time="15:00:00"]',
||||||| 23c4587dcbca7ad874ff84a3f4151eeae2edf145
            run: 'drag_and_drop_native td.fc-timegrid-slot-lane[data-time="15:00:00"]',
=======
            run: 'drag_and_drop_native .fc-daygrid-day[data-date$="20"]',
>>>>>>> f960c373651b15748971a7f2cd107328f36c1a06
        },
    ],
});
