/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("time_off_request_calendar_view", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the first Thursday of the year",
            trigger: ".fc-daygrid-day.fc-day-thu",
            run: () => {
                const el = document.querySelector(".fc-daygrid-day.fc-day-thu").firstChild;
                el.scrollIntoView();

                const fromPosition = el.getBoundingClientRect();
                fromPosition.x += el.offsetWidth / 2;
                fromPosition.y += el.offsetHeight / 2;

                el.dispatchEvent(
                    new MouseEvent("mousedown", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
                el.dispatchEvent(
                    new MouseEvent("mouseup", {
                        bubbles: true,
                        which: 1,
                        button: 0,
                        clientX: fromPosition.x,
                        clientY: fromPosition.y,
                    })
                );
            },
        },
        {
            content: "Save the leave",
            trigger: '.btn:contains("Save")',
            run: "click",
        },
    ],
});
