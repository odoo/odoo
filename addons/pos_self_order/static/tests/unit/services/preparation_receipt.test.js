import { test, describe, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import {
    setupSelfPosEnv,
    getFilledSelfOrder,
    addComboProduct,
    checkKioskPreparationTicketData,
} from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

describe("preparation ticket", () => {
    test("preparation ticket check 1", async () => {
        const store = await setupSelfPosEnv();
        await getFilledSelfOrder(store);

        const result = await checkKioskPreparationTicketData(store, [
            { name: "TEST", quantity: 3 },
            { name: "TEST 2", quantity: 2 },
        ]);
        expect(result).toBe(true);
    });
    test("preparation ticket check 2 - preparation categories", async () => {
        const store = await setupSelfPosEnv();

        const product1 = store.models["product.template"].get(11); // Steel desk
        const product2 = store.models["product.template"].get(13); // Pizza margarita

        await store.addToCart(product1, 2);
        await store.addToCart(product2, 2);

        const result = await checkKioskPreparationTicketData(store, [
            { name: "Steel desk", quantity: 2 },
        ]);
        expect(result).toBe(true);
    });
    test("preparation ticket check 3 - combo", async () => {
        const store = await setupSelfPosEnv();
        await addComboProduct(store);

        const result = await checkKioskPreparationTicketData(store, [
            { name: "Product combo", quantity: 2 },
            { name: "Wood chair", quantity: 2 },
            { name: "Wood desk", quantity: 2 },
        ]);
        expect(result).toBe(true);
    });
    test("name entered for a name-required preset shows as the prep ticket order_label", async () => {
        const store = await setupSelfPosEnv();
        store.config.company_id.country_id.state_ids = [];
        store.config.company_id.country_id.phone_code = 1;
        const order = await getFilledSelfOrder(store);
        const preset = store.models["pos.preset"].get(3);
        order.preset_id = preset;

        const comp = await mountWithCleanup(PresetInfoPopup, {
            props: { close: () => {}, getPayload: () => {} },
        });
        comp.state.name = "Mitchell";
        await comp.setInformations();
        expect(store.currentOrder.floating_order_name).toBe("Mitchell");

        const categoryIds = store.config.preparationCategories;
        const generator = store.ticketPrinter.getGenerator({
            models: store.models,
            order: store.currentOrder,
        });
        const changes = generator.generatePreparationData(categoryIds, {});
        expect(changes[0].extra_data.order_label).toBe("Mitchell");
    });
});
