/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("project_milestone_sale_quote_tour", {
    steps: () => [
        {
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            extra_trigger: ".o_sale_order",
            content: _t("Write a company name to create one, or see suggestions."),
            position: "right",
            run: function (actions) {
                actions.text("partner_a", this.$anchor);
            },
        },
        {
            trigger: `.ui-menu-item > a:contains("partner_a")`,
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            content: _t("Click here to add some products or services to your quotation."),
            position: "bottom",
        },
        {
            trigger: ".o_field_widget[name='product_template_id'] input",
            content: _t("Select a product, or create a new one on the fly."),
            position: "down",
            run: function (actions) {
                actions.text("Service Based on Milestones", this.$anchor);
            },
        },
        {
            trigger: `.ui-menu-item > a:contains("Service Based on Milestones")`,
            run: "click",
        },
        // additional step to ensure the order line was properly updated (description)
        {
            trigger: ".o_selected_row > td[name='name'][data-tooltip='Service Based on Milestones']",
            content: _t("Wait for the line to be displayed"),
        },
        ...stepUtils.statusbarButtonsSteps(
            'Confirm',
            _t("Confirm quotation"),
            ".o_statusbar_status .o_arrow_button_current:contains('Sales Order')"
        ),
        {
            trigger: ".o_form_readonly, .o_form_saved",
            content: _t("Wait for save completion"),
        },
    ],
});
