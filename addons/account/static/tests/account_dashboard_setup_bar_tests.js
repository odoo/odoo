odoo.define('account.dashboard.setup.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('account_dashboard_setup_tour', {
    test: true,
    url: '/web',
}, [tour.STEPS.SHOW_APPS_MENU_ITEM,
    {
        trigger: '.o_app[data-menu-xmlid="account.menu_finance"]',
        position: 'bottom',
    }, {
        content:    "wait web client",
        trigger:    ".o_onboarding_container",
        extra_trigger: ".breadcrumb",
        run: function () {},
    }, {
        content: "Checks the onboarding's step for Invoice layout is here",
        trigger: ".o_onboarding_step_title a:contains('" + _t('Invoice Layout') + "')",
        run: function () {},
    },  {
        content: "Open the modal to customize the layout. This tour step ensures the step has not been done before",
        trigger: "a.o_onboarding_step_action:contains('" + _t('Customize') + "')",
    }, {
        content: "Modal is opened",
        trigger: ".modal-content .modal-title",
        content: _t('Configure your document layout'),
    }, {
        content: "Saves the settings",
        trigger: ".modal-content button[name='document_layout_save']",
    }, {
        content: "Checks the onboarding's step has been written as done",
        trigger: "a.o_onboarding_all_done[data-model='base.document.layout']",
        run: function () {},
    }
]);

tour.register('account_render_report', {
    url: '/web',
}, [tour.STEPS.SHOW_APPS_MENU_ITEM,
    {
        trigger: '.o_app[data-menu-xmlid="account.menu_finance"]',
        position: 'bottom',
    }, {
        content:    "wait web client",
        trigger:    ".o_onboarding_container",
        extra_trigger: ".breadcrumb",
        run: function () {},
    }, {
        trigger: '.o_data_row:contains("'+ _t('Open') +'"):first',
    }, {
        trigger: '.o_control_panel button:contains("' + _t('Print') + '")',
    }, {
        trigger: '.o_control_panel div.o_dropdown_menu a:contains("'+ _t('Invoices without Payment')+ '")',
    }, {
        content: 'Wait for the report to render',
        trigger: 'iframe body.container',
    }, {
        trigger: 'iframe .o_report_layout_standard h2',
        content: 'Primary color is correct',
        run: function () {
            if (this.$anchor.css('color') !== "rgb(18, 52, 86)") {
                throw new Error(_('The primary color should be the one set on the company.'));
            }
        },
    }, {
        trigger: 'iframe .o_report_layout_standard #informations div strong',
        content: 'Secondary color is correct',
        run: function () {
            if (this.$anchor.css('color') !== "rgb(120, 145, 1)") {
                throw new Error(_('The secondary color should be the one set on the company.'));
            }
        },
    }
]);
});
