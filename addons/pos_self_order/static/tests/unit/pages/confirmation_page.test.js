import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { location } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";
import { getFilledSelfOrder, setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

async function mountConfirmationPage(mode) {
    const store = await setupSelfPosEnv(mode);
    const order = await getFilledSelfOrder(store);
    store.selectedOrderUuid = order.uuid;
    store.calls = [];
    store.ticketPrinter.printOrderReceipt = async () => ({ successful: true });
    store.ticketPrinter.printOrderChanges = async () => store.calls.push("printOrderChanges");
    const comp = await mountWithCleanup(ConfirmationPage, {
        props: { orderAccessToken: order.access_token, screenMode: "pay" },
    });
    await animationFrame();
    return { store, comp };
}

describe("preparation tickets", () => {
    test("kiosk prints them once the order is confirmed", async () => {
        const { store } = await mountConfirmationPage("kiosk");
        expect(store.calls).toEqual(["printOrderChanges"]);
    });

    test("mobile never prints them", async () => {
        const { store } = await mountConfirmationPage("mobile");
        expect(store.calls).toEqual([]);
    });
});

describe("setDefautLanguage", () => {
    async function setupLanguages(mode, currentCode) {
        const { store, comp } = await mountConfirmationPage(mode);
        const redirects = [];
        patch(location, {
            assign(url) {
                redirects.push(url);
            },
        });
        const language = store.models["res.lang"].create({ id: 999, code: "fr_FR", name: "FR" });
        store.config.self_ordering_default_language_id = language;
        store.currentLanguage = { code: currentCode };
        comp.state.onReload = false;
        cookie.set("frontend_lang", currentCode);
        return { comp, redirects };
    }

    test("kiosk in another language resets it and redirects to the default route", async () => {
        const { comp, redirects } = await setupLanguages("kiosk", "nl_BE");

        expect(comp.setDefautLanguage()).toBe(true);
        expect(cookie.get("frontend_lang")).toBe("fr_FR");
        expect(comp.state.onReload).toBe(true);
        expect(redirects).toHaveLength(1);
        const url = new URL(redirects[0]);
        expect(url.pathname).toBe("/pos-self/1");
        expect(Object.fromEntries(url.searchParams)).toEqual(
            Object.fromEntries(new URLSearchParams(location.search))
        );
    });

    test("only redirects once", async () => {
        const { comp, redirects } = await setupLanguages("kiosk", "nl_BE");

        comp.setDefautLanguage();
        expect(comp.setDefautLanguage()).toBe(true);

        expect(redirects).toHaveLength(1);
    });

    test("kiosk in the default language does not redirect", async () => {
        const { comp, redirects } = await setupLanguages("kiosk", "fr_FR");

        expect(comp.setDefautLanguage()).toBe(false);

        expect(redirects).toHaveLength(0);
    });

    test("mobile keeps the language of the customer", async () => {
        const { comp, redirects } = await setupLanguages("mobile", "nl_BE");

        expect(comp.setDefautLanguage()).toBe(false);

        expect(cookie.get("frontend_lang")).toBe("nl_BE");
        expect(redirects).toHaveLength(0);
    });
});
