/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";
    import { _t } from "@web/core/l10n/translation";

    import { markup } from "@odoo/owl";

    const { DateTime } = luxon;

    registry.category("web_tour.tours").add('mass_mailing_tour', {
        url: '/web',
        rainbowManMessage: _t('Congratulations, I love your first mailing. :)'),
        sequence: 200,
        steps: () => [stepUtils.showAppsMenuItem(), {
        isActive: ["enterprise"],
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        position: 'bottom',
        run: "click",
    }, {
        isActive: ["community"],
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        run: "click",
    },
    {
        isActive: ["auto"],
        trigger: ".o_mass_mailing_mailing_tree",
    },
    {
        trigger: '.o_list_button_add',
        content: markup(_t("Start by creating your first <b>Mailing</b>.")),
        position: 'bottom',
        run: "click",
    }, {
        trigger: 'input[name="subject"]',
        content: markup(_t('Pick the <b>email subject</b>.')),
        position: 'bottom',
        run: `edit ${DateTime.now().toFormat("LLLL")} Newsletter`,
    }, {
        isActive: ["auto"],
        trigger: 'div[name="contact_list_ids"] > .o_input_dropdown > input[type="text"]',
        run: 'click',
    }, {
        isActive: ["auto"],
        trigger: 'li.ui-menu-item',
        run: 'click',
    }, {
        isActive: ["enterprise"],
        trigger: 'div[name="body_arch"] :iframe #newsletter',
        content: markup(_t('Choose this <b>theme</b>.')),
        position: 'left',
        run: 'click',
    }, {
        isActive: ["community"],
        trigger: 'div[name="body_arch"] :iframe #default',
        content: markup(_t('Choose this <b>theme</b>.')),
        position: 'right',
        run: 'click',
    }, {
        isActive: ["enterprise"],
        trigger: 'div[name="body_arch"] :iframe div.s_text_block',
        content: _t('Click on this paragraph to edit it.'),
        position: 'top',
        run: 'click',
    }, {
        isActive: ["community"],
        trigger: 'div[name="body_arch"] :iframe div.o_mail_block_title_text',
        content: _t('Click on this paragraph to edit it.'),
        position: 'top',
        run: 'click',
    }, {
        trigger: 'button[name="action_set_favorite"]',
        content: _t('Click on this button to add this mailing to your templates.'),
        position: 'bottom',
        run: 'click',
    }, {
        trigger: 'button[name="action_test"]',
        content: _t("Test this mailing by sending a copy to yourself."),
        position: 'bottom',
        run: "click",
    }, {
        trigger: 'button[name="send_mail_test"]',
        content: _t("Check the email address and click send."),
        position: 'bottom',
        run: "click",
    }, {
        trigger: 'button[name="action_launch"]',
        content: _t("Ready for take-off!"),
        position: 'bottom',
        run: "click",
    }, {
        trigger: '.btn-primary:contains("Ok")',
        content: _t("Don't worry, the mailing contact we created is an internal user."),
        position: 'bottom',
        run: "click",
    }, {
        trigger: '.o_back_button',
        content: markup(_t("By using the <b>Breadcrumb</b>, you can navigate back to the overview.")),
        position: 'bottom',
        run: 'click',
    }]
});
