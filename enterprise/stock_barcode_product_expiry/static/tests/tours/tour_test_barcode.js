/** @odoo-module **/

import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add("test_delivery_package_with_expiration_dates", {
    steps: () => [
        {
            trigger: ".o_barcode_client_action",
            run: "scan SuperPackage",
        },
        {
            trigger: ".o_line_tracking_number:contains(SuperLot):contains(2024)",
        },
    ],
});
