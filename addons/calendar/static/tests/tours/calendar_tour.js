import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const todayDate = function () {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");

    return `${month}/${day}/${year} 10:00:00`;
};

registry.category("web_tour.tours").add("calendar_appointments_hour_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="calendar.mail_menu_calendar"]',
            content: "Open Calendar",
            run: "click",
        },
        {
            trigger: ".o-calendar-button-new",
            content: "Create a new event",
            run: "click",
        },
        {
            trigger: "#name_0",
            content: "Give a name to the new event",
            run: "edit TEST EVENT",
        },
        {
            trigger: "div[name='start'] button",
            content: "Open the date picker",
            run: "click",
        },
        {
            trigger: "#start_0",
            content: "Give a date to the new event",
            run: `edit ${todayDate()}`,
        },
        {
            trigger: "#duration_0",
            content: "Give a duration to the new event",
            run: "edit 02:00",
        },
        {
            trigger: ".fa-cloud-upload",
            content: "Save the new event",
            run: "click",
        },
        {
            trigger: ".o_back_button",
            content: "Go back to Calendar view",
            run: "click",
        },
        {
            trigger: ".scale_button_selection",
            content: "Click to change calendar view",
            run: "click",
        },
        {
            trigger: '.dropdown-item:contains("Month")',
            content: "Change the calendar view to Month",
            run: "click",
        },
        {
            trigger: ".fc-col-header-cell.fc-day.fc-day-mon",
            content: "Check the day is properly displayed",
            run: "click",
        },
        {
            trigger: '.fc-time:contains("10:00")',
            content: "Check the time is properly displayed",
            run: "click",
        },
        {
            trigger: '.o_event_title:contains("TEST EVENT")',
            content: "Check the event title",
        },
    ],
});

const clickOnTheEvent = {
    content: "Click on the event (focus + waiting)",
    trigger: 'a .fc-event-main:contains("Test Event")',
    async run(actions) {
        await actions.click();
        await new Promise((r) => setTimeout(r, 1000));
        const custom = document.querySelector(".o_cw_custom_highlight");
        if (custom) {
            custom.click();
        }
    },
};

registry.category("web_tour.tours").add("test_calendar_delete_tour", {
    steps: () => [
        clickOnTheEvent,
        {
            trigger: ".o_cw_popover",
        },
        {
            content: "Delete the event",
            trigger: ".o_cw_popover_delete",
            run: "click",
        },
        {
            content: "Validate the deletion",
            trigger: 'button:contains("Delete")',
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("test_calendar_decline_tour", {
    steps: () => [
        clickOnTheEvent,
        {
            trigger: ".o_cw_popover",
        },
        {
            content: "Delete the event",
            trigger: ".o_cw_popover_delete",
            run: "click",
        },
        {
            content: "Wait declined status",
            trigger: ".o_attendee_status_declined",
        },
    ],
});
