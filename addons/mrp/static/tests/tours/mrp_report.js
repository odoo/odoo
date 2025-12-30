/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mrp_bom_report_tour", {
    steps: () => [
        {
            content: "Check the current displayed variant",
            trigger: ".o_mrp_bom_report_page h2 a:contains('[alpaca] Product Test Sync (L)')",
            run: () => {},
        },
        {
            content: "Open dropdown menu",
            trigger: ".o-autocomplete--input",
            run: "click",
        },
        {
            content: "Select the other variant",
            trigger: ".o-autocomplete--dropdown-menu.show li.o-autocomplete--dropdown-item:eq(1)",
            run: "click",
        },
        {
            content: "Ensure the second variant is displayed",
            trigger: ".o_mrp_bom_report_page h2 a:contains('[zebra] Product Test Sync (S)')",
            run: () => {},
        },
    ],
});
