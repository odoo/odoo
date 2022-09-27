odoo.define('mass_mailing.mass_mailing_editor_tour', function (require) {
    "use strict";

    var tour = require('web_tour.tour');

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
        trigger: 'li.ui-menu-item',
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
        trigger: 'input[name="subject"]',
        run: 'text Test',
    }, {
        trigger: '.o_form_view', // blur previous input
    },
    ...tour.stepUtils.saveForm(),
    {
        trigger: 'iframe .o_editable',
        run: () => {},
    }]);
});
