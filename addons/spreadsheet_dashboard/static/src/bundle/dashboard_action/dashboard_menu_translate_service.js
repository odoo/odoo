import { registry } from "@web/core/registry";
import * as spreadsheet from "@odoo/o-spreadsheet";

import { dynamicSpreadsheetTranslate } from "@spreadsheet/o_spreadsheet/translation";

const { urlRegistry } = spreadsheet.registries;

export const dashboardMenuTranslateService = {
    dependencies: ["spreadsheet_dashboard_loader", "spreadsheetLinkMenuCell"],
    start(env) {
        const dashboardLoader = env.services.spreadsheet_dashboard_loader;
        for (const key of urlRegistry.getKeys()) {
            const linkSpec = urlRegistry.get(key);

            urlRegistry.replace(key, {
                ...linkSpec,
                // Override createLink to translate the label
                createLink(url, label) {
                    const dashboard = dashboardLoader.getActiveDashboard();
                    const translatedLabel = dashboard
                        ? dynamicSpreadsheetTranslate(dashboard.translationNamespace, label)
                        : label;
                    return linkSpec.createLink(url, translatedLabel);
                },
            });
        }
    },
};

registry
    .category("services")
    .add("spreadsheet_dashboard_menu_translate", dashboardMenuTranslateService);
