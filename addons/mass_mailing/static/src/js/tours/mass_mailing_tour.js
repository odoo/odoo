    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_utils";
    import { _t } from "@web/core/l10n/translation";

    import { markup } from "@odoo/owl";

    registry.category("web_tour.tours").add('mass_mailing_tour', {
        steps: () => [stepUtils.showAppsMenuItem(), {
        isActive: ["enterprise"],
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        run: "click",
    }, {
        isActive: ["community"],
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        content: _t("Let's try the Email Marketing app."),
        run: "click",
    },
    {
        isActive: ["desktop"],
        trigger: ".o_mass_mailing_mailing_tree",
    },
    {
        isActive: ["mobile"],
        trigger: ".o_kanban_view",
    },
    {
        isActive: ["desktop"],
        trigger: '.o_list_button_add',
        content: markup(_t("Start by creating your first <b>Mailing</b>.")),
        run: "click",
    }, {
        isActive: ["mobile"],
        trigger: 'button.o-kanban-button-new',
        content: _t("Start by creating your first Mailing."),
        run: "click",
    }, {
        trigger: 'div[name="subject"] input',
        content: markup(_t('Pick the <b>email subject</b>.')),
        run: "edit Newsletter",
    }, {
        trigger: 'div[name="contact_list_ids"] input',
        content: _t("Pick a mailing list."),
        run: 'edit Newsletter',
    }, {
        isActive: ["desktop"],
        trigger: '.o-autocomplete--dropdown-item:contains("Newsletter")',
        content: _t("Select this mailing list."),
        run: 'click',
    }, {
        isActive: ["mobile"],
        trigger: '.modal .o_kanban_record:contains("Newsletter")',
        content: _t("Select this mailing list."),
        run: 'click',
    }, {
        trigger: 'div[name="body_arch"] :iframe .o_mail_templates_grid .dropdown-item:contains("Welcome Message")',
        content: markup(_t('Choose a <b>template</b>.')),
        tooltipPosition: 'top',
        run: 'click',
    }, {
        trigger: 'div[name="body_arch"] :iframe section:has(p)',
        content: _t('Click on this block to edit it.'),
        tooltipPosition: 'top',
        run: 'click',
    }, {
        isActive: ["desktop"],
        trigger: 'button[title="Save & Quit"]',
        content: _t("Save your changes."),
        run: 'click',
    }, {
        isActive: ["mobile"],
        trigger: '.o_form_button_save',
        content: _t("Save your changes."),
        run: 'click',
    }, {
        trigger: '.o_action_manager button[data-tooltip="Actions"]',
        content: _t('Click on the actions gear icon.'),
        run: 'click',
    },
    {
        trigger: '.o-dropdown-item.o_save_as_template',
        content: _t('Click on the "Save as Template" button to add this mailing to your templates.'),
        run: 'click',
    },
    {
        trigger: '.o_notification_content',
        content: 'Wait for the template creation to finish.'
    },
    ...stepUtils.statusbarButtonsSteps(
        "Test",
        _t("Test this mailing by sending a copy to yourself."),
    ),
    {
        trigger: 'button[name="send_mail_test"]',
        content: _t("Check the email address and click send."),
        run: "click",
    }, {
        trigger: "button.btn-close",
        content: _t("Alright, let's send this mailing"),
        run: "click",
    }, {
        trigger: 'button[name="action_launch"]',
        content: _t("Ready for take-off!"),
        run: "click",
    }, {
        trigger: '.btn-primary:contains("Send to all")',
        content: _t("Don't worry, the mailing contact we created is an internal user."),
        run: "click",
    }, {
        trigger: '.o_back_button',
        content: markup(_t("By using the <b>Breadcrumb</b>, you can navigate back to the overview.")),
        run: 'click',
    }]
});
