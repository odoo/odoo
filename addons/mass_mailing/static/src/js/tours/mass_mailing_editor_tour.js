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
        trigger: 'input[name="subject"]',
        run: 'text Test',
    }, {
        trigger: 'div[name="contact_list_ids"] .o_input_dropdown > input[type="text"]',
    }, {
        trigger: 'li.ui-menu-item',
    }, {
        trigger: 'iframe #default',
        run: () => $('iframe').contents().find('o_editable').html('<p><br/></p>'),
    }, {
        trigger: 'button.o_form_button_save',
    }, {
        trigger: 'iframe.o_readonly',
    }]);
});
