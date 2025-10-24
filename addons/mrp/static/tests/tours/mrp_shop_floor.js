import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("test_work_order_dependency", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Activate work center",
            run: "click",
            trigger: '.btn-primary:contains(Activate your Work Centers)'
        },
        {
            content: "Open the Shop Floor app",
            run: "click",
            trigger: '.o_workcenter_button:contains(Simple Workcenter)'
        },
        {
            content: "Open the Shop Floor app",
            run: "click",
            trigger: '.o_workcenter_button:contains(Nuclear Workcenter)'
        },
        {
            content: "Open the Shop Floor app",
            run: "click",
            trigger: '.btn:contains(confirm)'
        },
        {
            content: "Open the Shop Floor app",
            run: 'click',
            trigger: '.o_work_center_btn:contains(Simple Workcenter)'
        },
        {
            content: "Open the Shop Floor app",
            run: 'click',
            trigger: '.o_searchview_dropdown_toggler'
        },
        {
            content: "Open the Shop Floor app",
            run: 'click',
            trigger: '.o-dropdown-item:contains(Blocked)'
        },
        {
            content: "Open the Shop Floor app",
            run: 'click',
            trigger: '.o_searchview_dropdown_toggler'
        },
        {
            content: "Open the Shop Floor app",
            run: 'click',
            trigger: '.o_mrp_display_record_start_btn'
        },
        {
            content: "Open the Shop Floor app",
            run: () => {},
            trigger: '.text-prewrap:contains(You cannot start a work order that is blocked by an other one)'
        },
    ],
});
