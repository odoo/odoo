odoo.define('account.dashboard.setup.tour', function (require) {
    "use strict";

    var core = require('web.core');
    var tour = require('web_tour.tour');

    var _t = core._t;

    tour.register('account_render_report', {
        test: true,
        url: '/web',
    }, [tour.stepUtils.showAppsMenuItem(),
    {
        id: 'account_menu_click',
        trigger: '.o_app[data-menu-xmlid="account.menu_finance"]',
        position: 'bottom',
    }, {
        trigger: '.o_data_row:first',
        extra_trigger: '.breadcrumb',
    }, {
        trigger: '.o_control_panel button:contains("' + _t('Print') + '")',
    }, {
        // TODO: remove the first selector when the "account_move_form" view is converted to owl
        trigger: '.o_control_panel .o-dropdown-menu a:contains("' + _t('Invoices without Payment') + '"), .o_control_panel .o-dropdown--menu span:contains("' + _t('Invoices without Payment') + '")',
    }, {
        trigger: 'iframe .o_report_layout_standard h2',
        content: 'Primary color is correct',
        run: function () {
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
        ]);
});
