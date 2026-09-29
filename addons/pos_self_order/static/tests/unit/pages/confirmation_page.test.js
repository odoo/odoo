import { test, describe, expect, click } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { setupSelfPosEnv, getFilledSelfOrder, mockRouterNavigate } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

const setupPaidKioskOrder = async () => {
    const store = await setupSelfPosEnv();
    onRpc("/pos_self_order/kiosk/increment_nb_print/", () => true);

    const printed = [];
    patchWithCleanup(store.ticketPrinter, {
        async printOrderReceipt() {
            printed.push("receipt");
            return true;
        },
        async printOrderChanges() {
            printed.push("changes");
            return true;
        },
    });

    await getFilledSelfOrder(store);
    const order = await store.sendDraftOrderToServer();
    order.state = "paid";

    return { store, order, printed };
};

const mountConfirmationPage = async (order) => {
    const page = await mountWithCleanup(ConfirmationPage, {
        props: { screenMode: "order", orderAccessToken: order.access_token },
    });
    await animationFrame();
    return page;
};

describe("kiosk receipts", () => {
    test("are printed when the confirmation page is shown", async () => {
        const { order, printed } = await setupPaidKioskOrder();
        expect(printed).toEqual([]);
        expect(order.nb_print).toBe(0);

        await mountConfirmationPage(order);

        expect(printed).toEqual(["receipt", "changes"]);
        expect(order.nb_print).toBe(1);
    });

    test("are not printed again for an order already printed", async () => {
        const { order, printed } = await setupPaidKioskOrder();
        // Happens when the page is mounted a second time for the same order
        order.nb_print = 1;
        await mountConfirmationPage(order);
        expect(printed).toEqual([]);
        expect(order.nb_print).toBe(1);
    });
});

test("closing the page restores the default language from the landing page", async () => {
    const { store, order } = await setupPaidKioskOrder();

    mockRouterNavigate();
    patchWithCleanup(browser.location, {
        reload: () => expect.step("reload"),
    });
    // `res.lang` is not loaded in the tests, languages are only compared by code.
    store.config.self_ordering_default_language_id = { code: "en_US" };
    store.currentLanguage = { code: "fr_FR" };

    await mountConfirmationPage(order);
    await click("button:contains(Close)");
    await animationFrame();

    // The confirmation page must not be reloaded, it would print the order again.
    expect(store.router.path).toBe(`/pos-self/${store.config.id}`);
    expect.verifySteps(["reload"]);
});
