import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("clickMyOrder navigates to cart with fromLanding when a draft order exists", async () => {
    const store = await setupSelfPosEnv("mobile");
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(LandingPage, {});

    expect(comp.draftOrder.length).toBeGreaterThan(0);

    patchWithCleanup(comp.router, {
        navigate(route, params, historyState) {
            expect.step(`${route}:${JSON.stringify(params)}:${JSON.stringify(historyState)}`);
        },
    });

    comp.clickMyOrder();
    expect.verifySteps(['cart:{}:{"fromLanding":true}']);
});

test("clickMyOrder navigates to orderHistory when there is no draft order", async () => {
    await setupSelfPosEnv();
    const comp = await mountWithCleanup(LandingPage, {});

    expect(comp.draftOrder.length).toBe(0);

    patchWithCleanup(comp.router, {
        navigate(route) {
            expect.step(route);
        },
    });

    comp.clickMyOrder();
    expect.verifySteps(["orderHistory"]);
});
