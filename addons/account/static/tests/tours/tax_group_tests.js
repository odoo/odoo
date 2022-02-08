/** @odoo-module alias=account.tax.group.tour.tests */
"use strict";

import tour from 'web_tour.tour';

tour.register('account_tax_group', {
    test: true,
    url: "/web",
}, [tour.stepUtils.showAppsMenuItem(),
    {
        content: "Go to Invoicing",
        trigger: '.o_app[data-menu-xmlid="account.menu_finance"]',
        edition: 'community',
    },
    {
        content: "Go to Accounting",
        trigger: '.o_app[data-menu-xmlid="account_accountant.menu_accounting"]',
        edition: 'enterprise',
    },
    {
        content: "Go to Vendors",
        trigger: 'a:contains("Vendors")',
    },
    {
        content: "Go to Bills",
        trigger: 'span:contains("Bills")',
    },
    {
        extra_trigger: '.breadcrumb:contains("Bills")',
        content: "Create new bill",
        trigger: '.o_list_button_add',
    },
    // Set a vendor
    {
        content: "Add vendor",
        trigger: 'div.o_field_widget.o_field_many2one[name="partner_id"] div input',
        run: 'text Azure Interior',
    },
    {
        content: "Valid vendor",
        trigger: '.ui-menu-item a:contains("Azure Interior")',
    },
    // Add First product
    {
        content: "Add items",
        trigger: 'div[name="invoice_line_ids"] .o_field_x2many_list_row_add a:contains("Add a line")',
    },
    {
        content: "Select input",
        trigger: 'div[name="invoice_line_ids"] .o_list_view .o_selected_row .o_list_many2one:first input',
    },
    {
        content: "Type item",
        trigger: 'div[name="invoice_line_ids"] .o_list_view .o_selected_row .o_list_many2one:first input',
        run: "text Large Desk",
    },
    {
        content: "Valid item",
        trigger: '.ui-menu-item-wrapper:contains("Large Desk")',
    },
    // Save account.move
    {
        content: "Save the account move",
        trigger: '.o_form_button_save',
    },
    // Edit account.move
    {
        content: "Edit the account move",
        trigger: '.o_form_button_edit',
    },
    // Edit tax group amount
    {
        content: "Edit tax group amount",
        trigger: '.o_tax_group_edit',
    },
    {
        content: "Modify the input value",
        trigger: '.o_tax_group_edit_input input',
        run: function (actions) {
            $('.o_tax_group_edit_input input').val(200);
            $('.o_tax_group_edit_input input').select();
            $('.o_tax_group_edit_input input').blur();
        },
    },
    // Check new value for total (with modified tax_group_amount).
    {
        content: "Valid total amount",
        trigger: 'span[name="amount_total"]:contains("1,499.00")',
    },
    // Modify the quantity of the object
    {
        content: "Select item quantity",
        trigger: 'div[name="invoice_line_ids"] .o_list_view tbody tr.o_data_row .o_list_number[title="1.00"]',
    },
    {
        content: "Change item quantity",
        trigger: 'div[name="invoice_line_ids"] .o_list_view tbody tr.o_data_row .o_list_number[title="1.00"] input',
        run: 'text 2',
    },
    {
        content: "Valid the new value",
        trigger: 'div[name="invoice_line_ids"] .o_list_view tbody tr.o_data_row .o_list_number[title="1.00"] input',
        run: function (actions) {
            let keydownEvent = jQuery.Event('keydown');
            keydownEvent.which = 13;
            this.$anchor.trigger(keydownEvent);
        },
    },
    // Save form
    {
        content: "Save the account move",
        trigger: '.o_form_button_save',
    },
    // Check new tax group value
    {
        content: "Check new value of tax group",
        trigger: '.o_tax_group_amount_value:contains("389.70")',
    },
]);
