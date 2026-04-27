/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('timesheet_record_time_new_helpdesk_ticket', {
    url: "/web",
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
        run: "edit Project Helpdesk Team",
    },
    {
        isActive: ["auto"],
        trigger: ".ui-autocomplete > li > a:contains(Test Project Helpdesk Team)",
        run: "click",
    },
    {
        trigger: '.timesheet-timer div[name="helpdesk_ticket_id"] input',
        content: "Create a new Ticket.",
        run: "edit Test Helpdesk Ticket",
    },
    {
        isActive: ["auto"],
        trigger: ".ui-autocomplete > li > a:contains(Test Helpdesk Ticket)",
        run: "click",
    },
    {
        trigger: 'body',
        content: "Wait for the ticket to be created",
        run: function() {
            return new Promise(resolve => setTimeout(resolve, 1000));
        }
    },
    {
        trigger: '.btn_stop_timer',
        content: "Stop the timer when you are done.",
        run: "click"
    }
]});
