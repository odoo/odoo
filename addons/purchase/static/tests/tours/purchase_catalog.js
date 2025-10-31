import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
import { purchaseForm } from "./tour_helper";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_add_section_from_product_catalog_on_purchase_order', {
    steps: () => [
        ...purchaseForm.createNewPO(),
        ...purchaseForm.selectVendor("Test Vendor"),
        ...addSectionFromProductCatalog(),
    ],
});
