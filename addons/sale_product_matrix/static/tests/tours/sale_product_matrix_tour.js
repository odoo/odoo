odoo.define('sale_product_matrix.sale_matrix_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');
let EXPECTED = [
    "Matrix", "PAV11", "PAV12 + $ 50.00",
]
for (let no of ['PAV41', 'PAV42']) {
    for (let dyn of ['PAV31', 'PAV32']) {
        for (let al of ['PAV21', 'PAV22']) {
            let row_label = [al, dyn, no].join(' • ');
            if (dyn === 'PAV31') {
                row_label += ' - $ 25.00';
            }
            EXPECTED.push(row_label, "", "");
        }
    }
}

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
    extra_trigger: '.oe_subtotal_footer_separator:contains("248.40")',
}, {
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\n\nPA4: PAV41")',
    extra_trigger: '.o_form_editable',
}, {
    trigger: '.o_edit_product_configuration',  // edit the matrix
}, {
    trigger: '.o_product_variant_matrix',
    run: function () {
        // whitespace normalization: removes newlines around text from markup
        // content, then collapse & convert internal whitespace to regular
        // spaces.
        const texts = $('.o_matrix_input_table').find('th, td')
            .map((_, el) => el.innerText.trim().replace(/\s+/g, ' '))
            .get();

        for (let i=0; i<EXPECTED.length; ++i) {
            if (EXPECTED[i] !== texts[i]) {
                throw new Error(`${EXPECTED[i]} != ${texts[i]}`)
            }
        }
        // set all qties to 3
        $('.o_matrix_input').val(3);
    }
}, {
    trigger: 'span:contains("Confirm")',  // apply the matrix
}, {
    trigger: '.o_sale_order',
    // wait for qty to be changed => check the total to be sure all qties are set to 3
    extra_trigger: '.oe_subtotal_footer_separator:contains("745.20")',
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
    extra_trigger: '.oe_subtotal_footer_separator:contains("248.40")',
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
    extra_trigger: '.oe_subtotal_footer_separator:contains("621.00")',
}, {
    trigger: '.o_form_button_save:contains("Save")',
}, {
    trigger: '.o_form_button_edit:contains("Edit")',  // Edit Sales Order.
},
// Ensures the matrix is opened with the values, when adding the same product.
{
    trigger: "a:contains('Add a product')",
    extra_trigger: '.o_form_editable',
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
    extra_trigger: '.oe_subtotal_footer_separator:contains("640.32")',
}, {
    trigger: '.o_form_button_save:contains("Save")',
}, {
    trigger: '.o_form_button_edit:contains("Edit")',
    run: function () {},  // Ensure the form is saved before closing the browser
},
]);


});
