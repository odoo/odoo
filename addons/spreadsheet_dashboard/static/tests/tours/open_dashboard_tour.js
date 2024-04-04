/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("spreadsheet_dashboard_open_dashboard", {
    test: true,
    url: "/web",
    steps: () => [
        {
            trigger:
                '.o_app[data-menu-xmlid="spreadsheet_dashboard.spreadsheet_dashboard_menu_root"]',
            content: "Open dashboard app",
            run: "click",
        },
        {
            trigger: "div.o_kanban_record",
            content: "Open dashboard",
            run: "click",
        },
        {
            trigger: ".o-spreadsheet",
            content: "Dashboard is open",
        },
    ],
});
