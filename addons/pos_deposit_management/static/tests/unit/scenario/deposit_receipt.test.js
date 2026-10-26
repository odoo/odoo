import { test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { setupAndMountPosApp, createComboSetup } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { renderReceipt, expectTicketData } from "@point_of_sale/../tests/unit/receipt_utils";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";
import { createDeposit } from "@pos_deposit_management/../tests/unit/utils";

definePosModels();

test("receipt prints each combo deposit, under its own line", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    const { template: comboTmpl, products } = createComboSetup(store, {
        id: 9200,
        name: "Office Combo",
        price: 30,
        combos: [
            {
                name: "Combo 1",
                items: [{ name: "Combo Product 2", price: 11 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    products.find(
        ({ template }) => template.name === "Combo Product 2"
    ).template.deposit_product_id = createDeposit(store, {
        id: 9211,
        name: "Child Deposit",
        price: 1,
    });
    comboTmpl.deposit_product_id = createDeposit(store, {
        id: 9221,
        name: "Parent Deposit",
        price: 2,
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await animationFrame();

    const { ticket } = renderReceipt(store, store.getOrder());

    expectTicketData(ticket, {
        orderlines: [
            { name: "Office Combo", quantity: "1" },
            { name: "Combo Product 2", cssRules: [{ css: ".combo-child-qty", length: 1 }] },
            {
                name: "Child Deposit",
                line_price: "$ 1.00",
                cssRules: [{ css: ".combo-child-qty", length: 1 }],
            },
            { name: "Combo Product 4", cssRules: [{ css: ".combo-child-qty", length: 1 }] },
            {
                name: "Parent Deposit",
                quantity: "1",
                line_price: "$ 2.00",
                cssRules: [{ css: ".qty", length: 1 }],
            },
        ],
    });
});
