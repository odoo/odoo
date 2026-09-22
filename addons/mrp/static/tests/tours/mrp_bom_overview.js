/** @odoo-module native */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mrp_bom_overview_tour", {
    steps: () => [
        {
            content: "The overview opens on the BoM's first variant",
            trigger:
                ".account_report .line_name:contains('[alpaca] Product Test Sync (L)')",
        },
        {
            content: "Open the variant filter",
            trigger: "#filter_bom_overview_variant button",
            run: "click",
        },
        {
            content: "Pick the other variant",
            trigger:
                ".o-dropdown--menu .dropdown-item:contains('[zebra] Product Test Sync (S)')",
            run: "click",
        },
        {
            content: "The report is rebuilt on it",
            trigger:
                ".account_report .line_name:contains('[zebra] Product Test Sync (S)')",
        },
    ],
});
