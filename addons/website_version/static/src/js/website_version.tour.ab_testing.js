(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
        id:   'ab_testing',
        name: "Tutorial to configure A/B testing",
        path: '/',
        mode: 'tutorial',
        steps: [
            //1.

            {
                title:      _t("Welcome to the tutorial"),
                content:   _t("This tutorial will guide you to make A/B testing."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
            },
            {
                title:      _t("Click on Version"),
                popover:   { fixed: true },
                element:   'a[id="version-menu-button"]:contains("Version"):first',
            },
            {
                title:     _t("Click on New Experiment"),
                popover:   { fixed: true },
                element:   'a[data-action="create_experiment"]:contains("New Experiment"):first',
            },
            {
                title:     _t("Click on Configure"),
                popover:   { fixed: true },
                element:   '.modal button[type="button"]:contains("Configure")',
            },
            {
                title:     _t("Click on Edit"),
                popover:   { fixed: true },
                waitFor:   'button.GoogleAccess:contains("Authorize google")',
                element:   'button.oe_button:contains("Edit")',
            },
            {
                title:     _t("Write the GA key"),
                waitFor:   'button.oe_button.oe_form_button_save:contains("Save"):visible',
                popover:   { fixed: true },
                element:   'input[placeholder="UA-XXXXXXXX-Y"]',
                sampleText: 'UA-55031254-1',
            },
            {
                title:     _t("Write the View ID"),
                waitFor:   'button.oe_button.oe_form_button_save:contains("Save"):visible',
                popover:   { fixed: true },
                element:   'input[placeholder="7654321"]',
                sampleText: '91492412',
            },
            {
                title:     _t("Click on save"),
                popover:   { fixed: true },
                element:   'button.oe_button.oe_form_button_save:contains("Save")',
            },
            {
                title:     _t("Click on Authorize google"),
                popover:   { fixed: true },
                waitFor:   'button.oe_button:contains("Edit"):visible',
                element:   'button.GoogleAccess:contains("Authorize google")',
            },








            

        ]
    });

}());