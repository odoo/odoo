import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_request_calendar_view", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the first Thursday of the year",
            trigger: ".o_calendar_day[data-date]",
            async run({ click }) {
                let date = luxon.DateTime.local().startOf("year");
                while (date.weekday !== 4) {
                    date = date.plus({ days: 1 });
                }
                const cell = document.querySelector(
                    `.o_calendar_day[data-date="${date.toISODate()}"]`
                );
                // the year view is scrolled to the current month
                cell.scrollIntoView({ block: "center" });
                await click(cell);
            },
        },
        {
            content: "Save the leave",
            trigger: '.o_form_button_save',
            run: "click",
        },
    ],
});
