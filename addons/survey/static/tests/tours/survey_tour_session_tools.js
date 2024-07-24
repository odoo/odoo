/** @odoo-module **/

import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * Tool that gathers common steps to every 'survey session' tours.
 */
export const accessSurveysteps = [
    stepUtils.showAppsMenuItem(),
    {
        isActive: ["community"],
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        run: "click",
    },
    {
        isActive: ["enterprise"],
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        run: "click",
    },
    {
        trigger: '.o_kanban_record:contains("User Session Survey")',
        run: "click",
    },
];
