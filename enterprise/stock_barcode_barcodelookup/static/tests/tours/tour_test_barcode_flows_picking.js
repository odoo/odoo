/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@stock_barcode/../tests/tours/tour_step_utils";

registry.category("web_tour.tours").add("test_create_product_from_barcode_lookup", {
    steps: () => [
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan WHIN",
        },
        // Scan a valid barcode lookup that does not correspond to an existing product.
        {
            trigger: ".o_barcode_client_action",
            run: "scan 510002952387",
        },
        {
            trigger: ".o_notification .o_notification_buttons button:contains(New Product)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=name] .o_input",
            run: "edit Lovely Product",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        { trigger: ".o_notification_content:contains(Product created successfully)" },
        ...stepUtils.validateBarcodeOperation(".o_barcode_line"),
    ],
});
