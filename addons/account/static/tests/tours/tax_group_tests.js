import { accountTourSteps } from "@account/js/tours/account";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('account_tax_group', {
    url: "/odoo",
    steps: () => [
    ...accountTourSteps.goToAccountMenu("Go to Invoicing"),
    {
        content: "Go to Vendors",
        trigger: 'span:contains("Vendors")',
        run: "click",
    },
    {
        content: "Go to Bills",
        trigger: 'a:contains("Bills")',
        run: "click",
    },
    {
        trigger: ".o_breadcrumb .text-truncate:contains(Bills)",
    },
    {
        content: "Create new bill",
        trigger: '.o_control_panel_main_buttons .o_list_button_add',
        run: "click",
    },
    // Set a vendor
    {
        content: "Add vendor",
        trigger: 'div.o_field_widget.o_field_res_partner_many2one[name="partner_id"] div input',
        run: "edit Account Tax Group Partner",
    },
    {
        content: "Valid vendor",
        trigger: '.ui-menu-item a:contains("Account Tax Group Partner")',
        run: "click",
    },
    // Show product column
    {
        content: "Open line fields list",
        trigger: ".o_optional_columns_dropdown_toggle",
        run: "click"
    },
    {
        content: "Show product column",
        trigger: '.o-dropdown-item input[name="product_id"]',
        run: "click"
    },
    {
        content: "Close line fields list",
        trigger: ".o_optional_columns_dropdown_toggle",
        run: "click"
    },
    // Add First product
    {
        content: "Add items",
        trigger: 'div[name="invoice_line_ids"] .o_field_x2many_list_row_add a:contains("Add a line")',
        run: "click",
    },
    {
        content: "Select input",
        trigger: 'div[name="invoice_line_ids"] .o_selected_row .o_list_many2one[name="product_id"] input',
        run: "edit Account Tax Group Product",
    },
    {
        content: "Valid item",
        trigger: '.ui-menu-item-wrapper:contains("Account Tax Group Product")',
        run: "click",
    },
    // Save account.move
    ...stepUtils.saveForm(),
    // Edit tax group amount
    {
        content: "Edit tax group amount",
        trigger: '.o_tax_group_edit',
        run: "click",
    },
    {
        content: "Modify the input value",
        trigger: '.o_tax_group_edit_input input',
        run() {
            this.anchor.value = 200;
            this.anchor.select();
            this.anchor.blur();
        },
    },
    // Check new value for total (with modified tax_group_amount).
    {
        content: "Valid total amount",
        trigger: 'span[name="amount_total"]:contains("800")',
        run: "click",
    },
    // Modify the quantity of the object
    {
        content: "Select item quantity",
        trigger: 'div[name="invoice_line_ids"] tbody tr.o_data_row .o_list_number[name="quantity"]',
        run: "click",
    },
    {
        content: "Change item quantity",
        trigger: 'div[name="invoice_line_ids"] tbody tr.o_data_row .o_list_number[name="quantity"] input',
        run: "edit 2",
    },
    {
        content: "Valid the new value",
        trigger: 'div[name="invoice_line_ids"] tbody tr.o_data_row .o_list_number[name="quantity"] input',
        run: "press Enter",
    },
    // Check new tax group value
    {
        content: "Check new value of tax group",
        trigger: '.o_tax_group_amount_value:contains("120")',
        run: "click",
    },
    // Save form
    ...stepUtils.saveForm(),
    // Check new tax group value
    {
        content: "Check new value of tax group",
        trigger: '.o_tax_group_amount_value:contains("120")',
        run: "click",
    },
    {
        content: "Edit tax value",
        trigger: '.o_tax_group_edit_input input',
        run: "edit 2 && click body",
    },
    {
        content: "Check new value of total",
        trigger: '.oe_subtotal_footer_separator:contains("1,202")',
        run: "click",
    },
    {
        content: "Discard changes",
        trigger: '.o_form_button_cancel',
        run: "click",
    },
    {
        content: "Check tax value is reset",
        trigger: '.o_tax_group_amount_value:contains("120")',
    },
]});
