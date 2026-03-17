import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('snippets_mailing_menu_toolbar', {
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        run: "click",
    },
    {
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
        run: "click",
    },
    {
        content: "Wait for the theme selector to load.",
        trigger: ':iframe .o_mailing_template_preview_wrapper',
        run: "click",
    },
    {
        content: "Make sure there does not exist a floating toolbar",
        trigger: "iframe:not(:visible)",
        run: function () {
            const iframeDocument = this.anchor.contentDocument;
            if (iframeDocument.querySelector('#toolbar.oe-floating')) {
                console.error('There should not be a floating toolbar in the iframe');
            }
        },
    },
    {
        content: "Make sure the empty template is an option on non-mobile devices.",
        trigger: ':iframe .o_mailing_template_preview_wrapper [data-name="empty"]',
    },
    {
        content: "Click on the default 'welcome' template.",
        trigger: ':iframe .o_mailing_template_preview_wrapper [data-name="default"]',
        run: "click",
    },
    {
        content: "Make sure the snippets menu is not hidden",
        trigger: ".o-snippets-menu",
    },
    {
        content: "Click on the empty wrapper to open the block library",
        trigger: ":iframe .o_mail_wrapper_td.oe_empty",
        run: "click",
    },
    {
        content: "Wait for the block library dialog to open",
        trigger: ".modal-content.o_add_snippet_dialog",
    },
    {
        content: "Select the Text tab in the block library",
        trigger: ".o_dialog button#tab_text",
        run: "click",
    },
    {
        content: "Wait for the text blocks to load",
        trigger: ".o_add_snippet_dialog :iframe .o_snippet_preview_wrap[data-snippet-id='s_text_block']",
    },
    {
        content: "Select a text block from the dialog",
        trigger: ".o_add_snippet_dialog :iframe .o_snippet_preview_wrap[data-snippet-id='s_text_block']",
        run: "click",
    },
    {
        content: "Wait for the block library dialog to close after selection",
        trigger: "body:not(:has(.modal-content.o_add_snippet_dialog))",
    },
    {
        content: "Wait for .s_text_block to be loaded",
        trigger: ':iframe .s_text_block p',
    },
    {
        content: "Click and select p block inside the editor",
        trigger: 'iframe',
        run: function () {
            const iframeWindow = this.anchor.contentWindow;
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
        trigger: ".overlay .o-we-toolbar",
    },
    ...stepUtils.discardForm(),
    ],
});
