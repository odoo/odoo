/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

let EXPECTED = [
    "Matrix", "PAV11", "PAV12 + $ 50.00",
];
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

registry.category("web_tour.tours").add('sale_matrix_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    run: "click",
}, 
{
    trigger: ".o_sale_order",
},
{
    trigger: '.o_list_button_add',
    run: "click",
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: "edit Agrolait",
}, {
    isActive: ["auto"],
    trigger: '.ui-menu-item > a:contains("Agrolait")',
    run: "click",
}, {
    trigger: 'a:contains("Add a product")',
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "edit Matrix",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Matrix")',
    run: "click",
}, {
    trigger: ".modal .o_matrix_input_table",
    in_modal: false,
    run: function () {
        // fill the whole matrix with 1's
        [...document.querySelectorAll(".o_matrix_input")].forEach((el) => (el.value = 1));
    }
}, {
    trigger: ".modal button:contains(Confirm)",
    in_modal: false,
    run: "click",
}, 
{
    trigger: 'td.o_list_monetary > span[name="Untaxed Amount"]:contains("216.00")',
},
{
    trigger: '.o_sale_order',
    // wait for qty to be 1 => check the total to be sure all qties are set to 1
    run: "click",
}, 
{
    trigger: ".o_form_editable",
},
{
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\nPA4: PAV41")',
    run: "click",
}, {
    trigger: '[name=product_template_id] button.fa-pencil',  // edit the matrix
    run: "click",
}, {
    trigger: ".modal .o_matrix_input_table",
    in_modal: false,
    run: function () {
        // whitespace normalization: removes newlines around text from markup
        // content, then collapse & convert internal whitespace to regular
        // spaces.
        const tds = [...this.anchor.querySelectorAll('th, td')];
        const texts = tds.map((el) => el.innerText.trim().replace(/\s+/g, ' '))

        for (let i=0; i<EXPECTED.length; ++i) {
            if (EXPECTED[i] !== texts[i]) {
                throw new Error(`${EXPECTED[i]} != ${texts[i]}`)
            }
        }
        // set all qties to 3
        [...document.querySelectorAll(".o_matrix_input")].forEach((el) => (el.value = 3));
    }
}, {
    trigger: ".modal button:contains(Confirm)", // apply the matrix
    in_modal: false,
    run: "click",
}, 
{
    trigger: 'td.o_list_monetary > span[name="Untaxed Amount"]:contains("648.00")',
},
{
    trigger: '.o_sale_order',
    // wait for qty to be 3 => check the total to be sure all qties are set to 3
    run: "click",
}, 
{
    trigger: ".o_form_editable",
},
{
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\nPA4: PAV41")',
    run: "click",
}, {
    trigger: '[name=product_template_id] button.fa-pencil',  // edit the matrix
    run: "click",
}, {
    trigger: ".modal .o_matrix_input_table",
    in_modal: false,
    run: function () {
        // reset all qties to 1
        [...document.querySelectorAll(".o_matrix_input")].forEach((el) => (el.value = 1));
    }
}, {
    trigger: ".modal button:contains(Confirm)", // apply the matrix
    in_modal: false,
    run: "click",
}, 
{
    trigger: 'td.o_list_monetary > span[name="Untaxed Amount"]:contains("216.00")',
},
{
    trigger: '.o_sale_order',
    // wait for qty to be 1 => check the total to be sure all qties are set to 1
    run: "click",
}, {
    trigger: '.o_form_button_save',  // SAVE Sales Order.
    run: "click",
},
// Open the matrix through the pencil button next to the product in line edit mode.
{
    trigger: ".o_form_status_indicator_buttons.invisible", // wait for save to be finished
},
{
    trigger: 'span:contains("Matrix (PAV11, PAV22, PAV31)\nPA4: PAV41")',
    run: "click",
}, 
{
    trigger: '[name=product_template_id] button.fa-pencil',  // edit the matrix
    run: "click",
}, {
    trigger: ".modal .o_matrix_input_table",
    in_modal: false,
    run: function () {
        // update some of the matrix values.
        [...document.querySelectorAll(".o_matrix_input")]
            .slice(8, 16)
            .forEach((el) => (el.value = 4));
    } // set the qty to 4 for half of the matrix products.
}, {
    trigger: ".modal button:contains(Confirm)", // apply the matrix
    in_modal: false,
    run: "click",
}, 
{
    trigger: '.o_field_cell.o_data_cell.o_list_number:contains("4.00")',
},
{
    trigger: '.o_form_button_save',
    run: 'click', // SAVE Sales Order, after matrix has been applied.
},
// Ensures the matrix is opened with the values, when adding the same product.
{
    trigger: ".o_form_status_indicator_buttons.invisible",
},
{
    trigger: 'a:contains("Add a product")',
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "edit Matrix",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Matrix")',
    run: "click",
}, {
    trigger: 'input[value="4"]',
    run: function () {
        // update some values of the matrix
        [...document.querySelectorAll("input[value='4']")]
            .slice(0, 4)
            .forEach((el) => (el.value = 8.2));
    }
}, {
    trigger: ".modal button:contains(Confirm)", // apply the matrix
    in_modal: false,
    run: "click",
        },
        {
            trigger: ".o_field_cell.o_data_cell.o_list_number:contains(8.20)",
        },
        ...stepUtils.saveForm(),
    ],
});
