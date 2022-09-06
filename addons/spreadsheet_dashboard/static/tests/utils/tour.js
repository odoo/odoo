/** @odoo-module */

import tour from "web_tour.tour";

/**
 * @param {string} tourName
 * @param {string} dashboardDisplayName
 */
export function registerDashboardTour(tourName, dashboardDisplayName) {
    tour.register(
        tourName,
        {
            test: true,
            url: "/web",
        },
        [
            ...tour.stepUtils.goToAppSteps(
                "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
                "Open dashboard app"
            ),
            {
                trigger: `.o_search_panel li[data-name="${dashboardDisplayName}"]`,
                content: `click ${dashboardDisplayName} dashboard`,
                run: "click",
            },
            {
                trigger: ".o-spreadsheet",
                content: "dashboard is displayed",
            },
        ]
    );
}
