/** @odoo-module alias=account.dashboard.setup.tour **/
    
    import core from "web.core";
    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";
    import "web.legacy_tranlations_loaded";

    var _t = core._t;

    registry.category("web_tour.tours").add('account_render_report', {
        test: true,
        url: '/web',
    steps: [stepUtils.showAppsMenuItem(),
    {
        id: 'account_menu_click',
        trigger: '.o_app[data-menu-xmlid="account.menu_finance"]',
        position: 'bottom',
    }, {
        trigger: '.o_data_row:first .o_data_cell',
        extra_trigger: '.o_breadcrumb',
    }, {
        trigger: '.o_control_panel .o_cp_action_menus .dropdown-toggle',
        extra_trigger: '.o_breadcrumb .active:contains("INV/")',
    }, {
        trigger: `.o_control_panel .o_cp_action_menus .dropdown-toggle:contains("${_t("Print")}")`,
        run: function () {
            this.$anchor[0].dispatchEvent(new MouseEvent("mouseenter"));
        },
    }, {
        trigger: '.o_control_panel .o_cp_action_menus .o_menu_item:contains("' + _t('Invoices without Payment') + '")',
    }, {
        trigger: 'iframe .o_report_layout_standard h2',
        content: 'Primary color is correct',
        run: function () {
            // This step fails randomly. This is probably because the css assets are not be fully
            // loaded at the time this step is reached. Can we just completely get rid of this css checks?
            if (this.$anchor.css('color') !== "rgb(18, 52, 86)") {
                console.error('The primary color should be the one set on the company.');
            }
        },
    }, {
        trigger: 'iframe .o_report_layout_standard #informations div strong',
        content: 'Secondary color is correct',
        run: function () {
            if (this.$anchor.css('color') !== "rgb(120, 145, 1)") {
                console.error('The secondary color should be the one set on the company.');
            }
        },
    }
        ]});
