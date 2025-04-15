/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "../../helpers/utils";
import { get, post } from "@web/core/network/http_service";

function onFetch(fetch) {
    patchWithCleanup(browser, {
        fetch: (route, params) => {
            const result = fetch(route, params);
            return result ?? new Response("{}");
        },
    });
}

QUnit.module("HTTP");

QUnit.test("method is correctly set", async (assert) => {
    onFetch((_, { method }) => {
        assert.step(method);
    });
    await get("/call_get");
    assert.verifySteps(["GET"]);
    await post("/call_post");
    assert.verifySteps(["POST"]);
});

QUnit.test("check status 502", async (assert) => {
    onFetch(() => {
        return new Response({}, { status: 502 });
    });
    try {
        await get("/custom_route");
        assert.notOk(true);
    } catch (e) {
        assert.strictEqual(e.message, "Failed to fetch");
    }
});

QUnit.test("FormData is built by post", async (assert) => {
    onFetch((_, { body }) => {
        assert.ok(body instanceof FormData);
        assert.strictEqual(body.get("s"), "1");
        assert.strictEqual(body.get("a"), "1");
        assert.deepEqual(body.getAll("a"), ["1", "2", "3"]);
    });
    await post("/call_post", { s: 1, a: [1, 2, 3] });
});

QUnit.test("FormData is given to post", async (assert) => {
    onFetch((_, { body }) => {
        assert.strictEqual(body, formData);
    });
    const formData = new FormData();
    await post("/call_post", formData);
});
