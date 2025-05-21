import { registry } from "@web/core/registry";
import { stepUtils } from "./tour_step_utils";

registry.category("web_tour.tours").add("test_catalog_vendor_uom", {
    steps: () => [
        // Open the PO for the vendor selling product as "Units".
        { trigger: "td[data-tooltip='PO/TEST/00002']", run: "click" },
        ...stepUtils.displayFormOptionalField("discount"),
        ...stepUtils.openCatalog(),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 2.50"),
        // Add 6 units and check the price is correctly updated.
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.checkProductUoM("Crab Juice", "Units"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.waitForQuantity("Crab Juice", 5),
        ...stepUtils.checkProductUoM("Crab Juice", "Units"),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 2.50"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 2.45"),
        // Add 6 units more and check the price is updated again.
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.waitForQuantity("Crab Juice", 11),
        ...stepUtils.checkProductUoM("Crab Juice", "Units"),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 2.45"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 2.20"),
        // Go back in the PO form view and check PO line price and qty is correct.
        { trigger: ".o-kanban-button-back", run: "click" },
        ...stepUtils.checkPurchaseOrderLineValues(0, {
            product: "Crab Juice",
            discount: "10.20",
            quantity: "12.00",
            unit: "Units",
            unitPrice: "2.45",
            totalPrice: "$ 26.40",
        }),

        // Open the PO for the vendor selling product as liter.
        { trigger: "a[href='/odoo/purchase']", run: "click" },
        { trigger: "td[data-tooltip='PO/TEST/00001']", run: "click" },
        ...stepUtils.openCatalog(),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 1.55"),
        ...stepUtils.addProduct("Crab Juice"),
        ...stepUtils.waitForQuantity("Crab Juice", 1),
        ...stepUtils.checkProductUoM("Crab Juice", "L"),
        ...stepUtils.checkProductPrice("Crab Juice", "$ 1.55"),
        // Go back in the PO form view and check PO line price and qty is correct.
        { trigger: ".o-kanban-button-back", run: "click" },
        ...stepUtils.checkPurchaseOrderLineValues(0, {
            product: "Crab Juice",
            quantity: "1.00",
            discount: "22.50",
            unit: "L",
            unitPrice: "2.00",
            totalPrice: "$ 1.55",
        }),
    ],
});
