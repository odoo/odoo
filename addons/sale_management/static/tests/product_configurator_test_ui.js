odoo.define('sale.product_configurator_tour', function(require) {
    "use strict";
    
    var tour = require('web_tour.tour');
    
    tour.register('sale_product_configurator_tour', {
        url: "/web",
        test: true,
    }, [{
        trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"], .oe_menu_toggler[data-menu-xmlid="sale.sale_menu_root"]'
    },  {
        trigger: ".o_list_button_add",
        extra_trigger: ".o_sale_order"
    }, {
        trigger: "a:contains('Configure a product')"
    }, {
        trigger: '.o_product_configurator .o_input_dropdown input',
        run: 'click'
    }, {
        trigger: 'li a:contains("Customizable Desk")',
        in_modal: false,
        extra_trigger: 'ul.ui-autocomplete',
        run: 'click'
    }, {
        trigger: '.configurator_container span:contains("Aluminium")',
        run: 'click'
    }, {
        trigger: ".o_sale_product_configurator_add",
        run: 'click'
    }, {
        trigger: 'span:contains("Aluminium")',
        extra_trigger: '.oe_optional_products_modal',
        run: 'click'
    }, {
        trigger: '.js_product:not(.in_cart) .js_add',
        extra_trigger: '.oe_optional_products_modal',
        run: 'click'
    }, {
        trigger: '.js_product:not(.in_cart) .js_add', // not a mistake, this adds the option's option
        extra_trigger: '.oe_optional_products_modal',
        run: 'click'
    }, {
        trigger: '.a-submit:not(.js_goto_shop)',
        extra_trigger: '.oe_optional_products_modal',
        run: 'click'
    }, 
    // check that 3 products were added to the SO
    { 
        trigger: 'td.o_data_cell:contains("[FURN_0098] Customizable Desk (White, Aluminium)")',
        extra_trigger: 'div[name="order_line"]',
        in_modal: false,
        run: function(){}
    }, {
        trigger: 'td.o_data_cell:contains("[E-COM13] Conference Chair (Aluminium)")',
        extra_trigger: 'div[name="order_line"]',
        in_modal: false,
        run: function(){}
    }, {
        trigger: 'td.o_data_cell:contains("Chair floor protection")',
        extra_trigger: 'div[name="order_line"]',
        in_modal: false,
        run: function(){}
    }]);
    
    });
    