/** @odoo-module **/

"use strict";

import tour from "web_tour.tour";

function checkLoginColumn(translation) {
    return [
        tour.stepUtils.showAppsMenuItem(), {
            content: "Settings",
            trigger: 'a[data-menu-xmlid="base.menu_administration"]',
            run: 'click',
        }, {
            content: "Open Users & Companies",
            trigger: '[data-menu-xmlid="base.menu_users"]',
            run: "click",
        }, {
            content: "Open Users",
            trigger: '[data-menu-xmlid="base.menu_action_res_users"]',
            run: "click",
        }, {
            content: `Login column should be ${translation}`,
            trigger: `[data-name="login"] span:contains("${translation}")`,
        }
    ]
}

tour.register('ir_model_fields_translation_en_tour', {
    test: true,
    url: '/web',
}, checkLoginColumn('Login'));

tour.register('ir_model_fields_translation_en_tour2', {
    test: true,
    url: '/web',
}, checkLoginColumn('Login2'));

tour.register('ir_model_fields_translation_fr_tour', {
    test: true,
    url: '/web',
}, checkLoginColumn('Identifiant'));

tour.register('ir_model_fields_translation_fr_tour2', {
    test: true,
    url: '/web',
}, checkLoginColumn('Identifiant2'));
