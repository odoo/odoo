/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

    // let employeeName = document.querySelector('.oe_topbar_name').firstChild.textContent;
    registry.category("web_tour.tours").add('hr_homeworking_calendar_request_calendar_view', {
        test: true,
        url: '/web',
        steps: () => [stepUtils.showAppsMenuItem(),
        {
            content: "Open Calendar app",
            trigger: '.o_app[data-menu-xmlid="calendar.mail_menu_calendar"]',
            run: 'click',
        },
        {
            content: "Add a location for thursday",
            trigger: '.fc-day-header.fc-thu .btnWorklocation',
            run: 'click',
        },
        {
            content: "Set a weekly Location",
            trigger: '.o-checkbox',
            run: 'click',
        },
        {
            content: "Choose a Location",
            trigger: 'input#work_location_id_0.o_input',
            run: function () {},
        },
        {
            content: "Create your new thursday's location",
            trigger: '.btn:contains("Set Location")',
            run: 'click',
        }
        //TO DO : finish tour with the worklocation in employee profile
    ]});