/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("documents_account_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            content: markup(_t("Want to become a <b>paperless company</b>? Let's discover Odoo Documents.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_search_panel_label_title:contains('" + _t("All") + "')",
            content: "Go to the 'All' folder special folder",
            run: "click",
        },
        {
            trigger: "span.o_documents_in_folder",
        },
        {
            trigger: 'body:not(:has(.o-FileViewer)) img[src="https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg"]',
            content: markup(_t("Click on a thumbnail to <b>preview the document</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_documents_kanban",
        },
        {
            trigger: "div[title='" + _t("Close (Esc)") + "']",
            content: markup(_t("Click the cross to <b>exit preview</b>.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o-FileViewer)) .o_documents_kanban",
        },
        {
            trigger: ".o_kanban_record:contains('Mails_inbox.pdf')",
            content: markup(_t("Click on a card to <b>select the document</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_control_panel_actions button:contains('" + _t("Send To Finance") + "')",
            content: markup(
                _t(
                    "Let's tag this mail as Finance<br/> <i>Tips: actions can be tailored to your process, according to the folder.</i>"
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_documents_kanban",
        },
        {
            trigger: ".o_kanban_record:contains('" + _t("Finance") + "')",
            content: markup(
                _t(
                    "Let's process documents in this folder.<br/> <i>Tip: Use Tags to filter documents and structure your process.</i>"
                )
            ),
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_documents_in_folder)) .o_documents_kanban",
        },
        {
            trigger: ".o_kanban_record:contains('Mails_inbox.pdf')",
            content: _t("Let's process this document now."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_documents_action_dropdown button:contains(" + _t("Action") + "')",
            content: _t("Open the actions menu"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_documents_action_dropdown button.dropdown-item:contains('" + _t("Split PDF") + "')",
            content: _t("As this PDF contains multiple documents, let's split and process in bulk."),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: '.o_page_splitter_wrapper:eq(3)',
            content: markup(
                _t(
                    "Click on the <b>page separator</b>: we don't want to split these two pages as they belong to the same document."
                )
            ),
            tooltipPosition: "right",
            run: "click",
        },
        {
            trigger: '.o_documents_pdf_page_selector:eq(5)',
            content: markup(_t("<b>Deselect this page</b> as we plan to process all bills first.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ".o_pdf_manager_button:contains('" + _t("Create Vendor Bill") + "')",
            content: _t("Let's process these bills: turn them into vendor bills."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: '.o_documents_pdf_page_selector',
            content: markup(_t("<b>Select</b> this page to continue.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_pdf_manager_button:contains('" + _t("Create Misc Entry") + "')",
            content: _t("This should be processed as a misc entry."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_documents_pdf_manager",
        },
        {
            trigger: ".o_documents_pdf_page_selector",
            content: markup(_t("<b>Select</b> this page to continue.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_pdf_manager_button:not(:disabled)",
        },
        {
            trigger: ".btn-primary.o_pdf_manager_button:contains('Split')",
            content: _t("Create a new document for the remaining page, it will be handled later."),
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});
