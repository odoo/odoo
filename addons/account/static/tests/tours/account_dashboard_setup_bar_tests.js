odoo.define('account.dashboard.setup.tour', function (require) {
    "use strict";

    var core = require('web.core');
    const { registry } = require("@web/core/registry");
    const { stepUtils } = require('@web_tour/tour_service/tour_utils');

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
        extra_trigger: '.breadcrumb',
    }, {
        trigger: '.o_control_panel button:contains("' + _t('Print') + '")',
    }, {
        trigger: '.o_control_panel .o-dropdown--menu span:contains("' + _t('Invoices without Payment') + '")',
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
});
