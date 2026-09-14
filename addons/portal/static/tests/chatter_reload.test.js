import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { PortalChatter } from "@portal/chatter/frontend/portal_chatter";
import {
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

async function prepareChatter(fetchMessages) {
    const env = await makeMockEnv();
    const thread = { messages: [], fetchMessages };
    patchWithCleanup(PortalChatter.prototype, {
        setup() {
            super.setup(...arguments);
            this.store = { Thread: { get: () => thread } };
        },
    });
    // Mount the real event subscriber without the independently tested mail UI.
    patchWithCleanup(PortalChatter, { template: xml`<div/>` });
    const chatter = await mountWithCleanup(PortalChatter, {
        env,
        props: {
            resId: 1,
            resModel: "res.partner",
            composer: false,
            twoColumns: false,
            displayRating: false,
        },
    });
    return { env, thread, chatter };
}

test("reload events during a fetch are coalesced into one sequential follow-up", async () => {
    const first = new Deferred();
    const second = new Deferred();
    let calls = 0;
    const { env, thread, chatter } = await prepareChatter(() => {
        expect.step("fetch");
        return ++calls === 1 ? first : second;
    });
    env.bus.trigger("reload_chatter_content");
    await animationFrame();
    env.bus.trigger("reload_chatter_content");
    env.bus.trigger("reload_chatter_content");
    expect(calls).toBe(1);
    first.resolve(["first"]);
    await animationFrame();
    expect(calls).toBe(2);
    second.resolve(["latest"]);
    await chatter.reloadPromise;
    expect(thread.messages).toEqual(["latest"]);
    expect.verifySteps(["fetch", "fetch"]);
});

test("a failed reload releases the request for a later retry", async () => {
    let calls = 0;
    const { chatter, thread } = await prepareChatter(async () => {
        if (++calls === 1) {
            throw new Error("fetch failed");
        }
        return ["recovered"];
    });
    await expect(chatter._reloadChatterContent()).rejects.toThrow("fetch failed");
    await chatter._reloadChatterContent();
    expect(thread.messages).toEqual(["recovered"]);
});

test("destroying chatter removes its listener and abandons queued reloads", async () => {
    const fetched = new Deferred();
    let calls = 0;
    const { env, chatter, thread } = await prepareChatter(() => {
        calls++;
        return fetched;
    });
    env.bus.trigger("reload_chatter_content");
    await animationFrame();
    env.bus.trigger("reload_chatter_content");
    chatter.__owl__.app.destroy();
    env.bus.trigger("reload_chatter_content");
    fetched.resolve(["late"]);
    await chatter.reloadPromise;
    expect(calls).toBe(1);
    expect(thread.messages).toEqual([]);
});

test("a reload at the completion boundary starts another fetch", async () => {
    const fetched = new Deferred();
    let calls = 0;
    const { chatter, thread } = await prepareChatter(() => {
        if (++calls === 1) {
            return fetched;
        }
        return ["latest"];
    });
    const first = chatter._reloadChatterContent();
    await animationFrame();
    const atCompletion = fetched.then(() => chatter._reloadChatterContent());
    fetched.resolve(["first"]);
    await Promise.all([first, atCompletion]);
    expect(thread.messages).toEqual(["latest"]);
    expect(calls).toBe(2);
});

test("a failed fetch does not drop a reload queued while it was pending", async () => {
    const first = new Deferred();
    let calls = 0;
    const { chatter, thread, env } = await prepareChatter(() =>
        ++calls === 1 ? first : Promise.resolve(["latest"]),
    );
    const pending = chatter._reloadChatterContent().then(
        () => "loaded",
        () => "failed",
    );
    await animationFrame();
    env.bus.trigger("reload_chatter_content");
    first.reject(new Error("first fetch failed"));
    expect(await pending).toBe("loaded");
    expect(calls).toBe(2);
    expect(thread.messages).toEqual(["latest"]);
});
