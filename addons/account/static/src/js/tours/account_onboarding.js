import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("account_tour_onboarding", {
    steps: () => [
    ...accountTourSteps.goToAccountMenu(markup(_t('Send invoices to your customers in no time with the <b>Invoicing app</b>.'))),
    ...accountTourSteps.onboarding(),
    ...accountTourSteps.newInvoice(),
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=partner_id] .o_input_dropdown`,
        content: markup(_t("Write a customer name to <b>create one</b> or <b>see suggestions</b>.")),
        tooltipPosition: "right",
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=partner_id] input`,
        run: "edit Test Customer",
    },
    {
        trigger: `body${accountTourSteps.draftInvoiceSelector} .o_m2o_dropdown_option a:contains('Create')`,
        content: _t("Select first partner"),
        run: "click",
    },
    {
        trigger: `body${accountTourSteps.draftInvoiceSelector} .modal-content button.btn-primary`,
        content: markup(_t("Once everything is set, you are good to continue. You will be able to edit this later in the <b>Customers</b> menu.")),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] .o_field_x2many_list_row_add button`,
        content: _t("Add a line to your invoice"),
        run: "click",
    },
    {
        isActive: ["desktop"],
        trigger: ".o_optional_columns_dropdown_toggle",
        content: _t("Open the list of optional columns."),
        run: "click",
    },
    {
        isActive: ["desktop"],
        trigger: `.o-dropdown-item input[name="product_id"]`,
        content: _t("Show the product column."),
        run: "click",
    },
    {
        isActive: ["desktop"],
        trigger: ".o_optional_columns_dropdown_toggle",
        content: _t("Close the list of optional columns."),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=product_id]`,
        content: _t("Fill in the details of the product or see the suggestion."),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] div[name=name] textarea`,
        content: _t("Add a description to your item."),
        run: "edit A very useful description.",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} div[name=invoice_line_ids] td[name=price_unit]`,
        content: _t("Verify the price and update if necessary."),
        run: "click",
    },
    ...stepUtils.saveForm(),
    {
        trigger: `.o_form_view_container${accountTourSteps.draftInvoiceSelector} button[name=action_post]`,
        content: _t("Once your invoice is ready, confirm it."),
        run: "click",
    },
    {
        trigger: `.o_form_view_container${accountTourSteps.postedInvoiceSelector} button[name=action_invoice_sent]:contains(send)`,
        content: _t("Send the invoice to the customer and check what he'll receive."),
        run: "click",
    },
    {
        trigger: "button[name=document_layout_save]",
        content: _t("Continue with the default document layout."),
        run: "click",
    },
    {
        // RecipientsInputTagsListPopover will not display if the customer already has an email address
        // unless it's possible to have optional steps, we will only use it for tests at the moment.
        trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover input`,
        content: markup(_t("Write here <b>your own email address</b> to test the flow.")),
        run: "edit customer@example.com",
    },
    {
        trigger: `body${accountTourSteps.postedInvoiceSelector} .o-mail-RecipientsInputTagsListPopover .btn-primary`,
        content: _t("Validate."),
        run: "click",
    },
    {
        trigger: `body${accountTourSteps.postedInvoiceSelector} .modal button[name=action_send_and_print]`,
        content: _t("Let's send the invoice."),
        tooltipPosition: "top",
        run: "click",
    },
    ...accountTourSteps.endSteps(),
]});
