/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

let optionVariantImage;

registry.category("web_tour.tours").add('sale_product_configurator_advanced_tour', {
    url: '/web',
    test: true,
    steps: [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
},  {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order'
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: '.o_field_widget[name=partner_shipping_id] .o_external_button', // Wait for onchange_partner_id
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody span:contains("Custom")'
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>input',
    run: 'text Custom 1'
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>ul:nth-child(8) span:contains("PAV9")',
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>ul:nth-child(8) ~ input',
    run: 'text Custom 2'
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>ul:nth-child(11) span:contains("PAV5")',
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>select:nth-child(15)',
    run: function (){
        let inputValue = $('main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>select:nth-child(15) option:contains("PAV9")').val();
        $('main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>select:nth-child(15)').val(inputValue);
        $('main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>select:nth-child(15)')[0].dispatchEvent(new Event("change"));
    }
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(2)>select:nth-child(15) ~ input',
    run: 'text Custom 3'
}, {
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1) strong:contains("Custom, White, PAV9, PAV5, PAV1")',
    isCheck: true,
}, {
    trigger: 'main.modal-body>table:nth-child(2)>tbody>tr:nth-child(1)>td:nth-child(2):contains("Conference Chair (TEST) (Steel)")',
    run: function () {
        optionVariantImage = $('main.modal-body>table:nth-child(2)>tbody>tr:nth-child(1)>td:nth-child(1)>img').attr('src');
    }
}, {
    trigger: 'main.modal-body>table:nth-child(2)>tbody>tr:nth-child(1) label:contains("Aluminium")',
}, {
    trigger: 'main.modal-body>table:nth-child(2)>tbody>tr:nth-child(1)>td:nth-child(2):contains("Conference Chair (TEST) (Aluminium)")',
    run: function () {
        let newVariantImage = $('main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(1)>img').attr('src');
        if (newVariantImage !== optionVariantImage) {
            $('<p>').text('image variant option src changed').insertAfter('main.modal-body>table:nth-child(2)>tbody>tr:nth-child(1)>td:nth-child(2)>div>strong');
        }
    }
}, {
    trigger: 'main.modal-body>table:nth-child(2)>tbody>tr:nth-child(1)>td:nth-child(2)>div:contains("image variant option src changed")',
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, White, PAV9, PAV5, PAV1)"):not(:contains("PA9: Single PAV"))',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: Custom 1")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA1: PAV9: Custom 2")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA4: PAV9: Custom 3")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA5: PAV1")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA7: PAV1")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA8: PAV1")',
    isCheck: true,
}, ...stepUtils.saveForm()
]});
