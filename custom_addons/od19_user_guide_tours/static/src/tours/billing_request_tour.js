import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Billing Request Tour
 *
 * Walks the user through the central AR/AP billing request application
 * (od19_billing_request — "Billing Requests / คำขอเปิดบิล"):
 *  1. Open the "Billing Requests" app (All Requests register)
 *  2. Raise a request and review the header, the Lines / Evidence tabs and the actions
 *  3. Follow it in the Billing Queue where Accounting raises the invoice / vendor bill
 *
 * The Billing Queue is restricted to the accounting role, so its steps are
 * guarded with `isActive` and are simply skipped for a requester-only user.
 */
registry.category("web_tour.tours").add("od19_billing_request_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_billing_request.menu_od19_billing_request_root",
            markup(_t("Let's raise a central <b>billing request</b> (AR / AP)."))
        ),

        // --- All Requests register ---
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Every row of <b>All Requests</b> is one billing request: its <b>direction</b> " +
                "(AR = customer invoice, AP = vendor bill), the <b>customer / vendor</b>, who " +
                "<b>requested</b> it, the <b>source document</b> and the <b>status</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to raise a billing request.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='direction']",
            content: markup(_t(
                "Choose the <b>direction</b>: <b>AR</b> bills a customer, <b>AP</b> records a " +
                "vendor bill. The AP-only <b>AP Original</b> tab appears accordingly, and the " +
                "statusbar runs <b>Draft → Submitted → Invoiced</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id']",
            content: markup(_t(
                "Pick the <b>customer or vendor</b>, set the <b>department</b>, and — when the " +
                "request comes from another document — link the <b>source document</b> so its " +
                "lines can be pulled in."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "<b>Pull Lines</b> imports the lines of the source document (use <b>Manage " +
                "Source</b> to detach them again), the <b>Evidence</b> tab holds the supporting " +
                "documents, then press <b>Submit</b> to send the request to Accounting."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Billing Queue (accounting role only) ---
        {
            isActive: [navSection("Billing Queue / คิวรอออกบิล")],
            trigger: navSection("Billing Queue / คิวรอออกบิล"),
            content: markup(_t(
                "Open the <b>Billing Queue</b>: the requests already submitted and waiting for " +
                "Accounting to raise the invoice or vendor bill."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            ...waitForAction("Billing Queue / คิวรอออกบิล"),
            isActive: [navSection("Billing Queue / คิวรอออกบิล")],
        },
        {
            isActive: [navSection("Billing Queue / คิวรอออกบิล")],
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Accounting reviews each request and clicks <b>Create Invoice/Bill</b> — or " +
                "<b>Reject</b> with a reason. Once invoiced, the request links to the generated " +
                "accounting document."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },

        {
            trigger: ".o_list_renderer, .o_kanban_view, .o_form_view",
            content: markup(_t(
                "Billing Request tour complete! Requester: <b>New → Pull Lines → Submit</b>. " +
                "Accounting: <b>Billing Queue → Create Invoice/Bill → Reject or post</b>."
            )),
            run: "click",
        },
    ],
});
