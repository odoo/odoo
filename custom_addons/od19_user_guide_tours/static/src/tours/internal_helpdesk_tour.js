import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Internal Helpdesk Tour
 *
 * Walks the user through the internal IT helpdesk. The internal queues are a
 * section of the single OCA Helpdesk application, so the tour opens it there:
 *  1. Open the Helpdesk app
 *  2. Open the "Internal Helpdesk" section and browse the internal tickets
 *  3. Create a ticket (subject, team, priority)
 *  4. Assign the ticket to yourself
 *  5. Switch to the "My Internal Tickets" personal queue
 */
registry.category("web_tour.tours").add("od19_internal_helpdesk_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "helpdesk_mgmt.helpdesk_ticket_main_menu",
            markup(_t("Let's handle an <b>Internal Helpdesk</b> ticket."))
        ),

        {
            trigger: navSection("Internal Helpdesk"),
            content: markup(_t("Open the <b>Internal Helpdesk</b> section of the Helpdesk app.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Internal Tickets"),
            content: markup(_t("Open the <b>Internal Tickets</b> list of the internal IT team.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Internal Tickets"),
        {
            trigger: ".o_kanban_view",
            content: markup(_t(
                "Tickets are grouped by <b>stage</b>. Drag a card to the next stage " +
                "to move a ticket forward."
            )),
        },
        {
            trigger: ".o-kanban-button-new",
            content: markup(_t("Click <b>New</b> to report an incident.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("Describe the problem: <b>subject</b> of the ticket.")),
            run: "edit Printer on the 3rd floor is not responding",
        },
        {
            trigger: ".o_field_widget[name='description'] .odoo-editor-editable",
            content: markup(_t(
                "<b>Description</b> is mandatory — add the details of the incident."
            )),
            tooltipPosition: "bottom",
            run: "editor The printer on the 3rd floor does not respond when printing from the ERP.",
        },
        {
            trigger: ".o_field_widget[name='team_id']",
            content: markup(_t(
                "Check the <b>team</b>. Internal tickets always go to the internal IT team."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='priority']",
            content: markup(_t(
                "Set the <b>priority</b> so urgent incidents are handled first."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.saveForm(),
        {
            isActive: ["button[name='assign_to_me']:visible"],
            trigger: "button[name='assign_to_me']:visible",
            content: markup(_t("Click <b>Assign to me</b> to take ownership of the ticket.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: navSection("Internal Helpdesk"),
            content: markup(_t("Reopen the <b>Internal Helpdesk</b> section.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("My Internal Tickets"),
            content: markup(_t("Open <b>My Internal Tickets</b> — your personal queue.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("My Internal Tickets"),

        {
            trigger: ".o_kanban_view, .o_list_renderer",
            content: markup(_t(
                "Internal Helpdesk complete! Report a ticket → set team &amp; priority → " +
                "<b>Assign to me</b>. Follow your own workload from <b>My Internal Tickets</b>."
            )),
            run: "click",
        },
    ],
});
