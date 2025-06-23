import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_card_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the Time Off name",
            trigger: '.o_timeoff_name:not(:contains("Pending Requests"))',
            run: "click",
        },
        {
            content: "Ensure the list view for Time Off requests is displayed",
            trigger: ".o_list_view",
        },
        {
            content: "Navigate back to the previous view",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "Click on the time off card to open the detailed popover.",
            trigger: "span.o_timeoff_details",
            run: "click",
        },
        {
            content: "Verify that the popover is displayed after clicking on the time off details.",
            trigger: ".o_popover",
        },
        {
            content: "Click on the link containing 'Allocated'.",
            trigger: ".o_popover .btn-link:contains('Allocated')",
            run: "click",
        },
        {
            content: "Ensure the list view for Time Off requests is displayed",
            trigger: ".o_list_view",
        },
        {
            content: "Navigate back to the previous view",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "Click on the time off card to open the detailed popover.",
            trigger: "span.o_timeoff_details",
            run: "click",
        },
        {
            content: "Click on the link containing 'Approved'",
            trigger: ".o_popover .btn-link:contains('Approved')",
            run: "click",
        },
        {
            content: "Ensure the list view for Time Off requests is displayed",
            trigger: ".o_list_view",
        },
        {
            content: "Navigate back to the previous view",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "Click on the time off card to open the detailed popover.",
            trigger: "span.o_timeoff_details",
            run: "click",
        },
        {
            content: "Click on the link containing 'Planned'",
            trigger: ".o_popover .btn-link:contains('Planned')",
            run: "click",
        },
        {
            content: "Ensure the list view for Time Off requests is displayed",
            trigger: ".o_list_view",
        },
    ],
});
