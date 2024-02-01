odoo.define('mass_mailing.mass_mailing_undo_icon_to_image_change', function (require) {
    "use strict";

    var tour = require('web_tour.tour');

    tour.register('mass_mailing_undo_icon_to_image_change', {
        url: '/web',
        test: true,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    }, {
        trigger: 'button.o_list_button_add',
    }, {
        trigger: 'div[name="contact_list_ids"] .o_input_dropdown > input[type="text"]',
    }, {
        trigger: 'li.ui-menu-item',
    }, {
        content: 'choose the theme "empty" to edit the mailing with snippets',
        trigger: '[name="body_arch"] iframe #empty',
    }, {
        content: 'wait for the editor to be rendered',
        trigger: '[name="body_arch"] iframe .o_editable',
        run: () => { },
    }, {
        content: 'drag the "Features" snippet from the design panel and drop it in the editor',
        trigger: '[name="body_arch"] iframe #email_designer_default_body [name="Features"] .ui-draggable-handle',
        run: function (actions) {
            actions.drag_and_drop('[name="body_arch"] iframe .o_editable', this.$anchor);
        }
    }, {
        content: 'select and click the gear icon',
        trigger: '[name="body_arch"] iframe .o_editable .fa-gear',
        run: function (actions) {
            const document = this.$anchor[0].ownerDocument;
            const range = document.createRange();
            range.selectNodeContents(this.$anchor[0]);
            const sel = document.defaultView.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            actions.click();
        },
    }, {
        content: 'replace media',
        trigger: '[name="body_arch"] iframe we-button:contains("Replace")',
        run: 'click'
    }, {
        content: 'check that the modal is open',
        trigger: '.modal-dialog',
        run: () => { },
    }, {
        content: 'click on image tab',
        trigger: '.modal-dialog a[aria-controls="editor-media-image"]',
    }, {
        content: 'choose an image',
        trigger: '.modal-dialog .o_existing_attachment_cell img',
    }, {
        content: 'verify that icon has been changed',
        trigger: '[name="body_arch"] iframe .o_editable img[data-original-id]',
        run: () => { },
    }, {
        content: 'select and click the image',
        trigger: '[name="body_arch"] iframe .o_editable img[data-original-id]',
        run: function (actions) {
            const document = this.$anchor[0].ownerDocument;
            const range = document.createRange();
            range.selectNodeContents(this.$anchor[0]);
            const sel = document.defaultView.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            actions.click();
        },
    }, {
        content: 'verify that image is fully loaded',
        trigger: '[name="body_arch"] iframe we-title:contains("Image")',
        run: () => { },
    }, {
        content: 'click undo',
        trigger: '[name="body_arch"] iframe .o_we_external_history_buttons button[data-action="undo"]',
        run: 'click',
    }, {
        content: 'Check that the change is reverted and now we have the icon back',
        trigger: '[name="body_arch"] iframe .o_editable .fa-gear',
        run: () => { },
    },
    ]);
});
