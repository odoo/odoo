import { test, describe, expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { PENDING_PREPARATION_KEY } from "@pos_self_order/app/services/self_order_service";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

const mockRouterLoad = (store) => {
    const loadedRoutes = [];
    patchWithCleanup(store.router, {
        load(routeName) {
            loadedRoutes.push(routeName);
        },
    });
    return loadedRoutes;
};

const setupKioskOrder = async (customerLanguageCode) => {
    const store = await setupSelfPosEnv("kiosk", "counter", "meal");
    await getFilledSelfOrder(store);
    const order = await store.sendDraftOrderToServer();
    order.state = "paid";
    expect(typeof order.access_token).toBe("string");

    const english = store.models["res.lang"].create({ code: "en_US", name: "English" });
    const french = store.models["res.lang"].create({ code: "fr_FR", name: "French" });
    store.config.self_ordering_available_language_ids = [english, french];
    store.config.self_ordering_default_language_id = english;
    store.currentLanguage = customerLanguageCode === "fr_FR" ? french : english;

    const prepPrints = [];
    patchWithCleanup(store.ticketPrinter, {
        async printOrderChanges({ order }) {
            prepPrints.push(order.access_token);
            return true;
        },
    });
    // Not the subject of these tests, and it needs a printer to be set up.
    patchWithCleanup(ConfirmationPage.prototype, { async printOrder() {} });

    const comp = await mountWithCleanup(ConfirmationPage, {
        props: { orderAccessToken: order.access_token, screenMode: "order" },
    });
    await animationFrame();
    await animationFrame();

    return { store, order, prepPrints, comp };
};

describe("kiosk preparation ticket", () => {
    test("is printed right away when the kiosk is in its own language", async () => {
        const { store, order, prepPrints, comp } = await setupKioskOrder("en_US");
        const loadedRoutes = mockRouterLoad(store);

        expect(prepPrints).toEqual([order.access_token]);

        // The kiosk still goes home with a page load, to refresh its data, but it has no pending preparation to print
        comp.backToHome();
        expect(loadedRoutes).toEqual(["default"]);
        expect(browser.sessionStorage.getItem(PENDING_PREPARATION_KEY)).toBe(null);
    });

    test("waits for the reload when the customer changed the language", async () => {
        const { store, order, prepPrints, comp } = await setupKioskOrder("fr_FR");
        const loadedRoutes = mockRouterLoad(store);

        // A ticket printed now would be in the language of the customer.
        expect(prepPrints).toEqual([]);

        comp.backToHome();

        // The kiosk language is restored, leaving the order for the reloaded kiosk to print
        expect(cookie.get("frontend_lang")).toBe("en_US");
        expect(loadedRoutes).toEqual(["default"]);
        expect(prepPrints).toEqual([]);
        expect(browser.sessionStorage.getItem(PENDING_PREPARATION_KEY)).toBe(order.access_token);
    });

    test("is printed once on the next kiosk boot, and only once", async () => {
        const { store, order, prepPrints } = await setupKioskOrder("fr_FR");

        store.setPendingPreparation(order.access_token);
        expect(prepPrints).toEqual([]);

        await store.printPendingPreparation();
        expect(prepPrints).toEqual([order.access_token]);
        expect(browser.sessionStorage.getItem(PENDING_PREPARATION_KEY)).toBe(null);

        // The order was only fetched to be printed: keeping it would show "My orders" on the landing page
        expect(store.models["pos.order"].getAll().length).toBe(0);

        // The order has been consumed, a further boot does not print it again.
        await store.printPendingPreparation();
        expect(prepPrints).toEqual([order.access_token]);
    });
});
