import { luxon } from "@web/core/l10n/luxon";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_dblclick_event_from_calendar", {
    steps: () => [
        {
            content: "Enter event form",
            trigger: '.fc-event[data-event-id="1"]',
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
            trigger: '.fc-event[data-event-id="2"]',
            run: "dblclick",
        },
        {
            content: "Change Scheduled End",
            trigger: "button#date_scheduled_end_0",
            run: "click",
        },
        {
            trigger: "input#date_scheduled_end_0",
            async run({ edit, anchor }) {
                const value = luxon.DateTime.fromFormat(
                    anchor.value,
                    "MM/dd/yyyy hh:mm:ss a",
                )
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
            trigger: '.fc-event[data-event-id="2"]',
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
            content: "Wait for monthly view to load",
            trigger: ".fc-dayGridMonth-view",
        },
        {
            content: "Move event to 15th of the month",
            trigger: '.fc-event[data-event-id="1"]',
            async run(helpers) {
                // Options, rather than the `run: "drag_and_drop ..."` string
                // form, and the empty object is the point: the string form
                // defaults to `position: "top"`, which hoot resolves to one
                // pixel ABOVE the target's top edge. Between list rows that
                // reads as "insert before this one"; in a date grid that pixel
                // belongs to the previous week, and the event landed a row
                // short of where the tour aimed. An empty object drops on the
                // cell's centre.
                await helpers.drag_and_drop('.fc-daygrid-day[data-date$="15"]', {});
            },
        },
        {
            content: "Move occurrence to 20th of the month (nothing should happen)",
            trigger: '.fc-event[data-event-id="2"]',
            async run(helpers) {
                // Centre of the cell, for the reason given on the step above.
                await helpers.drag_and_drop('.fc-daygrid-day[data-date$="20"]', {});
            },
        },
    ],
});
