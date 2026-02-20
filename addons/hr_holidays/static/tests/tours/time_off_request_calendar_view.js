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
<<<<<<< b5398fbead86ecbca6fa0983c3f1837e8132629a
            trigger: ".fc-daygrid-day.fc-day-thu",
            run: () => {
                const el = document.querySelector(".fc-daygrid-day.fc-day-thu:not(.fc-day-disabled)").firstChild;
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
||||||| e1a108427aefcae0bd51860f948a84aed89c6769
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
=======
            trigger: ".fc-daygrid-day.fc-day-thu .fc-daygrid-day-number",
            run: "click",
>>>>>>> d6c5c0ee173eb5c5caf26b8b53b55cbfa7ad39ce
        },
        {
            content: "Save the leave",
            trigger: '.o_form_button_save',
            run: "click",
        },
    ],
});
