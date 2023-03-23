odoo.define('mass_mailing.mass_mailing_editor_tour', function (require) {
    "use strict";

    var tour = require('web_tour.tour');
    const { boundariesIn, setSelection } = require('@web_editor/js/editor/odoo-editor/src/utils/utils');

    tour.register('mass_mailing_editor_tour', {
        url: '/web',
        test: true,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    }, {
        trigger: 'button.o_list_button_add',
    }, {
        trigger: 'div[name="contact_list_ids"] .o_input_dropdown input[type="text"]',
    }, {
        trigger: 'div[name="contact_list_ids"] .ui-state-active'
    }, {
        content: 'choose the theme "empty" to edit the mailing with snippets',
        trigger: '[name="body_arch"] iframe #empty',
    }, {
        content: 'wait for the editor to be rendered',
        trigger: '[name="body_arch"] iframe .o_editable[data-editor-message="DRAG BUILDING BLOCKS HERE"]',
        run: () => {},
    }, {
        content: 'drag the "Title" snippet from the design panel and drop it in the editor',
        trigger: '[name="body_arch"] iframe #email_designer_default_body [name="Title"] .ui-draggable-handle',
        run: function (actions) {
            actions.drag_and_drop('[name="body_arch"] iframe .o_editable', this.$anchor);
        }
    }, {
        content: 'wait for the snippet menu to finish the drop process',
        trigger: '[name="body_arch"] iframe #email_designer_header_elements:not(:has(.o_we_already_dragging))',
        run: () => {}
    }, {
        content: 'verify that the title was inserted properly in the editor',
        trigger: '[name="body_arch"] iframe .o_editable h1',
        run: () => {},
    }, {
        trigger: 'button.o_form_button_save',
    }, {
        content: 'verify that the save failed (since the field "subject" was not set and it is required)',
        trigger: 'label.o_field_invalid',
        run: () => {},
    }, {
        content: 'verify that the edited mailing body was not lost during the failed save',
        trigger: '[name="body_arch"] iframe .o_editable h1',
        run: () => {},
    }, {
        trigger: 'input#subject',
        run: 'text Test',
    }, {
        trigger: '.o_form_view', // blur previous input
    },
    ...tour.stepUtils.saveForm(),
    {
        trigger: 'iframe .o_editable',
        run: () => {},
    }]);

    tour.register('mass_mailing_basic_theme_toolbar', {
        test: true,
        url: '/web',
    }, [
        tour.stepUtils.showAppsMenuItem(),
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
            trigger: '#subject',
            run: 'text Test',
        },
        {
            content: "Fill in Mailing list",
            trigger: '#contact_list_ids',
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
            trigger: 'td:contains(Test)',
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
        ...tour.stepUtils.discardForm(),
    ]);

    tour.register('mass_mailing_campaing_new_mailing', {
        url: '/web',
        test: true,
    }, [
        tour.stepUtils.showAppsMenuItem(),
        {
            content: 'Select the "Email Marketing" app',
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        },
        {
            content: 'Select "Campaings" Navbar item',
            trigger: '.o_nav_entry[data-menu-xmlid="mass_mailing.menu_email_campaigns"]',
        },
        {
            content: 'Select "Newsletter" campaign',
            trigger: '.oe_kanban_card:contains("Newsletter")',
        },
        {
            content: 'Add a line (create new mailing)',
            trigger: '.o_field_x2many_list_row_add a',
        },
        {
            content: 'Pick the basic theme',
            trigger: 'iframe',
            run(actions) {
                // For some reason the selectors inside the iframe cannot be triggered.
                const link = this.$anchor[0].contentDocument.querySelector('#basic');
                actions.click(link);
            }
        },
        {
            content: 'Fill in Subject',
            trigger: '#subject',
            run: 'text Test',
        },
        {
            content: 'Fill in Mailing list',
            trigger: '#contact_list_ids',
            run: 'text Newsletter',
        },
        {
            content: 'Pick "Newsletter" option',
            trigger: '.o_input_dropdown a:contains(Newsletter)',
        },
        {
            content: 'Save form',
            trigger: '.o_form_button_save',
        },
        {
            content: 'Check that newly created record is on the list',
            trigger: '[name="mailing_mail_ids"] td[name="subject"]:contains("Test")',
            run: () => null,
        },
        ...tour.stepUtils.saveForm(),
    ]);
});
