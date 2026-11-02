import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Approval Center Tour
 *
 * Walks the administrator through the generic approval engine:
 *  1. Open Approval Sources (Settings > Approval Center)
 *  2. Declare the source model and the approval strategy
 *  3. Build the approval ladder on the Steps tab
 */
registry.category("web_tour.tours").add("od19_approval_center_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "base.menu_administration",
            markup(_t("Let's configure an <b>approval ladder</b> in the Approval Center."))
        ),
        {
            trigger: navSection("Approval Center"),
            content: markup(_t("Open the <b>Approval Center</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Approval Sources"),
            content: markup(_t(
                "Open <b>Approval Sources</b>: one record per document that " +
                "needs an approval ladder."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Approval Sources"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line declares the approval ladder of one model."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to register an approval source.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t(
                "Give the source a readable <b>name</b>, e.g. Purchase Approval (Tour)."
            )),
            run: "edit Purchase Approval (Tour)",
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            content: markup(_t(
                "Pick the <b>model</b> whose records follow this approval ladder."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='strategy']",
            content: markup(_t(
                "Choose the <b>strategy</b>: a simple state <i>field</i> or the " +
                "full <i>tier validation</i> engine."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='step_ids']",
            content: markup(_t(
                "On the <b>Steps</b> tab add one line per approval level. Each step " +
                "binds a <b>state value</b> (e.g. <i>waiting_approval</i>) to the " +
                "<b>approver kind</b> allowed to move the record forward."
            )),
            tooltipPosition: "top",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Approval Center tour complete! The ladder is reused from any document " +
                "form that declares the source."
            )),
            run: "click",
        },
    ],
});
