import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Approval Tour
 *
 * Walks the user through:
 *  1. Creating a Purchase Requisition (PR)
 *  2. Submitting the PR for approval
 *  3. Approving the PR (Purchase Manager)
 *  4. Creating a Purchase Order from the PR
 *  5. Setting project context on PO lines
 *  6. Submitting and approving the PO
 *  7. Budget warnings
 */
registry.category("web_tour.tours").add("od19_purchase_approval_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("Let's learn the <b>Purchase</b> approval workflow: PR → PO → Approval."))
        ),
        // --- Purchase Requisition ---
        {
            trigger: navSection('Orders'),
            content: markup(_t("Open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Purchase Requests'),
            content: markup(_t("Start by creating a <b>Purchase Requisition (PR)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Purchase Requests"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new PR."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_vendor_ref'] input",
            content: _t("Select the vendor."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_priority'] .o_select_menu_toggler",
            content: markup(_t(
                "Set the <b>Priority</b> (Normal, Urgent, Emergency) to flag how quickly " +
                "this purchase request must be handled."
            )),
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:first",
            content: _t("Pick the priority for the requisition."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_x2many_list_row_add a",
            content: _t("Add a product line to the requisition."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o_field_widget[name='product_id'] input",
            content: _t("Pick the product to requisition."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='line_ids'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the product from the suggestion list."),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            // The OCA module `purchase_request_tier_validation` forces the core
            // "Request approval" button (`button_to_approve`) to `invisible="1"`
            // and repurposes `button_approved` as the single "Confirm" button
            // that starts the approval flow. Click whichever one is rendered.
            trigger: "button[name='button_approved'], button[name='button_to_approve']",
            content: markup(_t(
                "Click <b>Confirm</b> to submit the Purchase Requisition for approval. " +
                "<b>Every PR must be approved</b> before it can be used."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // Only rendered when a Tier Validation definition applies to
            // `purchase.request` (the assigned reviewer must clear the review).
            isActive: ["button[name='validate_tier']"],
            trigger: "button[name='validate_tier']",
            content: markup(_t(
                "The assigned reviewer clicks <b>Validate</b> to approve the PR."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        ...stepUtils.discardForm(),

        // --- Purchase Order ---
        {
            trigger: navSection('Orders'),
            content: markup(_t("Open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem('Purchase Orders'),
            content: markup(_t("Now create a <b>Purchase Order (PO)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Purchase Orders"),
        {
            trigger: ".o_list_button_add",
            content: _t("Create a new PO."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] input",
            content: _t("Select the vendor."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='partner_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the vendor from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='order_line'] .o_field_x2many_list_row_add a",
            content: _t("Add a product line to the PO."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='order_line'] .o_field_widget[name='product_id'] input",
            content: _t("Pick the product for the order line."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='order_line'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the product from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_project_id'] input",
            content: markup(_t(
                "On each PO line, set the <b>Project</b> to track costs by Job Number. " +
                "Project context is tracked at the <b>line level</b>."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_procurement_purpose'] .o_select_menu_toggler",
            content: markup(_t(
                "Set the <b>Procurement Purpose</b> on each line (stock, project, service, etc.)."
            )),
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: "button[name='action_od19_submit_for_approval']",
            content: markup(_t(
                "Click <b>Submit for Approval</b>. If the order exceeds the budget, " +
                "a <b>warning</b> will be shown (no hard block)."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "button[name='action_od19_approve']",
            content: markup(_t(
                "The Purchase Manager approves the PO. Note that goods receipt (for products) " +
                "and service acceptance are managed separately."
            )),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Purchase workflow complete! Remember: <b>every PR and PO requires approval</b>, " +
                "project context is set at the <b>PO line level</b>, and budget control uses " +
                "<b>warnings only</b> (no hard blocks)."
            )),
            run: "click",
        },
    ],
});
