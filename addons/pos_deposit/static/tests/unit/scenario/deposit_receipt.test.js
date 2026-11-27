import { test } from "@odoo/hoot";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { renderReceipt, expectTicketData } from "@point_of_sale/../tests/unit/receipt_utils";

definePosModels();

test("receipt prints each deposit under its own line", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, module_pos_deposit: true });
    const template = (id) => store.models["product.template"].get(id);
    const comboItem = (id) => store.models["product.combo.item"].get(id);
    await store.addLineToCurrentOrder({ product_tmpl_id: template(5) });
    await store.addLineToCurrentOrder({
        product_tmpl_id: template(7),
        payload: [
            [
                { combo_item_id: comboItem(1), qty: 1 },
                { combo_item_id: comboItem(4), qty: 1 },
            ],
            [],
        ],
    });

    const { ticket } = renderReceipt(store, store.getOrder());

    expectTicketData(ticket, {
        orderlines: [
            { name: "TEST" },
            {
                name: "Deposit",
                quantity: "1",
                line_price: "$ 1.00",
                cssRules: [{ css: ".deposit-indent.w-5", length: 1 }],
            },
            { name: "Product combo" },
            { name: "Wood chair" },
            { name: "Deposit", cssRules: [{ css: ".deposit-indent.w-10", length: 1 }] },
            { name: "Steel desk" },
            { name: "Deposit", cssRules: [{ css: ".deposit-indent.w-5", length: 1 }] },
        ],
    });
});
