import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Document Signing Tour
 *
 * Walks the user through sending a document for electronic signature:
 *  1. Open the Signing app and its Documents list
 *  2. Create a signature request from a template
 *  3. Add the signers (contact + email are mandatory)
 *  4. Send, resend or expire the request
 */
registry.category("web_tour.tours").add("od19_signing_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "od19_document_sign.menu_od19_document_sign_root",
            markup(_t("Let's send a document for <b>electronic signature</b>."))
        ),

        {
            trigger: navSection("Documents"),
            content: markup(_t("Open the <b>Documents</b> list.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Documents"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Every signature request is listed here with its status: " +
                "<b>Draft</b> → <b>Sent</b> → <b>Signed</b>."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to create a signature request.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='template_id']",
            content: markup(_t(
                "Choose the <b>template</b>: it provides the document body and the " +
                "signer roles that must be filled in."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='date_deadline']",
            content: markup(_t(
                "Set a <b>deadline</b> so the request expires automatically if nobody signs."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: "a.nav-link:contains('Signers')",
            content: markup(_t("Open the <b>Signers</b> tab.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='signer_ids']",
            content: markup(_t(
                "Add the <b>signers</b>. A signer without a contact <b>and</b> an " +
                "email address cannot be sent."
            )),
            tooltipPosition: "top",
        },
        {
            trigger: "button[name='action_send']",
            content: markup(_t(
                "Click <b>Send for Signature</b> to email the signing link to the first signer."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Signing workflow complete! Create → pick a template → add signers → " +
                "<b>Send for Signature</b>. Use <b>Resend</b> to remind a signer and " +
                "<b>Mark Expired</b> to close a request."
            )),
            run: "click",
        },
    ],
});
