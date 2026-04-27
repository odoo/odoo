/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("frontdesk_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="frontdesk.frontdesk_menu_root"]',
            content: _t(
                "Looking for a better way to manage your visitors? \n It begins right here."
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: '.dropdown-item[data-menu-xmlid="frontdesk.frontdesk_menu_visitors"]',
            content: _t("Here, you'll see list of all the visitors."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: _t("Let's add a new visitor."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: _t("Enter the visitor's name."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='station_id'] .o_field_many2one_selection",
            content: _t("Select or create a station on the fly from where the visitor arrived."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            content: _t("Save the visitor."),
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});
