/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { parseHash, parseSearchQuery, routeToUrl } from "@web/core/browser/router_service";
import { makeFakeRouterService } from "../helpers/mock_services";
import { nextTick, patchWithCleanup } from "../helpers/utils";

import { EventBus } from "@odoo/owl";

async function createRouter(params = {}) {
    const env = params.env || {};
    env.bus = env.bus || new EventBus();
    if (params.onPushState) {
        const originalPushState = browser.history.pushState;
        const onPushState = params.onPushState;
        delete params.onPushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    originalPushState(...arguments);
                    onPushState(...arguments);
                },
            }),
        });
    }
    const router = await makeFakeRouterService(params).start(env);
    return router;
}

QUnit.module("Router");

QUnit.test("can parse an empty hash", (assert) => {
    assert.deepEqual(parseHash(""), {});
});

QUnit.test("can parse an single hash", (assert) => {
    assert.deepEqual(parseHash("#"), {});
});

QUnit.test("can parse a hash with a single key/value pair", (assert) => {
    const hash = "#action=114";
    assert.deepEqual(parseHash(hash), { action: 114 });
});

QUnit.test("can parse a hash with 2 key/value pairs", (assert) => {
    const hash = "#action=114&active_id=mail.box_inbox";
    assert.deepEqual(parseHash(hash), { action: 114, active_id: "mail.box_inbox" });
});

QUnit.test("a missing value is encoded as an empty string", (assert) => {
    const hash = "#action";
    assert.deepEqual(parseHash(hash), { action: "" });
});

QUnit.test("a missing value is encoded as an empty string -- 2", (assert) => {
    const hash = "#action=";
    assert.deepEqual(parseHash(hash), { action: "" });
});

QUnit.test("can parse a realistic hash", (assert) => {
    const hash = "#action=114&active_id=mail.box_inbox&cids=1&menu_id=91";
    const expected = {
        action: 114,
        active_id: "mail.box_inbox",
        cids: 1,
        menu_id: 91,
    };
    assert.deepEqual(parseHash(hash), expected);
});

QUnit.test("can parse an empty search", (assert) => {
    assert.deepEqual(parseSearchQuery(""), {});
});

QUnit.test("can parse an simple search with no value", (assert) => {
    assert.deepEqual(parseSearchQuery("?a"), { a: "" });
});

QUnit.test("can parse an simple search with a value", (assert) => {
    assert.deepEqual(parseSearchQuery("?a=1"), { a: 1 });
});

QUnit.test("can parse an search with 2 key/value pairs", (assert) => {
    assert.deepEqual(parseSearchQuery("?a=1&b=2"), { a: 1, b: 2 });
});

QUnit.test("can parse URI encoded strings", (assert) => {
    assert.deepEqual(parseSearchQuery("?space=this%20is"), { space: "this is" });
    assert.deepEqual(parseHash("#comma=that%2Cis"), { comma: "that,is" });
});

QUnit.test("routeToUrl encodes URI compatible strings", (assert) => {
    const route = { pathname: "/asf", search: {}, hash: {} };
    assert.strictEqual(routeToUrl(route), "/asf");

    route.search = { a: "11", g: "summer wine" };
    assert.strictEqual(routeToUrl(route), "/asf?a=11&g=summer%20wine");

    route.hash = { b: "2", c: "", e: "kloug,gloubi" };
    assert.strictEqual(routeToUrl(route), "/asf?a=11&g=summer%20wine#b=2&c=&e=kloug%2Cgloubi");
});

QUnit.module("Router: Push state");

QUnit.test("can push in same timeout", async (assert) => {
    const router = await createRouter();

    assert.deepEqual(router.current.hash, {});

    router.pushState({ k1: 2 });
    assert.deepEqual(router.current.hash, {});

    router.pushState({ k1: 3 });
    assert.deepEqual(router.current.hash, {});
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 3 });
});

QUnit.test("can lock keys", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 2 }, { lock: true });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k1: 3 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k1: 4 }, { lock: true });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 4 });

    router.pushState({ k1: 3 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 4 });
});

QUnit.test("can re-lock keys in same final call", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 2 }, { lock: true });
    await nextTick();
    router.pushState({ k1: 1 }, { lock: true });
    router.pushState({ k1: 4 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 1 });
});

QUnit.test("can unlock keys", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 2 }, { lock: true });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k1: 3 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k1: 4 }, { lock: false });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 4 });

    router.pushState({ k1: 3 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 3 });
});

QUnit.test("can replace hash", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k2: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(router.current.hash, { k2: 3 });
});

QUnit.test("can replace hash with locked keys", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 2 }, { lock: true });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k2: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2, k2: 3 });
});

QUnit.test("can merge hash", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2 });

    router.pushState({ k2: 3 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 2, k2: 3 });
});

QUnit.test("undefined keys are not pushed", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    const router = await createRouter({ onPushState });

    router.pushState({ k1: undefined });
    await nextTick();
    assert.verifySteps([]);
    assert.deepEqual(router.current.hash, {});
});

QUnit.test("undefined keys destroy previous non locked keys", async (assert) => {
    const router = await createRouter();

    router.pushState({ k1: 1 });
    await nextTick();
    assert.deepEqual(router.current.hash, { k1: 1 });

    router.pushState({ k1: undefined });
    await nextTick();
    assert.deepEqual(router.current.hash, {});
});

QUnit.test("do not re-push when hash is same", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    const router = await createRouter({ onPushState });

    router.pushState({ k1: 1, k2: 2 });
    await nextTick();
    assert.verifySteps(["pushed state"]);

    router.pushState({ k2: 2, k1: 1 });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("do not re-push when hash is same (with integers as strings)", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    const router = await createRouter({ onPushState });

    router.pushState({ k1: 1, k2: "2" });
    await nextTick();
    assert.verifySteps(["pushed state"]);

    router.pushState({ k2: 2, k1: "1" });
    await nextTick();
    assert.verifySteps([]);
});
