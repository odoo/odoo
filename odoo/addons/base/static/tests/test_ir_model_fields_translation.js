/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
function checkLoginColumn(translation) {
    return [
        stepUtils.showAppsMenuItem(), {
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
            isCheck: true,
        }
    ]
}

registry.category("web_tour.tours").add('ir_model_fields_translation_tour', {
    test: true,
    url: '/web',
    steps: () => checkLoginColumn('Identifiant')
});

registry.category("web_tour.tours").add('ir_model_fields_translation_tour2', {
    test: true,
    url: '/web',
    steps: () => checkLoginColumn('Identifiant2')
});
