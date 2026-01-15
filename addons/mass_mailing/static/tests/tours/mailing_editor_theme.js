import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { boundariesIn } from "@html_editor/utils/position";
import { setSelection } from "@html_editor/../tests/tours/helpers/editor";

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
            trigger: ".o_mailing_template_preview_wrapper",
        },
        {
            content: "Pick the basic theme",
            trigger: '.o_mailing_template_preview_wrapper [data-name="basic"]',
            run: "click",
        },
        {
            trigger: "html:not(:has(.o_mailing_template_preview_wrapper))",
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: "html:not(:has(.o-snippets-menu))",
        },
        ...stepUtils.saveForm(),
        {
            content: "Click on the New button to create another mailing",
            trigger: 'button.o_form_button_create',
            run: "click",
        },
        {
            trigger: ".o_mailing_template_preview_wrapper",
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
            trigger: '.o_mailing_template_preview_wrapper [data-name="newsletter"]',
            run: "click",
        },
        {
            content: "Make sure the snippets menu is displayed",
            trigger: ".o-snippets-menu",
        },
        ...stepUtils.discardForm(),
        {
            content: 'Go back to previous mailing',
            trigger: 'td[name="subject"]:contains(Test Basic Theme)',
            run: "click",
        },
        {
            content: "Make sure the snippets menu is hidden",
            trigger: "html:not(:has(.o-snippets-menu))",
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
                const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesIn(
                    this.anchor
                );
                setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
            }
        },
        {
            content: "Make sure the floating toolbar is visible",
            trigger: '.overlay:has(.o-we-toolbar)[style*="visible"]',
        },
        {
            content: "Expand Toolbar",
            trigger: ".o-we-toolbar button[name='expand_toolbar']",
            run: "click",
        },
        {
            content: "Open the color picker",
            trigger: ".o-select-color-foreground",
            run: "click",
        },
        {
            content: "Open Solid tab",
            trigger: ".btn-tab.solid-tab",
            run: "click",
        },
        {
            content: "Pick a color",
            trigger: '.o_font_color_selector button[data-color="o-color-1"]',
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
            trigger: "html:not(:has(.o-snippets-menu))",
        },
        {
            content: "Select content",
            trigger: ':iframe p:contains(content)',
            run() {
                const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesIn(
                    this.anchor
                );
                setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
            }
        },
        {
            content: "Make sure the floating toolbar is visible",
            trigger: '.overlay:has(.o-we-toolbar)[style*="visible"]',
        },
    ],
});
