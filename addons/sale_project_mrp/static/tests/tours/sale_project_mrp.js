odoo.define('sale_project_mrp.tour', function (require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

    tour.register('sale_project_mrp_tour',{
        url:"/web"
    },[tour.STEPS.SHOW_APPS_MENU_ITEM, {
        trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',  
        edition: 'community'
    },{
        trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
        edition: 'enterprise'
    },{
        content: 'Create Sale Order',
        trigger: ".o_list_button_add",
        extra_trigger: ".o_sale_order",
    },{
        content: "search the partner",
        trigger: 'div[name="partner_id"] input',
        run: 'text Azure'
    },{
        content: "select the partner",
        trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
    },{
        content: 'Add a product',
        trigger: "a:contains('Add a product')",
    },{
        content: 'Add your super kit to the sale order',
        trigger: 'div[name="product_id"] input',
        extra_trigger: ".o_sale_order",
        run: function (){
            var $input = $('div[name="product_id"] input');
            $input.click();
            $input.val('super kit');
            var keyDownEvent = jQuery.Event("keydown");
            keyDownEvent.which = 42;
            $input.trigger(keyDownEvent);
        }
    },{
        content: "select the kit",
        trigger: 'ul.ui-autocomplete > li > a:contains(super)',
    },{
        content: 'Confirm quotation',
        trigger: "button:contains('Confirm')",
    },{
        content: 'Check project generation',
        trigger: "button:contains('Project')",
    }
    ]);
});
