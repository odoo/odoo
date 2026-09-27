import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("spreadsheet_share_dashboard_public", {
    steps: () => [
        {
            trigger: ".o-spreadsheet",
            content: "spreadsheet is loaded",
        },
    ],
});
