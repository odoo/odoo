import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_card_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the Time Off card to open the detailed popover.",
            trigger: ".o_timeoff_card_inner",
            run: "click",
        },
        {
            content: "Verify popover is displayed",
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
            trigger: ".o_timeoff_card_inner",
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
            trigger: ".o_timeoff_card_inner",
            run: "click",
        },
        {
            content: "Click on the link containing 'Pending'",
            trigger: ".o_popover .btn-link:contains('Pending')",
            run: "click",
        },
        {
            content: "Ensure the list view for Time Off requests is displayed",
            trigger: ".o_list_view",
        },
    ],
});
