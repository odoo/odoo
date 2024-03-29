/** @odoo-module **/
    
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { boundariesIn, setSelection } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

registry.category("web_tour.tours").add('mailing_editor_theme', {
    test: true,
    url: '/web',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Select the 'Email Marketing' app.",
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        },
        {
            content: "Click on the create button to create a new mailing.",
            trigger: 'button.o_list_button_add',
        },
        {
            content: "Fill in Subject",
            trigger: '#subject_0',
            run: "edit Test Basic Theme",
        },
        {
            content: "Fill in Mailing list",
            trigger: '#contact_list_ids_0',
            run: "edit Newsletter",
        },
        {
            content: "Pick 'Newsletter' option",
            trigger: '.o_input_dropdown a:contains(Newsletter)',
        },
        {
            content: "Pick the basic theme",
            trigger: ':iframe #basic',
            extra_trigger: ':iframe .o_mail_theme_selector_new',
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'html:has(#oe_snippets.d-none)',
            extra_trigger: ':iframe html:not(:has(.o_mail_theme_selector_new))',
            run: () => null, // no click, just check
        },
        {
            content: "Click on the New button to create another mailing",
            trigger: 'button.o_form_button_create',
        },
        {
            content: "Fill in Subject",
            trigger: '#subject_0',
            extra_trigger: ':iframe .o_mail_theme_selector_new',
            run: "edit Test Newsletter Theme",
        },
        {
            content: "Fill in Mailing list",
            trigger: '#contact_list_ids_0',
            run: "edit Newsletter",
        },
        {
            content: "Pick 'Newsletter' option",
            trigger: '.o_input_dropdown a:contains(Newsletter)',
        },
        {
            content: "Pick the newsletter theme",
            trigger: ':iframe #newsletter',
        },
        {
            content: "Make sure the snippets menu is displayed",
            trigger: '#oe_snippets',
            run: () => null, // no click, just check
        },
        {
            content: 'Save form',
            trigger: '.o_form_button_save',
        },
        {
            content: 'Go back to previous mailing',
            trigger: 'button.o_pager_previous',
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'html:has(#oe_snippets.d-none)',
            run: () => null,
        },
        {
            content: "Add some content to be selected afterwards",
            trigger: ':iframe p',
            run: "editor content",
        },
        {
            content: "Select text",
            trigger: ':iframe p:contains(content)',
            run() {
                setSelection(...boundariesIn(this.anchor), false);
            }
        },
        {
            content: "Make sure the floating toolbar is visible",
            trigger: '#toolbar.oe-floating[style*="visible"]',
            run: () => null,
        },
        {
            content: "Open the color picker",
            trigger: '#toolbar #oe-text-color',
        },
        {
            content: "Switch back to solid tab from custom tab",
            trigger: '.colorpicker button[data-target="theme-colors"]',// Switch back to solid tab
        },
        {
            content: "Pick a color",
            trigger: '#toolbar button[data-color="o-color-1"]',
        },
        {
            content: "Check that color was applied",
            trigger: ':iframe p font.text-o-color-1',
            run: () => null,
        },
        {
            content: 'Save changes',
            trigger: '.o_form_button_save',
        },
        {
            content: "Go to 'Mailings' list view",
            trigger: '.breadcrumb a:contains(Mailings)'
        },
        {
            content: "Open newly created mailing",
            trigger: 'td:contains("Test Basic Theme")',
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'html:has(#oe_snippets.d-none)',
            run: () => null,
        },
        {
            content: "Select content",
            trigger: ':iframe p:contains(content)',
            run() {
                setSelection(...boundariesIn(this.anchor), false);
            }
        },
        {
            content: "Make sure the floating toolbar is visible",
            trigger: '#toolbar.oe-floating[style*="visible"]',
            run: () => null,
        },
        ...stepUtils.discardForm(),
    ]
});
