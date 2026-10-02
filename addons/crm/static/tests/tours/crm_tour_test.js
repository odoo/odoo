import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("crm_tour_test", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
            content: "Ready to boost your sales? Let's have a look at your Pipeline.",
            run: "click",
        },
        {
            trigger: ".o_opportunity_kanban .o_kanban_renderer",
        },
        {
            trigger: ".o_opportunity_kanban .o-kanban-button-new",
            content: "Create your first opportunity.",
            run: "click",
        },
        {
            trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id'] input",
            content: "Write a few letters to look for a company, or create a new one.",
            run: "edit Brandon Freeman",
        },
        {
            trigger: ".ui-menu-item > a:contains('Brandon Freeman')",
            run: "click",
        },
        {
            trigger: ".o_kanban_quick_create .o_field_widget[name='name'] input:value('Brandon Freeman')",
        },
        {
            trigger: ".o_kanban_quick_create .o_kanban_add",
            content: "Now, add your Opportunity to your Pipeline.",
            run: "click",
        },
        {
            trigger: ".o_opportunity_kanban .o_kanban_renderer",
        },
        {
            trigger: ".o_opportunity_kanban:not(:has(.o_view_sample_data)) .o_kanban_group .o_kanban_record:last-of-type",
            content: "Drag & drop opportunities between columns as you progress in your sales cycle.",
            run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(1))",
        },
        {
            trigger: ".o_opportunity_kanban .o_kanban_renderer",
        },
        {
            // Choose the element that is not going to be moved by the previous step.
            trigger: ".o_opportunity_kanban .o_kanban_group .o_kanban_record .o-mail-ActivityButton",
            content: "Looks like nothing is planned.",
            run: "click",
        },
        {
            trigger: ".o_opportunity_kanban .o_kanban_renderer",
        },
        {
            trigger: ".o-mail-ActivityListPopover button:contains(Schedule an activity)",
            content: "Let's Schedule an Activity.",
            run: "click",
        },
        {
            trigger: '.modal-footer button[name="action_schedule_activities"]',
            content: "All set. Let’s Schedule it.",
            run: "click",
        },
        {
            trigger: ".o_kanban_record",
            content: "Let’s have a look at an Opportunity.",
            run: "click",
        },
        {
            trigger: ".o_lead_opportunity_form .o_statusbar_status",
            content: "You can make your opportunity advance through your pipeline by clicking on stages here. Try sending it to the next stage!",
            run: "click",
        },
        {
            trigger: ".breadcrumb-item:not(.active):first",
            content: "Click on the breadcrumbs to go back to your Pipeline. Odoo will save all your changes as you navigate.",
            run: "click .breadcrumb-item:not(.active):last",
        },
        {
            trigger: ".o_opportunity_kanban .o_kanban_record:last-of-type",
            content: "Drag your opportunity to Won when you get the deal. Congrats!",
            run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(3))",
        },
    ],
});
