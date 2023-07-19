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
            content: "Wait for the theme selector to load and pick the basic theme.",
            trigger: 'iframe #basic',
            extra_trigger: 'iframe .o_mail_theme_selector_new',
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'iframe html:has(#oe_snippets.d-none)',
            run: () => null, // no click, just check
        },
        {
            content: "Add some content to be selected afterwards",
            trigger: 'iframe p',
            run: 'text content',
        },
        {
            content: "Select text",
            trigger: 'iframe p:contains(content)',
            run() {
                setSelection(...boundariesIn(this.$anchor[0]), false);
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
            content: "Pick a color",
            trigger: '#toolbar button[data-color="o-color-1"]',
        },
        {
            content: "Check that color was applied",
            trigger: 'iframe p font.text-o-color-1',
            run: () => null,
        },
        {
            content: "Fill in Subject",
            trigger: '[name="subject"] input',
            run: 'text TestFromTour',
        },
        {
            content: "Fill in Mailing list",
            trigger: '[name="contact_list_ids"] input',
            run: 'text Newsletter',
        },
        {
            content: "Pick 'Newsletter' option",
            trigger: '.o_input_dropdown a:contains(Newsletter)',
        },
        {
            content: "Save and go to 'Mailings' list view",
            trigger: '.breadcrumb a:contains(Mailings)'
        },
        {
            content: "Open newly created mailing",
            trigger: 'td:contains(TestFromTour)',
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: 'iframe html:has(#oe_snippets.d-none)',
            run: () => null,
        },
        {
            content: "Select content",
            trigger: 'iframe p:contains(content)',
            run() {
                setSelection(...boundariesIn(this.$anchor[0]), false);
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
