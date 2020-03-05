odoo.define('sale.product_configurator_single_custom_attribute_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_single_custom_attribute_tour', {
    url: "/web",
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order"
}, {
    trigger: "a:contains('Add a product')"
}, {
    trigger: 'div[name="product_template_id"] input',
    run: function (){
        var $input = $('div[name="product_template_id"] input');
        $input.click();
        $input.val('Custo');
        // fake keydown to trigger search
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        $input.trigger(keyDownEvent);
    }
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: 'click'
}, {
    trigger: '.configurator_container span:contains("Aluminium")',
    run: function () {
        // used to check that the radio is NOT rendered
        if ($('.configurator_container ul[data-attribute_id].d-none input[data-value_name="single product attribute value"]').length === 1) {
            $('.configurator_container').addClass('tour_success');
        }
    }
}, {
    trigger: '.configurator_container.tour_success',
    run: function () {
        //check
    }
}, {
    trigger: '.configurator_container .variant_custom_value',
    run: 'text great single custom value'
}, {
    trigger: '.o_sale_product_configurator_add',
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: 'td.o_data_cell:contains("single product attribute value: great single custom value")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check custom value
}, {
    trigger: 'td.o_product_configurator_cell',
}, {
    trigger: '.o_edit_product_configuration',
}, {
    trigger: '.configurator_container .variant_custom_value',
    run: function () {
        // check custom value initialized
        if ($('.configurator_container .variant_custom_value').val() === "great single custom value") {
            $('.configurator_container').addClass('tour_success_2');
        }
    }
}, {
    trigger: '.configurator_container.tour_success_2',
    run: function () {
        //check
    }
}]);

});
