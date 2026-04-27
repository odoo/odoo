import { registry } from "@web/core/registry";

function daysToLastWeekWednesday() {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const daysUntilPreviousWed = (dayOfWeek + 7 - 3) % 7;
    const daysToLastWeekWed =
        dayOfWeek >= 3 || dayOfWeek == 0 ? 7 + daysUntilPreviousWed : daysUntilPreviousWed;
    return daysToLastWeekWed;
}

function goBackNDays(n) {
    return Array(n).fill({
        content: "Go to the previous Day",
        trigger: "button span[title='Previous']",
        run: "click",
    });
}

registry.category("web_tour.tours").add("timesheet_overtime", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open Timesheet app.",
            trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
            run: "click",
        },
        {
            content: "Click on Timesheets",
            trigger: "button[data-menu-xmlid='hr_timesheet.menu_hr_time_tracking']",
            run: "click",
        },
        {
            content: "Click on All Timesheets",
            trigger: "a[data-menu-xmlid='hr_timesheet.timesheet_menu_activity_all']",
            run: "click",
        },
        {
            content: "Choose Day scale - 1",
            trigger: ".dropdown-toggle.scale_button_selection",
            run: "click",
        },
        {
            content: "Choose Day scale - 2",
            trigger: ".dropdown-menu.o-dropdown--menu span:contains('Day')",
            run: "click",
        },
        ...goBackNDays(daysToLastWeekWednesday()),
        {
            content: "Check overtime is shown",
            trigger: "div[name='employee_id'] .o_timesheet_overtime_indication:contains('+08:00')",
            run: () => {},
        },
    ],
});
