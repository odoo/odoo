/** @odoo-module */

import { _t } from "web.core";
import "web.legacy_tranlations_loaded";
import { Markup } from "web.utils";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/js/tour_step_utils";

registry.category("web_tour.tours").add(
    "point_of_sale_tour",
    {
        url: "/web",
        rainbowMan: false,
        sequence: 45,
        steps: [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
            content: Markup(_t("Ready to launch your <b>point of sale</b>?")),
            width: 215,
            position: "right",
            edition: "community",
        },
        {
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
            content: Markup(_t("Ready to launch your <b>point of sale</b>?")),
            width: 215,
            position: "bottom",
            edition: "enterprise",
        },
        {
            trigger: ".o_pos_kanban button.oe_kanban_action_button",
            content: Markup(
                _t(
                    "<p>Ready to have a look at the <b>POS Interface</b>? Let's start our first session.</p>"
                )
            ),
            position: "bottom",
        },
    ]
});
