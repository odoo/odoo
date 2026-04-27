/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("web_studio_home_menu_background_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_navbar_item",
            content: markup(
                _t("Want to customize the background? Let’s activate <b>Odoo Studio</b>.")
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_web_studio_change_background",
            content: markup(_t("Change the <b>background</b>, make it yours.")),
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});
