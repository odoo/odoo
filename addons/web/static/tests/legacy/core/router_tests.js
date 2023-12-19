/** @odoo-module alias=@web/../tests/core/router_tests default=false */

import { browser } from "@web/core/browser/browser";
import {
    parseHash,
    parseSearchQuery,
    routeToUrl,
    router,
    routerBus,
    startRouter,
} from "@web/core/browser/router";
import { nextTick, patchWithCleanup } from "../helpers/utils";

async function createRouter(params = {}) {
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
    startRouter();
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
    patchWithCleanup(browser, {
        location: {
            pathname: "/asf",
        },
    });
    let route = {};
    assert.strictEqual(routeToUrl(route), "/asf");

    route = { a: "11", g: "summer wine" };
    assert.strictEqual(routeToUrl(route), "/asf?a=11&g=summer%20wine");

    route = { b: "2", c: "", e: "kloug,gloubi" };
    assert.strictEqual(routeToUrl(route), "/asf?b=2&c=&e=kloug%2Cgloubi");
});

QUnit.module("Router: Push state");

QUnit.test("can push in same timeout", async (assert) => {
    await createRouter();

    assert.deepEqual(router.current, {});

    router.pushState({ k1: 2 });
    assert.deepEqual(router.current, {});

    router.pushState({ k1: 3 });
    assert.deepEqual(router.current, {});
    await nextTick();
    assert.deepEqual(router.current, { k1: 3 });
});

QUnit.test("can lock keys", async (assert) => {
    await createRouter();

    router.addLockedKey(["k1"]);

    router.replaceState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.replaceState({ k1: 3 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 3 });

    router.replaceState({ k2: 4 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 3, k2: 4 });

    router.replaceState({ k1: 4 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 4, k2: 4 });
});

QUnit.test("can re-lock keys in same final call", async (assert) => {
    await createRouter();

    router.addLockedKey(["k1"]);

    router.pushState({ k1: 2 });
    await nextTick();
    router.pushState({ k2: 1 });
    router.pushState({ k1: 4 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 4, k2: 1 });
});

QUnit.test("can replace search state", async (assert) => {
    await createRouter();

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.pushState({ k2: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(router.current, { k2: 3 });
});

QUnit.test("can replace search state with locked keys", async (assert) => {
    await createRouter();

    router.addLockedKey("k1");

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.pushState({ k2: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2, k2: 3 });
});

QUnit.test("can merge hash", async (assert) => {
    await createRouter();

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.pushState({ k2: 3 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2, k2: 3 });
});

QUnit.test("undefined keys are not pushed", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    await createRouter({ onPushState });

    router.pushState({ k1: undefined });
    await nextTick();
    assert.verifySteps([]);
    assert.deepEqual(router.current, {});
});

QUnit.test("undefined keys destroy previous non locked keys", async (assert) => {
    await createRouter();

    router.pushState({ k1: 1 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 1 });

    router.pushState({ k1: undefined });
    await nextTick();
    assert.deepEqual(router.current, {});
});

QUnit.test("do not re-push when hash is same", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    await createRouter({ onPushState });

    router.pushState({ k1: 1, k2: 2 });
    await nextTick();
    assert.verifySteps(["pushed state"]);

    router.pushState({ k2: 2, k1: 1 });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("do not re-push when hash is same (with integers as strings)", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    await createRouter({ onPushState });

    router.pushState({ k1: 1, k2: "2" });
    await nextTick();
    assert.verifySteps(["pushed state"]);

    router.pushState({ k2: 2, k1: "1" });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("test the help utils history.back and history.forward", async (assert) => {
    patchWithCleanup(browser.location, {
        pathname: "/asf",
        origin: "http://lordofthering",
    });
    routerBus.addEventListener("ROUTE_CHANGE", () => assert.step("ROUTE_CHANGE"));
    await createRouter();

    router.pushState({ k1: 1 });
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k1=1");

    router.pushState({ k2: 2 });
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k1=1&k2=2");

    router.pushState({ k3: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k3=3");

    browser.history.back(); // Click on back button
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k1=1&k2=2");

    router.pushState({ k4: 3 }, { replace: true }); // Click on a link
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k4=3");

    browser.history.back(); // Click on back button
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k1=1&k2=2");

    browser.history.forward(); // Click on forward button
    await nextTick();
    assert.deepEqual(browser.location.href, "http://lordofthering/asf?k4=3");

    assert.verifySteps(["ROUTE_CHANGE", "ROUTE_CHANGE", "ROUTE_CHANGE"]);
});

QUnit.module("Router: Retrocompatibility");

QUnit.test("parse an url with hash (key/values)", async (assert) => {
    browser.location.hash = "#a=114&b=c.e&f=1&g=91";
    await createRouter();
    assert.strictEqual(browser.location.search, "?a=114&b=c.e&f=1&g=91");
    assert.strictEqual(browser.location.hash, "");
    assert.deepEqual(router.current, { a: 114, b: "c.e", f: 1, g: 91 });
});

QUnit.test("parse an url with hash (key/values) and query string", async (assert) => {
    browser.location.hash = "#g=91";
    browser.location.search = "?a=114&b=c.e&f=1";
    await createRouter();
    assert.strictEqual(browser.location.search, "?a=114&b=c.e&f=1&g=91");
    assert.strictEqual(browser.location.hash, "");
    assert.deepEqual(router.current, { a: 114, b: "c.e", f: 1, g: 91 });
});

QUnit.test("parse an url with hash (anchor link)", async (assert) => {
    browser.location.hash = "#anchor";
    await createRouter();
    assert.strictEqual(browser.location.search, "");
    assert.strictEqual(browser.location.hash, "#anchor");
    assert.deepEqual(router.current, {});
});

QUnit.test("parse an url with hash (anchor link) and query string", async (assert) => {
    browser.location.hash = "#anchor";
    browser.location.search = "?a=114&b=c.e&f=1";
    await createRouter();
    assert.strictEqual(browser.location.search, "?a=114&b=c.e&f=1");
    assert.strictEqual(browser.location.hash, "#anchor");
    assert.deepEqual(router.current, { a: 114, b: "c.e", f: 1 });
});
