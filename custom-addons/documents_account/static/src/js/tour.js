/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";


registry.category("web_tour.tours").add('documents_account_tour', {
    url: "/web",
    rainbowManMessage: () => markup(_t("Wow... 6 documents processed in a few seconds, You're good.<br/>The tour is complete. Try uploading your own documents now.")),
    sequence: 170,
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
    content: markup(_t("Want to become a <b>paperless company</b>? Let's discover Odoo Documents.")),
    position: 'bottom',
}, {
    trigger: 'body:not(:has(.o-FileViewer)) img[src="https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg"]',
    content: markup(_t("Click on a thumbnail to <b>preview the document</b>.")),
    position: 'bottom',
}, {
    trigger: '[title="Close (Esc)"]',
    extra_trigger: '.o_documents_kanban',
    content: markup(_t("Click the cross to <b>exit preview</b>.")),
    position: 'left',
}, { // equivalent to '.o_search_panel_filter_value:contains('Inbox')' but language agnostic.
    trigger: '.o_search_panel_filter_value:eq(0)',
    extra_trigger: '.o_search_panel_label',
    content: markup(_t("Let's process documents in your Inbox.<br/><i>Tip: Use Tags to filter documents and structure your process.</i>")),
    position: 'bottom',
    run: function (actions) {
        $('.o_search_panel_filter_value:eq(0) .o_search_panel_label_title').click();
    },
}, {
    trigger: '.o_kanban_record:contains(mail.png)',
    extra_trigger: 'body:not(:has(.o-FileViewer)) .o_documents_kanban',
    content: markup(_t("Click on a card to <b>select the document</b>.")),
    position: 'bottom',
}, { // equivalent to '.o_inspector_rule:contains('Send to Legal') .o_inspector_trigger_rule' but language agnostic.
    trigger: '.o_inspector_rule[data-id="3"] .o_inspector_trigger_rule',
    content: markup(_t("Let's tag this mail as legal<br/> <i>Tips: actions can be tailored to your process, according to the workspace.</i>")),
    position: 'bottom',
}, { // the nth(0) ensures that the filter of the preceding step has been applied.
    trigger: '.o_kanban_record:nth(0):contains(Mails_inbox.pdf)',
    extra_trigger: '.o_documents_kanban',
    content: _t("Let's process this document, coming from our scanner."),
    position: 'bottom',
}, {
    trigger: '.o_inspector_split',
    extra_trigger: '[title="Mails_inbox.pdf"]',
    content: _t("As this PDF contains multiple documents, let's split and process in bulk."),
    position: 'bottom',
}, {
    trigger: '.o_page_splitter_wrapper:nth(3)',
    extra_trigger: '.o_documents_pdf_canvas:nth(5)', // Makes sure that all the canvas are loaded.
    content: markup(_t("Click on the <b>page separator</b>: we don't want to split these two pages as they belong to the same document.")),
    position: 'right',
}, {
    trigger: '.o_documents_pdf_page_selector:nth(5)',
    extra_trigger: '.o_documents_pdf_manager',
    content: markup(_t("<b>Deselect this page</b> as we plan to process all bills first.")),
    position: 'left',
}, { // equivalent to '.o_pdf_manager_button:contains(Create Vendor Bill)' but language agnostic.
    trigger: '.o_pdf_manager_button:nth-last-child(2)',
    extra_trigger: '.o_documents_pdf_manager',
    content: _t("Let's process these bills: turn them into vendor bills."),
    position: 'bottom',
}, {
    trigger: '.o_documents_pdf_page_selector',
    extra_trigger: '.o_documents_pdf_manager',
    content: markup(_t("<b>Select</b> this page to continue.")),
    position: 'bottom',
}, { // equivalent to '.o_pdf_manager_button:contains(Send to Legal)' but language agnostic.
    trigger: '.o_pdf_manager_button:nth-child(4)',
    extra_trigger: '.o_pdf_manager_button:not(:disabled)',
    content: _t("Send this letter to the legal department, by assigning the right tags."),
    position: 'bottom',
}]});
