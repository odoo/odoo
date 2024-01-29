/** @odoo-module **/

import { after, expect, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";

import { get, post } from "@web/core/network/http_service";

test`headless`("method is correctly set", async () => {
    const restoreFetch = mockFetch((_, { method }) => {
        expect.step(method);
    });
    after(restoreFetch);

    await get("/call_get");
    expect(["GET"]).toVerifySteps();

    await post("/call_post");
    expect(["POST"]).toVerifySteps();
});

test`headless`("check status 502", async () => {
    const restoreFetch = mockFetch(() => new Response("{}", { status: 502 }));
    after(restoreFetch);
    await expect(get("/custom_route")).rejects.toThrow(/Failed to fetch/);
});

test`headless`("FormData is built by post", async () => {
    const restoreFetch = mockFetch((_, { body }) => {
        expect(body).toSatisfy((body) => body instanceof FormData);
        expect(body.get("s"), "1");
        expect(body.get("a"), "1");
        expect(body.getAll("a"), ["1", "2", "3"]);
    });
    after(restoreFetch);
    await post("call_post", { s: 1, a: [1, 2, 3] });
});

test`headless`("FormData is given to post", async () => {
    const formData = new FormData();
    const restoreFetch = mockFetch((_, { body }) => {
        expect(body).toBe(formData);
    });
    after(restoreFetch);
    await post("/call_post", formData);
});
