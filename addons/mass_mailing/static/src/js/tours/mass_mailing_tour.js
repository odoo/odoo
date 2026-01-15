    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_utils";
    import { _t } from "@web/core/l10n/translation";

    import { markup } from "@odoo/owl";

    registry.category("web_tour.tours").add('mass_mailing_tour', {
        url: '/odoo',
        steps: () => [stepUtils.showAppsMenuItem(), {
        isActive: ["enterprise"],
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        isActive: ["community"],
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        run: "click",
    },
    {
        trigger: ".o_mass_mailing_mailing_tree",
    },
    {
        trigger: '.o_list_button_add',
        content: markup(_t("Start by creating your first <b>Mailing</b>.")),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: 'div[name="subject"]',
        content: markup(_t('Pick the <b>email subject</b>.')),
        tooltipPosition: 'bottom',
        run: 'click',
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
        trigger: 'div[name="body_arch"] .o_mailing_template_preview_wrapper [data-name="newsletter"]',
        content: markup(_t('Choose this <b>theme</b>.')),
        tooltipPosition: 'left',
        run: 'click',
    }, {
        isActive: ["community"],
        trigger: 'div[name="body_arch"] .o_mailing_template_preview_wrapper [data-name="default"]',
        content: markup(_t('Choose this <b>theme</b>.')),
        tooltipPosition: 'right',
        run: 'click',
    }, {
        isActive: ["enterprise"],
        trigger: 'div[name="body_arch"] :iframe div.theme_selection_done div.s_text_block',
        content: _t('Click on this paragraph to edit it.'),
        tooltipPosition: 'top',
        run: 'click',
    }, {
        isActive: ["community"],
        trigger: 'div[name="body_arch"] :iframe div.o_mail_block_title_text',
        content: _t('Click on this paragraph to edit it.'),
        tooltipPosition: 'top',
        run: 'click',
    }, {
        trigger: 'button[name="action_set_favorite"]',
        content: _t('Click on this button to add this mailing to your templates.'),
        tooltipPosition: 'bottom',
        run: 'click',
    }, {
        trigger: 'button[name="action_test"]',
        content: _t("Test this mailing by sending a copy to yourself."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: 'button[name="send_mail_test"]',
        content: _t("Check the email address and click send."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: 'button[name="action_launch"]',
        content: _t("Ready for take-off!"),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: '.btn-primary:contains("Send to all")',
        content: _t("Don't worry, the mailing contact we created is an internal user."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: '.o_back_button',
        content: markup(_t("By using the <b>Breadcrumb</b>, you can navigate back to the overview.")),
        tooltipPosition: 'bottom',
        run: 'click',
    }]
});
