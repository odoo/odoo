/** @odoo-module **/

import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * Tool that gathers common steps to every 'survey session' tours.
 */
export const accessSurveysteps = [
    stepUtils.showAppsMenuItem(),
    {
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        edition: "community",
    },
    {
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        edition: "enterprise",
    },
    {
        trigger: '.oe_kanban_card:contains("User Session Survey")',
    },
];
