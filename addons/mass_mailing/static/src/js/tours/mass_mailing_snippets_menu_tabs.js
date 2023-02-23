/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('mass_mailing_snippets_menu_tabs', {
    test: true,
    url: '/web',
}, [
    tour.stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    },
    {
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
    },
    {
        content: "Click on the 'Start From Scratch' template.",
        trigger: 'iframe #empty',
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'iframe .o_we_customize_design_btn',
    },
    {
        content: "Click on the empty 'DRAG BUILDING BLOCKS HERE' area.",
        trigger: 'iframe .oe_structure.o_mail_no_options',
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'iframe .o_we_customize_design_btn',
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: 'iframe .o_we_customize_panel .snippet-option-DesignTab',
        run: () => null, // it's a check
    },
    {
        content: "Click on the style tab.",
        trigger: 'iframe .o_we_customize_snippet_btn',
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'iframe .o_we_customize_design_btn',
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: 'iframe .o_we_customize_panel .snippet-option-DesignTab',
        run: () => null, // it's a check
    },
    ...tour.stepUtils.discardForm(),
]);


tour.register('mass_mailing_snippets_menu_toolbar_new_mailing_mobile', {
    test: true,
    url: '/web',
}, [
    tour.stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    },
    {
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
        mobile: true,
    },
    {
        content: "Check templates available in theme selector",
        trigger: 'iframe .o_mail_theme_selector_new',
        run: function () {
            if (this.$anchor[0].querySelector('#empty')) {
                console.error('The empty template should not be visible on mobile.');
            }
        },
        mobile: true,
    },
    {
        content: "Make sure the toolbar isn't floating -> on top of the selection menu",
        trigger: 'iframe #toolbar:not(.oe-floating)',
        run: () => null, // it's a check
        mobile: true,
    },
    {
        content: "Click on the 'Start From Scratch' template.",
        trigger: 'iframe #default',
        mobile: true,
    },
    {
        content: "Make sure the snippets menu is hidden",
        trigger: 'iframe #oe_snippets.d-none',
        run: () => null, // it's a check
        mobile: true,
    },
    {
        content: "Select an editable element",
        trigger: 'iframe .s_text_block',
        mobile: true,
    },
    {
        content: "Make sure the toolbar is there, with the tables formating tool",
        trigger: 'iframe #toolbar.oe-floating #table:not(.d-none)',
        run: () => null, // it's a check
        mobile: true,
    },
]);

tour.register('mass_mailing_snippets_menu_toolbar', {
    test: true,
    url: '/web',
}, [
    tour.stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    },
    {
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
    },
    {
        content: "Wait for the theme selector to load.",
        trigger: 'iframe .o_mail_theme_selector_new',
    },
    {
        content: "Make sure the toolbar isn't floating -> on top of the selection menu",
        trigger: 'iframe',
        run: function () {
            if (this.$anchor[0].querySelector('#toolbar:not(.oe-floating)')) {
                console.error('There should not be any floating toolbar on the theme selection screen.');
            }
        },
    },
    {
        content: "Make sure the empty template is an option on non-mobile devices.",
        trigger: 'iframe #empty',
        run: () => null, // it's a check
    },
    {
        content: "Click on the default 'welcome' template.",
        trigger: 'iframe #default',
    },
    {
        content: "Make sure the snippets menu is not hidden",
        trigger: 'iframe #oe_snippets:not(.d-none)',
        run: () => null, // it's a check
    },
    {
        content: "Select an editable element",
        trigger: 'iframe .s_text_block',
    },
    {
        content: "Make sure the toolbar is there",
        trigger: 'iframe .o_we_customize_panel',
        run: function () {
            const toolbar = this.$anchor[0].querySelector('#toolbar');
            if (!toolbar) {
                console.error('The toolbar should be in the customize panel when a text block is selected');
            }
        },
    },
    ...tour.stepUtils.discardForm(),
]);
