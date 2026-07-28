/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('snippets_mailing_menu_toolbar', {
    test: true,
    url: '/web',
    steps: () => [
    stepUtils.showAppsMenuItem(), {
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
        content: "Make sure there does not exist a floating toolbar",
        trigger: 'iframe',
        run: function () {
            const iframeDocument = this.$anchor[0].contentDocument;
            if (iframeDocument.querySelector('#toolbar.oe-floating')) {
                console.error('There should not be a floating toolbar in the iframe');
            }
        },
    },
    {
        content: "Make sure the empty template is an option on non-mobile devices.",
        trigger: 'iframe #empty',
        run: () => null,
    },
    {
        content: "Click on the default 'welcome' template.",
        trigger: 'iframe #default',
    },
    { // necessary to wait for the cursor to be placed in the first p
      // and to avoid leaving the page before the selection is added
        content: "Wait for template selection event to be over.",
        trigger: 'iframe .o_editable.theme_selection_done',
    },
    {
        content: "Make sure the snippets menu is not hidden",
        trigger: 'iframe #oe_snippets:not(.d-none)',
        run: () => null,
    },
    {
        content: "Wait for .s_text_block to be populated",
        trigger: 'iframe .s_text_block p',
        run: () => null,
    },
    {
        content: "Click and select p block inside the editor",
        trigger: 'iframe',
        run: function () {
            const iframeWindow = this.$anchor[0].contentWindow;
            const iframeDocument = iframeWindow.document;
            const p = iframeDocument.querySelector('.s_text_block p');
            p.click();
            const selection = iframeWindow.getSelection();
            const range = iframeDocument.createRange();
            range.selectNodeContents(p);
            selection.removeAllRanges();
            selection.addRange(range);
        },
    },
    {
        content: "Make sure the toolbar is there",
        trigger: 'iframe #oe_snippets .o_we_customize_panel #toolbar',
        run: () => null,
    },
    ...stepUtils.discardForm(),
    ],
});
