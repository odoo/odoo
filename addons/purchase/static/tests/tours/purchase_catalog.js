import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
import { selectPOVendor } from "./tour_helper";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_add_section_from_product_catalog_on_purchase_order', {
    steps: () => [
        {
            content: "Create a new PO",
            trigger: '.o_list_button_add',
            run: 'click',
        },
        ...selectPOVendor("Test Vendor"),
        ...addSectionFromProductCatalog(),
    ],
});
