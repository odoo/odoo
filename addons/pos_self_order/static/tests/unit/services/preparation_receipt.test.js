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

    test("delivery preset shows name, address, phone and email", async () => {
        const store = await setupSelfPosEnv("kiosk");
        store.config.company_id.country_id.state_ids = [];
        store.config.company_id.country_id.phone_code = 1;
        const order = await getFilledSelfOrder(store);
        const preset = store.models["pos.preset"].get(1);
        preset.identification = "address";
        order.preset_id = preset;

        const comp = await mountWithCleanup(PresetInfoPopup, {
            props: { close: () => {}, getPayload: () => {} },
        });
        comp.state.name = "Robin";
        comp.state.email = "robin@example.com";
        comp.state.phoneLocal = "2025551234";
        comp.state.street = "21, Wonderfull Street";
        comp.state.city = "Vice City";
        comp.state.zip = "000021";
        await comp.setInformations();
        // Mirrors what cart_page.js does once the popup closes.
        store.currentOrder.email = store.currentOrder.partner_id.email;
        store.currentOrder.mobile = comp.getFullPhone();

        const categoryIds = store.config.preparationCategories;
        const generator = store.ticketPrinter.getGenerator({
            models: store.models,
            order: store.currentOrder,
        });
        const changes = generator.generatePreparationData(categoryIds, {});
        expect(changes[0].extra_data.order_label).toBe("Robin");
        const customer = changes[0].extra_data.customer;
        expect(customer.address).toInclude("21, Wonderfull Street");
        expect(customer.phone).toBe(comp.getFullPhone());
        expect(customer.email).toBe("robin@example.com");
    });

    test("name-only preset shows name and phone but no address", async () => {
        const store = await setupSelfPosEnv("kiosk");
        store.config.company_id.country_id.state_ids = [];
        store.config.company_id.country_id.phone_code = 1;
        const order = await getFilledSelfOrder(store);
        const preset = store.models["pos.preset"].get(1);
        preset.identification = "name";
        order.preset_id = preset;

        const comp = await mountWithCleanup(PresetInfoPopup, {
            props: { close: () => {}, getPayload: () => {} },
        });
        comp.state.name = "Sam";
        comp.state.phoneLocal = "2025551234";
        await comp.setInformations();
        expect(store.currentOrder.floating_order_name).toBe("Sam");
        store.currentOrder.mobile = comp.getFullPhone();

        const categoryIds = store.config.preparationCategories;
        const generator = store.ticketPrinter.getGenerator({
            models: store.models,
            order: store.currentOrder,
        });
        const changes = generator.generatePreparationData(categoryIds, {});
        expect(changes[0].extra_data.order_label).toBe("Sam");
        const customer = changes[0].extra_data.customer;
        expect(customer.phone).toBe(comp.getFullPhone());
        expect(customer.address).toBe(false);
    });
});
