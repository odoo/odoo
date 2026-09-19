import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
import { productCatalog, purchaseForm } from "./tour_helper";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_add_section_from_product_catalog_on_purchase_order", {
    steps: () => [
        ...purchaseForm.createNewPO(),
        ...purchaseForm.selectVendor("Test Vendor"),
        ...addSectionFromProductCatalog(),
    ],
});

registry.category("web_tour.tours").add("test_catalog_vendor_uom", {
    steps: () => [
        // Open the PO for the vendor selling product as "Units".
        { trigger: ".o_data_cell:text(PO/TEST/00002)", run: "click" },
        ...purchaseForm.displayOptionalField("discount"),
        ...purchaseForm.openCatalog(),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 2.50"),
        // Add 6 units and check the price is correctly updated.
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.checkProductUoM("Crab Juice", "Units"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.waitForQuantity("Crab Juice", 5),
        ...productCatalog.checkProductUoM("Crab Juice", "Units"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 2.50"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 2.45"),
        // Add 6 units more and check the price is updated again.
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.waitForQuantity("Crab Juice", 11),
        ...productCatalog.checkProductUoM("Crab Juice", "Units"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 2.45"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 2.20"),
        // Go back in the PO form view and check PO line price and qty is correct.
        ...productCatalog.goBackToOrder(),
        ...purchaseForm.checkLineValues(0, {
            product: "Crab Juice",
            discount: "10.20",
            quantity: "12.00",
            unit: "Units",
            unitPrice: "2.45",
            totalPrice: "$ 26.40",
        }),

        // Open the PO for the vendor selling product as liter.
<<<<<<< 423770de9c5da4ca862e9e972c0caf8fa3f1a886
        { trigger: "a[href='/odoo/purchase']", run: "click" },
        { trigger: ".o_data_cell:text(PO/TEST/00001)", run: "click" },
||||||| cd826c81964566d831d200059e62bb7dfe88d088
        { trigger: "a[href='/odoo/purchase']", run: "click" },
        { trigger: "td[data-tooltip='PO/TEST/00001']", run: "click" },
=======
        { trigger: "li.o_back_button:first-child", run: "click" },
        { trigger: "td[data-tooltip='PO/TEST/00001']", run: "click" },
>>>>>>> b21be1b717fb6c929961e09cfd18e3c3545124d4
        ...purchaseForm.openCatalog(),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 1.55"),
        ...productCatalog.addProduct("Crab Juice"),
        ...productCatalog.waitForQuantity("Crab Juice", 1),
        ...productCatalog.checkProductUoM("Crab Juice", "L"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 1.55"),
        // Go back in the PO form view and check PO line price and qty is correct.
        ...productCatalog.goBackToOrder(),
        ...purchaseForm.checkLineValues(0, {
            product: "Crab Juice",
            quantity: "1.00",
            discount: "22.50",
            unit: "L",
            unitPrice: "2.00",
            totalPrice: "$ 1.55",
        }),

        // Reopen the PO for `vendor_by_liter` and verify that the price is updated based on the UoM change.
        { trigger: "li.o_back_button:first-child", run: "click" },
        { trigger: ".o_data_cell:text(PO/TEST/00001)", run: "click" },
        ...purchaseForm.openCatalog(),
        ...productCatalog.checkProductUoM("Crab Juice", "L"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 1.55"),
        ...productCatalog.selectProductUoM("Crab Juice", "Units"),
        ...productCatalog.checkProductUoM("Crab Juice", "Units"),
        ...productCatalog.checkProductPrice("Crab Juice", "$ 3.00"),
    ],
});
