/** @odoo-module */
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("hr_referral_utm_campaign_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_app[data-menu-xmlid='hr_recruitment.menu_hr_recruitment_root']",
            content: "Open recruitment app",
            run: "click",
        },
        {
            content: "select one job position",
            trigger: ".o_kanban_record:contains('Test Job Referral Campaign')",
            run: "hover && click .o_kanban_record:contains('Test Job Referral Campaign') .o_dropdown_kanban .dropdown-toggle",
        },
        {
            content: "Select referral campaign",
            trigger: "a.oe_kanban_action:contains('Referral Campaign')",
            run: "click",
        },
        {
            content: "Send the referral Campaign",
            trigger: "button:contains('Send')",
            run: "click",
        },
        ...stepUtils.toggleHomeMenu(),
    ]
})
