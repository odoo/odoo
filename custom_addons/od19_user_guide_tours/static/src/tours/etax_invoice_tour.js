import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 e-Tax Invoice Tour (ขมธอ.3-2560)
 *
 * Walks the user through the Thai e-Tax invoicing module that lives inside
 * the Accounting application:
 *  1. Open the e-Tax Invoice section
 *  2. Browse the e-Tax documents list
 *  3. Create an e-Tax document from a posted customer invoice
 *  4. Review the signing certificates
 */
registry.category("web_tour.tours").add("od19_etax_invoice_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's issue an <b>e-Tax Invoice</b> (ขมธอ.3-2560)."))
        ),

        {
            trigger: navSection("e-Tax Invoice"),
            content: markup(_t("Open the <b>e-Tax Invoice</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("e-Tax Documents"),
            content: markup(_t("Open <b>e-Tax Documents</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("e-Tax Documents"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "An e-Tax document is the legal, signed XML representation of a " +
                "posted customer invoice. The status goes <b>Draft</b> → " +
                "<b>Generated</b> → <b>Signed</b>."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to prepare an e-Tax document.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t(
                "Enter the <b>document reference</b> reported in the XML " +
                "(maximum 35 characters)."
            )),
            run: "edit INV/2026/00001",
        },
        {
            trigger: ".o_field_widget[name='document_type']",
            content: markup(_t(
                "Choose the <b>document type</b>: tax invoice, e-receipt (ใบเสร็จรับเงิน) " +
                "or one of the debit / credit notes."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='move_id']",
            content: markup(_t(
                "Link the <b>journal entry</b> (posted customer invoice). Its lines and " +
                "taxes are what the e-Tax XML is built from."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Then use the header buttons: <b>Generate XML</b> builds the file against " +
                "the official ETDA schema, <b>Sign</b> applies the XAdES-BES signature and " +
                "<b>Generate PDF</b> produces the printable version. Once signed, " +
                "<b>Submit to RD</b> sends it to the Revenue Department."
            )),
            tooltipPosition: "bottom",
        },
        {
            isActive: [".o_control_panel .o_form_button_cancel:visible"],
            trigger: ".o_control_panel .o_form_button_cancel:visible",
            content: _t("Discard the draft document."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: [".o_control_panel .o_back_button:visible"],
            trigger: ".o_control_panel .o_back_button:visible",
            content: _t("Go back to the list."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_view, .o_kanban_view",
        },

        // --- Signing certificates ---
        {
            trigger: navSection("e-Tax Invoice"),
            content: markup(_t("Reopen the <b>e-Tax Invoice</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Signing Certificates"),
            content: markup(_t(
                "Open <b>Signing Certificates</b> to see the certificates used to sign " +
                "the documents. A certificate can also be set on the company as the default."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_renderer, .o_form_view, .o_kanban_view",
        },

        {
            trigger: ".o_list_renderer, .o_kanban_view, .o_form_view",
            content: markup(_t(
                "e-Tax complete! Prepare the document from a posted invoice → " +
                "<b>Generate XML</b> → <b>Sign</b> → <b>Generate PDF</b> → " +
                "<b>Submit to RD</b>. Track the filings from <b>RD Submissions</b>."
            )),
            run: "click",
        },
    ],
});
