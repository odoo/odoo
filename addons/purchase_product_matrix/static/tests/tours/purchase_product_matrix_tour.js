odoo.define('purchase_product_matrix.purchase_matrix_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('purchase_matrix_tour', {
    url: "/web",
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="purchase.menu_purchase_root"]',
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_purchase_order"
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Agrolait',
}, {
    trigger: '.ui-menu-item > a:contains("Agrolait")',
    auto: true,
}, {
    trigger: "a:contains('Add a product')"
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "text Matrix",
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
    run: 'click'
}, {
    trigger: '.o_form_button_save',
    run: 'click' // SAVE Sales Order.
},
// Open the matrix through the pencil button next to the product in line edit mode.
{
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\nPA4: PAV41")',
    extra_trigger: '.o_form_status_indicator_buttons.invisible', // wait for save to be finished
}, {
    trigger: '[name=product_template_id] button.fa-pencil', // edit the matrix
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        // update some of the matrix values.
        $('.o_matrix_input').slice(8, 16).val(4);
    } // set the qty to 4 for half of the matrix products.
}, {
    trigger: 'span:contains("Confirm")',
    run: 'click' // apply the matrix
}, {
    trigger: '.o_form_button_save',
    extra_trigger: '.o_field_cell.o_data_cell.o_list_number:contains("4.00")',
    run: 'click' // SAVE Sales Order, after matrix has been applied (extra_trigger).
},
// Ensures the matrix is opened with the values, when adding the same product.
{
    trigger: 'a:contains("Add a product")',
    extra_trigger: '.o_form_status_indicator_buttons.invisible',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Matrix',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Matrix")',
}, {
    trigger: 'input[value="4"]',
    run: function () {
        // update some values of the matrix
        $("input[value='4']").slice(0, 4).val(8.2);
    }
}, {
    trigger: 'span:contains("Confirm")',
    run: 'click' // apply the matrix
}, ...tour.stepUtils.saveForm({ extra_trigger: '.o_field_cell.o_data_cell.o_list_number:contains("8.20")' })
]);


});
