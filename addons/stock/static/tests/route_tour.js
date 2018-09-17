odoo.define('stock.tour', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('stock', {
    test: true,
    url: '/web?debug=assets#action=stock.action_stock_config_settings',
    },
     [
        {
            content:    "wait web client",
            trigger:    ".o_base_settings",
            run: function() {}
        },
        {
            content: "active 'Multi-Step Routes'",
            trigger: '.o_field_boolean[name="group_stock_adv_location"]',
            run: function() {
                if (!this.$anchor.find('input').prop('checked')) {
                    this.$anchor.find('label').click();
                    $('.o_statusbar_buttons button[name="execute"]').click();
                }
            }
        },
        {
            content: "list of product variants",
            trigger: '.o_menu_sections [data-menu-xmlid="stock.menu_product_variant_config_stock"]',
            extra_trigger: '.o_menu_sections:has(a[data-menu-xmlid="stock.menu_routes_config"])',
            timeout: 5000,
        },
        {
            content: "select a product variant",
            trigger: '.oe_kanban_global_click:first',
        },
        {
            content: "click on routes",
            trigger: 'button.oe_stat_button i.fa-cogs',
        },
        {
            content: "print the report",
            trigger: 'button[name="print_report"]',
        },
        {
            content: "print inside the report and check the breadcrum",
            trigger: '.o_content iframe .o_report_stock_rule_rule_name',
            extra_trigger: 'ol.breadcrumb li:eq(2).active',
        },
        {
            content: "print the report",
            trigger: 'ol.breadcrumb li:eq(3).active',
        },
    ]
);

});
