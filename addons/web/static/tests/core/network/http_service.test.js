import { describe, expect, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";

import { get, post } from "@web/core/network/http_service";

describe.current.tags("headless");

test("method is correctly set", async () => {
    mockFetch((_, { method }) => expect.step(method));

    await get("/call_get");
    expect.verifySteps(["GET"]);

    await post("/call_post");
    expect.verifySteps(["POST"]);
});

test("check status 502", async () => {
    mockFetch(() => new Response("{}", { status: 502 }));

    await expect(get("/custom_route")).rejects.toThrow(/Failed to fetch/);
});

test("FormData is built by post", async () => {
    mockFetch((_, { body }) => {
        expect(body).toBeInstanceOf(FormData);
        expect(body.get("s")).toBe("1");
        expect(body.get("a")).toBe("1");
        expect(body.getAll("a")).toEqual(["1", "2", "3"]);
    });

    await post("call_post", { s: 1, a: [1, 2, 3] });
});

test("FormData is given to post", async () => {
    const formData = new FormData();
    mockFetch((_, { body }) => expect(body).toBe(formData));

    await post("/call_post", formData);
});
