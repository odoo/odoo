/* Copyright 2021 ITerra - Sergey Shebanin
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
odoo.define("web_responsive.test_patch", function (require) {
    "use strict";

    const utils = require("web_tour.TourStepUtils");

    /* Make base odoo JS tests working */
    utils.include({
        showAppsMenuItem() {
            return {
                edition: "community",
                trigger: ".o_navbar_apps_menu",
                auto: true,
                position: "bottom",
            };
        },
    });
});
