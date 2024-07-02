import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("point_of_sale_tour", {
    url: "/web",
    rainbowMan: false,
    sequence: 45,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            isActive: ["community"],
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
            content: markup(_t("Ready to launch your <b>point of sale</b>?")),
            position: "right",
            run: "click",
        },
        {
            isActive: ["enterprise"],
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
            content: markup(_t("Ready to launch your <b>point of sale</b>?")),
            position: "bottom",
            run: "click",
        },
        {
            trigger: ".o_pos_kanban",
            position: "bottom",
            run: "click",
        },
    ],
});
