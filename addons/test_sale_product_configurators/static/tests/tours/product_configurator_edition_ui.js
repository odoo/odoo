/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_edition_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order',
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk")) label:contains("Aluminium")',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk (TEST) (Aluminium, White)"))',
    isCheck: true,
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Aluminium, White)")',
    extra_trigger: 'div[name="order_line"]',
    isCheck: true // check added product
}, {
    trigger: 'div[name="product_template_id"]',
}, {
    trigger: '.fa-pencil',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk"))>td:nth-child(2)>ul:nth-child(3)>li:nth-child(2)>div label:contains("Aluminium") > input:checked',
    isCheck: true, // check updated legs
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk"))>td:nth-child(4) span:contains("800.40")',
    isCheck: true, // check updated price
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk")) label:contains("Custom") > input',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk"))>td:nth-child(2)>input',
    run: 'text nice custom value'
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk")) label[style="background-color:#000000"] input',
}, {
    trigger: '.o_sale_product_configurator_name:contains("Customizable Desk (TEST) (Custom, Black)")',
    isCheck: true, // used to sync with server
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, Black)")',
    extra_trigger: 'div[name="order_line"]',
    isCheck: true, // check updated product
}, {
    trigger: 'td.o_data_cell:contains("Custom: nice custom value")',
    extra_trigger: 'div[name="order_line"]',
    isCheck: true, // check custom value
}, {
    trigger: 'div[name="product_template_id"]',
}, {
    trigger: '.fa-pencil',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk"))>td:nth-child(2)>input',
    run: 'text another nice custom value'
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Custom: another nice custom value")',
    extra_trigger: 'div[name="order_line"]',
    isCheck: true, // check custom value
}, {
    trigger: 'div[name="product_template_id"]',
}, {
    trigger: '.fa-pencil',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk")) label:contains("Steel") > input',
},  {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk (TEST) (Steel, Black)"))',
    isCheck: true,
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk"))>td:nth-child(3)>div>button:has(i.fa-plus)',
}, {  // Mr Tajine Saucisse uses the pricelist that has a rule when 2 or more products. Price is 600
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(2)>td>span:contains("1,200.00")',
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("2.00")',
    isCheck: true, // check quantity
}, {
    trigger: 'div[name="product_template_id"]',
    run: function () {
        // used to check that the description does not contain a custom value anymore
        if ($('td.o_data_cell:contains("Custom: another nice custom value")').length === 0){
            $('td.o_data_cell:contains("Customizable Desk (TEST) (Steel, Black)")').html('tour success');
        }
    }
}, {
    trigger: 'td.o_data_cell:contains("tour success")',
    extra_trigger: 'div[name="order_line"]',
    isCheck: true,
},
    ...stepUtils.saveForm(),
]});
