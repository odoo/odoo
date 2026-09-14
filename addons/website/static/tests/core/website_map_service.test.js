// @ts-check

import "@website/builder/plugins/options/google_maps_option/google_maps_service";

import { describe, expect, getFixture, test } from "@odoo/hoot";
import { mockFetch, tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { assets } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { websiteMapService } from "@website/core/website_map_service";

describe.current.tags("headless");

test("builder load honors an overridden key provider", async () => {
    const service = registry
        .category("services")
        .get("google_maps")
        .start({}, { notification: { add() {} } });
    mockFetch(() => ({ result: JSON.stringify({ google_maps_api_key: "unpatched" }) }));
    patchWithCleanup(service, {
        async getGMapsAPIKey() {
            expect.step("key override");
            return "override";
        },
    });
    patchWithCleanup(assets, {
        async loadJS(url) {
            completeScript(url);
        },
    });
    expect(await service.loadGMapsAPI(true)).toBe("override");
    expect.verifySteps(["key override"]);
});

test("builder validation honors an overridden map fetcher", async () => {
    const service = registry
        .category("services")
        .get("google_maps")
        .start({}, { notification: { add() {} } });
    mockFetch(() => new Response("unpatched", { status: 403 }));
    patchWithCleanup(service, {
        async fetchGoogleMaps(key) {
            expect(key).toBe("override");
            expect.step("fetch override");
            return new Response("");
        },
    });
    expect(await service.validateGMapsApiKey("override")).toEqual({
        isValid: true,
        message: undefined,
    });
    expect.verifySteps(["fetch override"]);
});

test("builder service preserves its API and retries failed scripts", async () => {
    const service = registry
        .category("services")
        .get("google_maps")
        .start({}, { notification: { add() {} } });
    mockFetch(() => ({
        result: JSON.stringify({ google_maps_api_key: "builder-key" }),
    }));
    let attempts = 0;
    patchWithCleanup(assets, {
        async loadJS(url) {
            if (++attempts === 1) {
                throw new Error("script unavailable");
            }
            completeScript(url);
        },
    });
    expect(await service.getGMapsAPIKey()).toBe("builder-key");
    expect(await service.loadGMapsAPI(true)).toBe(false);
    expect(await service.loadGMapsAPI(true)).toBe("builder-key");
    expect(attempts).toBe(2);
    expect(await service.validateGMapsApiKey("")).toEqual({ isValid: false });
});

function startService(mockKey = true) {
    const service = websiteMapService.start(
        {},
        {
            "public.interactions": { stopInteractions() {}, startInteractions() {} },
            notification: { add() {} },
        },
    );
    if (mockKey) {
        patchWithCleanup(service, { getGMapAPIKey: async () => "test-key" });
    }
    return service;
}

test("a stale key response failure does not evict the refreshed key", async () => {
    const service = startService(false);
    const oldResponse = new Deferred();
    let requests = 0;
    mockFetch(async () => {
        requests++;
        return requests === 1
            ? await oldResponse
            : { result: JSON.stringify({ google_maps_api_key: "new" }) };
    });
    const oldKey = service.getGMapAPIKey();
    await tick();
    expect(await service.getGMapAPIKey(true)).toBe("new");
    oldResponse.resolve({ result: "invalid JSON" });
    expect(await oldKey).toBe("");
    expect(await service.getGMapAPIKey()).toBe("new");
    expect(requests).toBe(2);
});

test("a malformed key response can be retried", async () => {
    const service = startService(false);
    let requests = 0;
    mockFetch(() => ({
        result:
            ++requests === 1
                ? "invalid JSON"
                : JSON.stringify({ google_maps_api_key: "new" }),
    }));
    expect(await service.getGMapAPIKey()).toBe("");
    expect(await service.getGMapAPIKey()).toBe("new");
    expect(requests).toBe(2);
});

function completeScript(url) {
    window[new URL(url).searchParams.get("callback")]();
}

test("concurrent callers share a script and wait for API readiness", async () => {
    const service = startService();
    let scriptUrl;
    patchWithCleanup(assets, {
        async loadJS(url) {
            expect.step("script");
            scriptUrl = url;
        },
    });
    let settled = false;
    const first = service.loadGMapAPI(true).then((key) => {
        settled = true;
        return key;
    });
    const second = service.loadGMapAPI(true);
    await tick();
    expect(settled).toBe(false);
    completeScript(scriptUrl);
    expect(await Promise.all([first, second])).toEqual(["test-key", "test-key"]);
    expect(await service.loadGMapAPI(true, true)).toBe("test-key");
    expect.verifySteps(["script"]);
});

test("API readiness restarts map sections and releases the global callback", async () => {
    getFixture().innerHTML = '<section class="s_google_map"></section>';
    const service = websiteMapService.start(
        {},
        {
            "public.interactions": {
                stopInteractions(el) {
                    expect(el).toBe(getFixture().firstElementChild);
                    expect.step("stop");
                },
                startInteractions(el) {
                    expect(el).toBe(getFixture().firstElementChild);
                    expect.step("start");
                },
            },
            notification: { add() {} },
        },
    );
    patchWithCleanup(service, { getGMapAPIKey: async () => "test-key" });
    let callbackName = "";
    patchWithCleanup(assets, {
        async loadJS(url) {
            callbackName = new URL(url).searchParams.get("callback");
            completeScript(url);
        },
    });
    expect(await service.loadGMapAPI(true)).toBe("test-key");
    expect.verifySteps(["stop", "start"]);
    expect(window[callbackName]).toBe(undefined);
});

test("a failed script can be retried with the same key", async () => {
    const service = startService();
    let attempts = 0;
    patchWithCleanup(assets, {
        async loadJS(url) {
            attempts++;
            if (attempts === 1) {
                throw new Error("script unavailable");
            }
            completeScript(url);
        },
    });
    expect(await service.loadGMapAPI(true)).toBe(false);
    const retry = service.loadGMapAPI(true);
    await tick();
    expect(attempts).toBe(2);
    expect(await retry).toBe("test-key");
});

test("refetched keys have independent readiness callbacks", async () => {
    const service = startService();
    let key = "first";
    patchWithCleanup(service, { getGMapAPIKey: async () => key });
    const urls = [];
    patchWithCleanup(assets, {
        async loadJS(url) {
            urls.push(url);
        },
    });
    const settled = [];
    const first = service.loadGMapAPI(true).then((key) => settled.push(key));
    await tick();
    key = "second";
    const second = service.loadGMapAPI(true, true).then((key) => settled.push(key));
    await tick();
    completeScript(urls[0]);
    await tick();
    expect(settled).toEqual(["first"]);
    completeScript(urls[1]);
    await Promise.all([first, second]);
    expect(settled).toEqual(["first", "second"]);
});

test("an older load failure does not evict a newer successful load", async () => {
    const service = startService();
    const oldScript = new Deferred();
    let key = "first";
    patchWithCleanup(service, {
        async getGMapAPIKey() {
            expect.step("key");
            return key;
        },
    });
    patchWithCleanup(assets, {
        async loadJS(url) {
            if (new URL(url).searchParams.get("key") === "first") {
                await oldScript;
            } else {
                completeScript(url);
            }
        },
    });
    const first = service.loadGMapAPI(true);
    await tick();
    key = "second";
    expect(await service.loadGMapAPI(true, true)).toBe("second");
    oldScript.reject(new Error("old request failed"));
    expect(await first).toBe(false);
    expect(await service.loadGMapAPI(true)).toBe("second");
    expect.verifySteps(["key", "key"]);
});

test("keys matching object prototype properties still load a script", async () => {
    const service = startService();
    patchWithCleanup(service, { getGMapAPIKey: async () => "constructor" });
    patchWithCleanup(assets, {
        async loadJS(url) {
            expect.step("script");
            completeScript(url);
        },
    });
    expect(await service.loadGMapAPI(true)).toBe("constructor");
    expect.verifySteps(["script"]);
});
