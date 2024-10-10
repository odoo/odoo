/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { boundariesIn, setSelection } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

registry.category("web_tour.tours").add('mailing_editor_theme', {
    url: '/odoo',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
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
            run: "click",
        },
        {
            trigger: ":iframe .o_mail_theme_selector_new",
        },
        {
            content: "Pick the basic theme",
            trigger: ':iframe #basic',
            run: "click",
        },
        {
            trigger: ":iframe html:not(:has(.o_mail_theme_selector_new))",
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'html:has(#oe_snippets.d-none)',
        },
        ...stepUtils.saveForm(),
        {
            content: "Click on the New button to create another mailing",
            trigger: 'button.o_form_button_create',
            run: "click",
        },
        {
            trigger: ":iframe .o_mail_theme_selector_new",
        },
        {
            content: "Fill in Subject",
            trigger: '#subject_0',
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
            run: "click",
        },
        {
            content: "Pick the newsletter theme",
            trigger: ':iframe #newsletter',
            run: "click",
        },
        {
            content: "Make sure the snippets menu is displayed",
            trigger: '#oe_snippets',
        },
        ...stepUtils.discardForm(),
        {
            content: 'Go back to previous mailing',
            trigger: 'td[name="subject"]:contains(Test Basic Theme)',
            run: "click",
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'html:has(#oe_snippets.d-none)',
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
        },
        {
            content: "Open the color picker",
            trigger: '#toolbar #oe-text-color',
            run: "click",
        },
        {
            content: "Pick a color",
            trigger: '#toolbar button[data-color="o-color-1"]',
            run: "click",
        },
        {
            content: "Check that color was applied",
            trigger: ':iframe p font.text-o-color-1',
        },
        ...stepUtils.saveForm(),
        {
            content: "Go to 'Mailings' list view",
            trigger: '.breadcrumb a:contains(Mailings)',
            run: "click",
        },
        {
            content: "Open newly created mailing",
            trigger: 'td:contains("Test Basic Theme")',
            run: "click",
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'html:has(#oe_snippets.d-none)',
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
        },
        ...stepUtils.discardForm(),
    ]
});
