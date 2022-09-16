odoo.define('sale_product_matrix.sale_matrix_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_matrix_tour', {
    url: "/web",
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order"
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Agrolait',
}, {
    trigger: '.ui-menu-item > a:contains("Agrolait")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")',
}, {
    trigger: '.o_data_cell',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Matrix',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Matrix")',
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        // fill the whole matrix with 1's
        $('.o_matrix_input').val(1);
    }
}, {
    trigger: 'span:contains("Confirm")',
}, {
    trigger: '.o_sale_order',
    // wait for qty to be 1 => check the total to be sure all qties are set to 1
    extra_trigger: '.oe_subtotal_footer_separator:contains("18.40")',
}, {
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\n\nPA4: PAV41")',
    extra_trigger: '.o_form_editable',
}, {
    trigger: '.o_edit_product_configuration',  // edit the matrix
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        // set all qties to 3
        $('.o_matrix_input').val(3);
    }
}, {
    trigger: 'span:contains("Confirm")',  // apply the matrix
}, {
    trigger: '.o_sale_order',
    // wait for qty to be changed => check the total to be sure all qties are set to 3
    extra_trigger: '.oe_subtotal_footer_separator:contains("55.20")',
}, {
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\n\nPA4: PAV41")',
    extra_trigger: '.o_form_editable',
}, {
    trigger: '.o_edit_product_configuration',
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        // reset all qties to 1
        $('.o_matrix_input').val(1);
    }
}, {
    trigger: 'span:contains("Confirm")',
}, {
    trigger: '.o_sale_order',
    // wait for qty to be 1 => check the total to be sure all qties are reset to 1
    extra_trigger: '.oe_subtotal_footer_separator:contains("18.40")',
}, {
    trigger: '.o_form_button_save:contains("Save")',  // SAVE Sales Order.
},
// Open the matrix through the pencil button next to the product in line edit mode.
{
    trigger: '.o_form_button_edit:contains("Edit")',   // Edit Sales Order.
}, {
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\n\nPA4: PAV41")',
    extra_trigger: '.o_form_editable',
}, {
    trigger: '.o_edit_product_configuration',  // edit the matrix
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        // update some of the matrix values.
        $('.o_matrix_input').slice(8, 16).val(4);
    } // set the qty to 4 for half of the matrix products.
}, {
    trigger: 'span:contains("Confirm")',  // apply the matrix
}, {
    trigger: '.o_sale_order',
    // wait for qty to be changed => check the total to be sure all qties are set to either 1 or 4
    extra_trigger: '.oe_subtotal_footer_separator:contains("46.00")',
}, {
    trigger: '.o_form_button_save:contains("Save")',
}, {
    trigger: '.o_form_button_edit:contains("Edit")',  // Edit Sales Order.
},
// Ensures the matrix is opened with the values, when adding the same product.
{
    trigger: "a:contains('Add a product')"
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Matrix'
}, {
    trigger: 'ul.ui-autocomplete a:contains("Matrix")',
}, {
    trigger: "input[value='4']",
    run: function () {
        // update some values of the matrix
        $("input[value='4']").slice(0, 4).val(8.2);
    }
}, {
    trigger: 'span:contains("Confirm")',
}, {
    trigger: '.o_sale_order',
    // wait for qty to be changed => check the total to be sure all qties are set
    extra_trigger: '.oe_subtotal_footer_separator:contains("65.32")',
}, {
    trigger: '.o_form_button_save:contains("Save")',
},
]);


});
