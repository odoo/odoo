odoo.define('account.dashboard.setup.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('account_dashboard_setup_tour', {
    test: true,
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

});