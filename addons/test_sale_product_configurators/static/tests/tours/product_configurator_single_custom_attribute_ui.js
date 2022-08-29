/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('sale_product_configurator_single_custom_attribute_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
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
    trigger: '.oe_advanced_configurator_modal span:contains("Aluminium")',
    run: function () {
        // used to check that the radio is NOT rendered
        if ($('.oe_advanced_configurator_modal ul[data-attribute_id].d-none input[data-value_name="single product attribute value"]').length === 1) {
            $('.oe_advanced_configurator_modal').addClass('tour_success');
        }
    }
}, {
    trigger: '.oe_advanced_configurator_modal.tour_success',
    run: function () {
        //check
    }
}, {
    trigger: '.oe_advanced_configurator_modal .variant_custom_value',
    run: 'text great single custom value'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: 'td.o_data_cell:contains("single product attribute value: great single custom value")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check custom value
}, {
    trigger: 'td.o_product_configurator_cell',
}, {
    trigger: '.o_edit_product_configuration',
}, {
    trigger: '.main_product .variant_custom_value',
    run: function () {
        // check custom value initialized
        if ($('.main_product .variant_custom_value').val() === "great single custom value") {
            $('.main_product').addClass('tour_success_2');
        }
    }
}, {
    trigger: '.main_product.tour_success_2',
    run: function () {
        //check
    }
}, {
    trigger: '.main_product',
    run: function () {
        window.location.href = window.location.origin + '/web';
    }
}, {
    trigger: '.o_navbar',
    run: function() {},  // Check the home page is loaded
}]);
