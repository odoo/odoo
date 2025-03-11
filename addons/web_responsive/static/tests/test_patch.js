/* Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2025 Carlos Lopez - Tecnativa
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
odoo.define(
    "web_responsive.test_patch",
    ["@web_tour/tour_service/tour_utils", "@web/core/utils/patch"],
    function (require) {
        "use strict";

        const {stepUtils} = require("@web_tour/tour_service/tour_utils");
        const {patch} = require("@web/core/utils/patch");

        patch(stepUtils, {
            /* Make base odoo JS tests working */
            showAppsMenuItem() {
                return {
                    edition: "community",
                    trigger: "button.o_grid_apps_menu__button",
                    auto: true,
                    position: "bottom",
                };
            },
        });
    }
);
