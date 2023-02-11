odoo.define('sale.product_configurator_edition_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_edition_tour', {
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
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        $input.trigger(keyDownEvent);
    }
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: 'click'
}, {
    trigger: '.main_product span:contains("Steel")',
    run: function () {
        $('input.product_id').change(function () {
            $('.show .modal-footer .btn-primary').attr('request_count', 1);
        });
    }
}, {
    trigger: '.main_product span:contains("Aluminium")'
}, {
    trigger: '.btn-primary[request_count="1"]',
    extra_trigger: '.show .modal-footer',
    run: function (){} // used to sync with "get_combination_info" completion
}, {
    trigger: '.btn-primary:not(.disabled)',
    extra_trigger: '.show .modal-footer',
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Aluminium, White)")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check added product
}, {
    trigger: 'td.o_product_configurator_cell',
}, {
    trigger: '.o_edit_product_configuration',
}, {
    trigger: '.configurator_container li.js_attribute_value:has(span:contains("Aluminium")) input:checked',
    run: function (){} // check updated legs
}, {
    trigger: 'span.oe_currency_value:contains("800")',
    run: function (){} // check updated price
}, {
    trigger: '.configurator_container span:contains("Steel")',
    run: function () {
        $('input.product_id').change(function () {
            if ($('.o_sale_product_configurator_edit').attr('request_count')) {
                $('.o_sale_product_configurator_edit').attr('request_count',
                    parseInt($('.o_sale_product_configurator_edit').attr('request_count')) + 1);
            } else {
                $('.o_sale_product_configurator_edit').attr('request_count', 1);
            }
        });
    }
}, {
    trigger: '.configurator_container span:contains("Custom")',
    run: function () {
        // FIXME awa: since jquery3 update it doesn't "click"
        // on the element without this run (and 'run: "click"'
        // doesn't work either)
        $('.configurator_container span:contains("Custom")').click();
    }
}, {
    trigger: '.configurator_container .variant_custom_value',
    run: 'text nice custom value'
}, {
    trigger: 'input[data-value_name="Black"]',
    run: 'click'
}, {
    trigger: '.o_sale_product_configurator_edit[request_count="2"]',
    run: function (){} // used to sync with "get_combination_info" completion
}, {
    trigger: '.o_sale_product_configurator_edit',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, Black)")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check updated product
}, {
    trigger: 'td.o_data_cell:contains("Custom: nice custom value")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check custom value
}, {
    trigger: 'td.o_product_configurator_cell',
}, {
    trigger: '.o_edit_product_configuration',
}, {
    trigger: '.configurator_container .variant_custom_value',
    run: 'text another nice custom value'
}, {
    trigger: '.o_sale_product_configurator_edit',
}, {
    trigger: 'td.o_data_cell:contains("Custom: another nice custom value")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check custom value
}, {
    trigger: 'td.o_product_configurator_cell',
}, {
    trigger: '.o_edit_product_configuration',
}, {
    trigger: '.configurator_container span:contains("Steel")',
    run: function () {
        $('input.product_id').change(function () {
            $('.o_sale_product_configurator_edit').attr('request_count', 1);
        });
    }
}, {
    trigger: '.configurator_container span:contains("Steel")',
    run: function () {
        // FIXME awa: since jquery3 update it doesn't "click"
        // on the element without this run (and 'run: "click"'
        // doesn't work either)
        $('.configurator_container span:contains("Steel")').click();
    }
}, {
    trigger: '.o_sale_product_configurator_edit[request_count="1"]',
    run: function (){} // used to sync with "get_combination_info" completion
}, {
    trigger: '.configurator_container button.js_add_cart_json:has(.fa-plus)',
}, {
    trigger: '.o_sale_product_configurator_edit',
}, {
    trigger: 'td.o_data_cell:contains("2.00")',
    run: function (){} // check quantity
}, {
    trigger: 'td.o_product_configurator_cell',
    run: function () {
        // used to check that the description does not contain a custom value anymore
        if ($('td.o_data_cell:contains("Custom: another nice custom value")').length === 0){
            $('td.o_data_cell:contains("Customizable Desk (TEST) (Steel, Black)")').html('tour success');
        }
    }
}, {
    trigger: 'td.o_data_cell:contains("tour success")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){}
}]);

});
