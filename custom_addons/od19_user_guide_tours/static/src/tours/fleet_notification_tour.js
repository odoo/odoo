import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Fleet Notification Tour
 *
 * Walks the user through setting the Insurance and Act (tax) expiry
 * dates on a vehicle and configuring the reminder lead times.
 */
registry.category("web_tour.tours").add("od19_fleet_notification_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "fleet.menu_root",
            markup(_t("Let's configure <b>Insurance</b> and <b>Act (Tax)</b> expiry reminders for a vehicle."))
        ),

        {
            trigger: ".o_switch_view.o_list",
            content: markup(_t(
                "Switch to the <b>list view</b>. An empty database shows read-only sample " +
                "kanban cards, so we create a fresh vehicle to edit its expiry dates."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Create a new vehicle.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            content: markup(_t("Select the vehicle <b>Model</b> (the only required field).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='model_id'] .o-autocomplete--dropdown-menu a.dropdown-item:not(.o_loading)",
            content: _t("Pick the model from the suggestion list."),
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: "a.nav-link:contains('Insurance & Act')",
            content: markup(_t("Open the <b>Insurance &amp; Act</b> tab.")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_insurance_expire_date'] input",
            content: markup(_t(
                "Set the <b>Insurance Expire Date</b> (ประกัน). A reminder is scheduled before it expires."
            )),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_insurance_reminder_days'] input",
            content: markup(_t(
                "Set the <b>Insurance Reminder Days</b> (how many days in advance to be notified)."
            )),
            run: "edit 30",
        },
        {
            trigger: ".o_field_widget[name='od19_act_expire_date'] input",
            content: markup(_t("Set the <b>Act (Tax) Expire Date</b> (ภาษี).")),
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_act_reminder_days'] input",
            content: markup(_t(
                "Set the <b>Act Reminder Days</b>. The system notifies the responsible users " +
                "before both the insurance and the tax expire."
            )),
            run: "edit 15",
        },
        ...stepUtils.saveForm(),
        ...stepUtils.discardForm(),

        {
            trigger: ".o_kanban_view, .o_list_view",
            content: markup(_t(
                "Fleet Notification complete! Insurance and Act expiry dates are tracked with " +
                "configurable reminder lead times so renewals are never missed."
            )),
            run: "click",
        },
    ],
});
