/** @odoo-module */
import { registry } from "@web/core/registry";
import { delay } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add('timesheet_record_time', {
    url: "/odoo",
    steps: () => [
    {
        trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
        content: "Open Timesheet app.",
        run: "click"
    },
    {
        trigger: '.btn_start_timer',
        content: "Launch the timer to start a new activity.",
        run: "click"
    },
    {
        trigger: 'div[name=name] input',
        content: "Describe your activity.",
        run: "edit Description"
    },
    {
        trigger: '.timesheet-timer div[name="project_id"] input',
        content: "Select the project on which you are working.",
        run: "edit Test Project",
    },
    {
        isActive: ["auto"],
        trigger: ".ui-autocomplete > li > a:contains(Test Project)",
        run: "click",
    },
    {
        trigger: '.btn_stop_timer',
        content: "Stop the timer when you are done.",
        run: "click"
    }
]});

registry.category("web_tour.tours").add('timesheet_overtime_hour_encoding', {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
            content: "Open Timesheet app.",
            run: "click"
        },
        {
            trigger: "button.btn.btn-secondary span[title='Previous']",
            run: "click"
        },
        {
            trigger: ".o_grid_row",
            run: async () => {
                await delay(300);
            }
        },
        {
            trigger: ".o_grid_row",
            run: async function () {
                let expectedValues = ["+2:00", "+1:00", "-1:00", "-2:00", "-3:00"];
                document.querySelectorAll(".o_grid_bar_chart_overtime[title='Daily overtime']")
                    .forEach((span, index) => {
                        if (span.textContent.trim() !== expectedValues[index]) {
                            throw new Error(`Tour stopped: Expected ${expectedValues[index]}, but found ${span.textContent.trim()}`);
                        }
                    });
            },
        },
        {
            trigger: ".o_grid_bar_chart_overtime[title='Total overtime']:contains('+5:00'):not(:visible)",
            run: "hover",
        },
    ]
});


registry.category("web_tour.tours").add('timesheet_overtime_day_encoding', {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
            content: "Open Timesheet app.",
            run: "click"
        },
        {
            trigger: "button.btn.btn-secondary span[title='Previous']",
            run: "click"
        },
        {
            trigger: ".o_grid_row",
            run: async () => {
                await delay(300);
            }
        },
        {
            trigger: ".o_grid_row",
            run: async function () {
                let expectedValues = ["+0.25", "-0.13", "-0.25", "-0.38"];
                document.querySelectorAll(".o_grid_bar_chart_overtime[title='Daily overtime']")
                    .forEach((span, index) => {
                        if (span.textContent.trim() !== expectedValues[index]) {
                            throw new Error(`Tour stopped: Expected ${expectedValues[index]}, but found ${span.textContent.trim()}`);
                        }
                    });
            },
        },
        {
            trigger: ".o_grid_bar_chart_overtime[title='Total overtime']:contains('-0.50'):not(:visible)",
            run: "hover",
        },
    ]
});
