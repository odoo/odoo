import { after, describe, expect, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { patch } from "@web/core/utils/patch";

describe.current.tags("headless");

const CACHE_NAME = "odoo-pos-cache";
const POS_URL = "/pos/ui/1";

async function setup({ cachedText, status }) {
    after(() => caches.delete(CACHE_NAME));
    const cache = await caches.open(CACHE_NAME);
    if (cachedText) {
        await cache.put(new Request(POS_URL), new Response(cachedText));
    }
    patch(Cache.prototype, {
        put(request, response) {
            expect.step(`cache ${response.status}`);
            return super.put(...arguments);
        },
    });
    const server = { status };
    mockFetch(() => new Response("server", { status: server.status }));
    return server;
}

function swFetch() {
    let response;
    const event = new Event("fetch");
    Object.assign(event, {
        request: new Request(POS_URL),
        respondWith: (promise) => (response = promise),
    });
    window.dispatchEvent(event);
    return response;
}

test("serves the cached page when the server answers a 5xx", async () => {
    await setup({ cachedText: "cached pos", status: 502 });

    const response = await swFetch();
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("cached pos");
    expect.verifySteps([]);
});

test("returns the 5xx response when nothing is cached", async () => {
    await setup({ status: 502 });

    const response = await swFetch();
    expect(response.status).toBe(502);
    expect.verifySteps([]);
});

test("only caches successful responses", async () => {
    const server = await setup({ status: 404 });
    expect((await swFetch()).status).toBe(404);
    expect.verifySteps([]);

    server.status = 200;
    expect((await swFetch()).status).toBe(200);
    expect.verifySteps(["cache 200"]);
});
