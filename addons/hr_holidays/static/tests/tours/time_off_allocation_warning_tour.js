import { registry } from '@web/core/registry';
import { stepUtils } from "@web_tour/tour_utils";

const today = luxon.DateTime.now();
const pastDateFrom = today.minus({ days: 3 }).toFormat("MM/dd/yyyy");
const pastDateTo = today.minus({ days: 2 }).toFormat("MM/dd/yyyy");
const futureDateTo = today.plus({ days: 2 }).toFormat("MM/dd/yyyy");
const warningText = "The allocated days cannot be used, because the allocation is set to finish in the past.";

registry.category("web_tour.tours").add("time_off_allocation_warning_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Click Time Off",
            trigger: ".o_app[data-menu-xmlid='hr_holidays.menu_hr_holidays_root']",
            run: "click",
        },
        {
            content: "Open Management menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_holidays.menu_hr_holidays_management']",
            run: "click",
        },
        {
            content: "Go to Allocations",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays.hr_holidays_menu_manager_approve_allocations']",
            run: "click",
        },
        {
            content: "Create a new allocation",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Click to select a leave type",
            trigger: ".o_field_widget[name='holiday_status_id'] input",
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu > li > a[id=holiday_status_id_0_0_0]",
            run: "click",
        },
        {
            content: "Open the start date picker",
            trigger: ".o_field_widget[name='date_from'] button",
            // Past date to trigger the warning
            run: "click",
        },
        {
            content: "Edit the start date picker",
            trigger: ".o_field_widget[name='date_from'] input",
           // Past date to trigger the warning
            run: `click && edit ${pastDateFrom}`,
        },
        {
            content: "Edit the end date picker",
            trigger: ".o_field_widget[name='date_to'] input",
            // Past date to trigger the warning
            run: `click && edit ${pastDateTo} && click body`,
        },
        {
            content: "Error regarding allocation to be visible",
            trigger: `.o_cell:has(.o_row[name='validity']) + div span:contains(${warningText})`,
        },
        {
            content: "Open the end date picker",
            trigger: ".o_field_widget[name='date_to'] button",
            run: "click",
        },
        {
            content: "Edit the end date picker",
            trigger: ".o_field_widget[name='date_to'] input",
            run: `click && edit ${futureDateTo} && click body`,
        },
        {
            content: "Error regarding allocation to be visible",
            trigger: `.o_cell:has(.o_row[name='validity']) + div:not(:has(span:not(:contains(${warningText}))))`,
        },
        ...stepUtils.saveForm(),
    ],
});
