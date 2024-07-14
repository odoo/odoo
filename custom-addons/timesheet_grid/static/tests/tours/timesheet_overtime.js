/** @odoo-module */

import { registry } from "@web/core/registry";

function daysToLastWeekWednesday() {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const daysUntilPreviousWed = (dayOfWeek + 7 - 3) % 7;
    const daysToLastWeekWed = dayOfWeek >= 3 ? 7 + daysUntilPreviousWed : daysUntilPreviousWed;
    return daysToLastWeekWed;
}

function goBackNDays(n) {
    return Array(n).fill({
        content: "Go to the previous Day",
        trigger: "button span[title='Previous']",
    });
}

registry.category("web_tour.tours").add("timesheet_overtime", {
    test: true,
    url: "/web",
    steps: () => [
        {
            content: "Open Timesheet app.",
            trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
        },
        {
            content: "Click on Timesheets",
            trigger: "button[data-menu-xmlid='hr_timesheet.menu_hr_time_tracking']",
        },
        {
            content: "Click on All Timesheets",
            trigger: "a[data-menu-xmlid='hr_timesheet.timesheet_menu_activity_all']",
        },
        {
            content: "Search for Test Employee",
            trigger: ".o_searchview_input_container input",
            run: "text Test Employee",
        },
        {
            content: "Search by Employee",
            trigger: ".o_searchview_input_container ul li:nth-child(2)",
        },
        {
            content: "Choose Day scale - 1",
            trigger: ".dropdown-toggle.scale_button_selection",
        },
        {
            content: "Choose Day scale - 2",
            trigger: ".o-dropdown .o-dropdown--menu span:contains('Day')",
        },
        ...goBackNDays(daysToLastWeekWednesday()),
        {
            content: "Check overtime is shown",
            trigger: "div[name='employee_id'] .o_timesheet_overtime_indication:contains('+08:00')",
            run: () => {},
        },
    ],
});
