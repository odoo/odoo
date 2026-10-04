import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_dblclick_event_from_calendar", {
    steps: () => [
        {
            content: "Enter event form",
            trigger: '.o_event[data-event-id="1"]',
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
            trigger: '.o_event[data-event-id="2"]',
            run: "dblclick",
        },
        {
            content: "Change Scheduled End",
            trigger: "button.o_daterange_end",
            run: "click",
        },
        {
            trigger: 'input[data-field="schedule_end"]',
            async run({ edit, anchor }) {
                const value = luxon.DateTime.fromFormat(anchor.value, "MM/dd/yyyy hh:mm:ss a")
                    .plus({ hours: 1 })
                    .toFormat("MM/dd/yyyy hh:mm:ss a");
                await edit(value);
            },
        },
        {
            content: "Return to calendar",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            trigger: '.o_event[data-event-id="2"]',
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
            content: 'Wait for monthly view to load',
            trigger: '.o_calendar_fc_view_dayGridMonth',
        },
        {
            content: "Move event to 15th of the month",
            trigger: '.o_event[data-event-id="1"]',
            run: ({ drag_and_drop }) =>
                drag_and_drop('.o_calendar_day[data-date$="15"]', { position: "center", relative: true }),
        },
        {
            content: "Move occurrence to 20th of the month (nothing should happen)",
            trigger: '.o_event[data-event-id="2"]',
            run: ({ drag_and_drop }) =>
                drag_and_drop('.o_calendar_day[data-date$="20"]', { position: "center", relative: true }),
        },
    ],
});
