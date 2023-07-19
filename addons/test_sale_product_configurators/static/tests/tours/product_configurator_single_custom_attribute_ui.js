/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_single_custom_attribute_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order'
}, {
    trigger: 'a:contains("Add a product")'
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>input:nth-child(7)',
    run: 'text great single custom value'
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("single product attribute value: great single custom value")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check custom value
}, {
    trigger: 'div[name="product_template_id"]',
}, {
    trigger: '.fa-pencil',
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>input:nth-child(7)',
    run: function () {
        // check custom value initialized
        if ($('main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>input:nth-child(7)').val() === "great single custom value") {
            $('main').addClass('tour_success_2');
        }
    }
}, {
    trigger: 'main.tour_success_2',
    isCheck: true,
}, {
    trigger: 'button:contains(Back)',
},
    ...stepUtils.discardForm()
]});
