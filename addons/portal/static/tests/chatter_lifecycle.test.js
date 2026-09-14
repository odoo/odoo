import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { App } from "@odoo/owl";
import { portalChatterBootService } from "@portal/chatter/boot/boot_service";
import { PortalChatterService } from "@portal/chatter/frontend/portal_chatter_service";
import { makeMockEnv, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { assets } from "@web/core/assets";
import { Deferred } from "@web/core/utils/concurrency";

async function prepareChatter() {
    onRpc("/portal/chatter_init", () => ({}));
    const env = await makeMockEnv();
    getFixture().innerHTML =
        '<div class="o_portal_chatter" data-res_id="1" data-res_model="res.partner" data-allow_composer="0"></div>';
    patchWithCleanup(odoo, { portalChatterReady: new Deferred() });
    const service = new PortalChatterService(env, {
        "mail.store": { Thread: { insert: () => ({ rpcParams: {} }) }, insert() {} },
    });
    patchWithCleanup(service, {
        createShadow: async (root) => root.attachShadow({ mode: "open" }),
    });
    return { service, env };
}

test("chatter readiness waits for the app to mount", async () => {
    const { service, env } = await prepareChatter();
    const mounted = new Deferred();
    patchWithCleanup(App.prototype, { mount: () => mounted });
    let ready = false;
    odoo.portalChatterReady.then(() => {
        ready = true;
    });
    const initialization = service.initialize(env);
    await animationFrame();
    expect(ready).toBe(false);
    mounted.resolve();
    await initialization;
    expect(await odoo.portalChatterReady).toBe(true);
});

test("failed chatter mounting rejects initialization and removes its root", async () => {
    const { service, env } = await prepareChatter();
    patchWithCleanup(App.prototype, {
        mount: async () => {
            throw new Error("mount failed");
        },
        destroy: () => expect.step("destroy"),
    });
    await expect(service.initialize(env)).rejects.toThrow("mount failed");
    expect("#chatterRoot").toHaveCount(0);
    expect.verifySteps(["destroy"]);
});

test("failed chatter bundle loading settles readiness false", async () => {
    await makeMockEnv();
    getFixture().innerHTML = '<div class="o_portal_chatter"></div>';
    patchWithCleanup(odoo, { portalChatterReady: new Deferred() });
    const failure = new Error("bundle failed");
    patchWithCleanup(assets, {
        loadBundle: async () => {
            throw failure;
        },
    });
    patchWithCleanup(console, {
        error: (message, error) => {
            expect(error).toBe(failure);
            expect.step("reported");
        },
    });
    expect(portalChatterBootService.start()).toBe(undefined);
    expect(await odoo.portalChatterReady).toBe(false);
    expect.verifySteps(["reported"]);
});
