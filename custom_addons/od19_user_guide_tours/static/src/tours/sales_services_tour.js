import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sales Services Tour
 *
 * Walks the user through the customer-service queue added by
 * od19_helpdesk_extension (Sales > Sales Services):
 *  1. Sales > Sales Services > My Service Tickets (personal queue)
 *  2. Sales > Sales Services > Service Tickets (all customer-service tickets)
 *  3. Log a new service request
 *
 * The menus are restricted to the "Sales Services" group.
 */
registry.category("web_tour.tours").add("od19_sales_services_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's follow the <b>Sales Services</b> tickets (บริการลูกค้า)."))
        ),

        // --- My Service Tickets ---
        {
            trigger: navSection("Sales Services"),
            content: markup(_t("Open the <b>Sales Services</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("My Service Tickets"),
            content: markup(_t(
                "Open <b>My Service Tickets</b> — only the customer-service tickets " +
                "assigned to you."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("My Service Tickets"),
        {
            trigger: ".o_kanban_view, .o_list_renderer",
            content: markup(_t(
                "Your personal queue. Drag a card to the next stage to move the ticket forward."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- All Service Tickets ---
        {
            trigger: navSection("Sales Services"),
            content: markup(_t("Reopen the <b>Sales Services</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Service Tickets"),
            content: markup(_t(
                "Open <b>Service Tickets</b> — every customer-service ticket handled by the team."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Service Tickets"),
        {
            trigger: ".o-kanban_view, .o_list_renderer",
            content: markup(_t("The whole team queue, grouped by stage.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Log a new ticket ---
        {
            trigger: ".o-kanban-button-new, .o_list_button_add",
            content: markup(_t("Click <b>New</b> to log a customer service request.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("Type the ticket <b>subject</b>.")),
            run: "edit Machine installation follow-up",
        },
        {
            trigger: ".o_field_widget[name='description'] .odoo-editor-editable",
            content: markup(_t(
                "<b>Description</b> is mandatory — add what the customer asked for."
            )),
            tooltipPosition: "bottom",
            run: "editor The customer asks for a follow-up on the machine installation schedule.",
        },
        {
            trigger: ".o_field_widget[name='team_id']",
            content: markup(_t(
                "Check the <b>team</b> so the ticket lands in the right service queue."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='priority']",
            content: markup(_t(
                "Set the <b>priority</b> so urgent requests are handled first."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o-kanban_view, .o_list_renderer",
            content: markup(_t(
                "Sales Services tour complete! Track your own workload from " +
                "<b>My Service Tickets</b> and the whole team from <b>Service Tickets</b>."
            )),
            run: "click",
        },
    ],
});
