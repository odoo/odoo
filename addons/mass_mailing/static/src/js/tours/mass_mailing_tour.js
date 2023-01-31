odoo.define('mass_mailing.mass_mailing_tour', function (require) {
    "use strict";

    const {_t} = require('web.core');
    const {Markup} = require('web.utils');
    var tour = require('web_tour.tour');
    var now = moment();

    tour.register('mass_mailing_tour', {
        url: '/web',
        rainbowManMessage: _t('Congratulations, I love your first mailing. :)'),
        sequence: 200,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        width: 225,
        position: 'bottom',
        edition: 'enterprise',
    }, {
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        edition: 'community',
    }, {
        trigger: '.o_list_button_add',
        extra_trigger: '.o_mass_mailing_mailing_tree',
        content: Markup(_t("Start by creating your first <b>Mailing</b>.")),
        position: 'bottom',
    }, {
        trigger: 'input[name="subject"]',
        content: Markup(_t('Pick the <b>email subject</b>.')),
        position: 'bottom',
        run: 'text ' + now.format("MMMM") + " Newsletter",
    }, {
        trigger: 'div[name="contact_list_ids"] > .o_input_dropdown > input[type="text"]',
        run: 'click',
        auto: true,
    }, {
        trigger: 'li.ui-menu-item',
        run: 'click',
        auto: true,
    }, {
        trigger: 'div[name="body_arch"] iframe #newsletter',
        content: Markup(_t('Choose this <b>theme</b>.')),
        position: 'left',
        edition: 'enterprise',
        run: 'click',
    }, {
        trigger: 'div[name="body_arch"] iframe #default',
        content: Markup(_t('Choose this <b>theme</b>.')),
        position: 'right',
        edition: 'community',
        run: 'click',
    }, {
        trigger: 'div[name="body_arch"] iframe div.s_text_block',
        content: _t('Click on this paragraph to edit it.'),
        position: 'top',
        edition: 'enterprise',
        run: 'click',
    }, {
        trigger: 'div[name="body_arch"] iframe div.o_mail_block_title_text',
        content: _t('Click on this paragraph to edit it.'),
        position: 'top',
        edition: 'community',
        run: 'click',
    }, {
        trigger: 'button[name="action_test"]',
        content: _t("Test this mailing by sending a copy to yourself."),
        position: 'bottom',
    }, {
        trigger: 'button[name="send_mail_test"]',
        content: _t("Check the email address and click send."),
        position: 'bottom',
    }, {
        trigger: 'button[name="action_launch"]',
        content: _t("Ready for take-off!"),
        position: 'bottom',
    }, {
        trigger: '.btn-primary:contains("Ok")',
        content: _t("Don't worry, the mailing contact we created is an internal user."),
        position: 'bottom',
        run: "click",
    }, {
        trigger: '.o_back_button',
        content: Markup(_t("By using the <b>Breadcrumb</b>, you can navigate back to the overview.")),
        position: 'bottom',
        run: 'click',
    }]
    );
});
