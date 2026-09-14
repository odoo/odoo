// @ts-check
import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { websiteService } from "@website/services/website_service";

describe.current.tags("headless");

function startWebsiteService(orm = {}) {
    const components = registry.category("main_components");
    patchWithCleanup(components, {
        add() {
            return components;
        },
    });
    return websiteService.start(
        {},
        {
            orm: {
                async webSearchRead() {
                    return { records: [{ id: 1 }] };
                },
                ...orm,
            },
            action: {},
            hotkey: { add() {} },
        },
    );
}

for (const [pathname, translatable, expected] of [
    ["/es/caf%C3%A9", true, "/café"],
    ["/es", true, "/"],
    ["/es/broken%ZZ", true, "/broken%ZZ"],
    ["/broken%ZZ", false, "/broken%ZZ"],
]) {
    test(`currentLocation preserves a usable path for ${pathname}`, async () => {
        const service = startWebsiteService();
        await service.fetchWebsites();
        service.currentWebsiteId = 1;
        const page = document.implementation.createHTMLDocument("Page");
        page.documentElement.dataset.websiteId = "1";
        page.documentElement.lang = "es";
        if (translatable) {
            page.documentElement.dataset.translatable = "1";
        }
        const location = new URL(`https://example.test${pathname}`);
        service.pageDocument = {
            documentElement: page.documentElement,
            title: page.title,
            querySelectorAll: page.querySelectorAll.bind(page),
            getElementById: page.getElementById.bind(page),
            location,
            defaultView: { location },
        };
        expect(service.currentLocation).toBe(expected);
    });
}

for (const hasWebsite of [false, true]) {
    test(`model-name fallback without page metadata, website loaded: ${hasWebsite}`, async () => {
        const service = startWebsiteService({
            async call() {
                expect.step("unexpected model request");
                return [];
            },
        });
        if (hasWebsite) {
            await service.fetchWebsites();
            service.currentWebsiteId = 1;
            service.pageDocument = null;
        }
        expect(await service.getUserModelName()).toBe("Data");
        expect.verifySteps([]);
    });
}

test("model-name callers share their request and retain successful results", async () => {
    const response = new Deferred();
    const service = startWebsiteService({
        call(model, method) {
            expect(model).toBe("ir.model");
            expect(method).toBe("get_available_models");
            expect.step("request");
            return response;
        },
    });
    const first = service.getUserModelName("website.page");
    const second = service.getUserModelName("product.template");
    response.resolve([
        { model: "website.page", display_name: "Page" },
        { model: "product.template", display_name: "Product" },
    ]);
    expect(await Promise.all([first, second])).toEqual(["Page", "Product"]);
    expect(await service.getUserModelName("website.page")).toBe("Page");
    expect(await service.getUserModelName("unknown.model")).toBe("Data");
    expect.verifySteps(["request"]);
});

test("a failed model-name request can be retried", async () => {
    let attempts = 0;
    const service = startWebsiteService({
        async call() {
            attempts++;
            if (attempts === 1) {
                throw new Error("offline");
            }
            return [{ model: "website.page", display_name: "Page" }];
        },
    });
    expect(await service.getUserModelName("website.page")).toBe("Data");
    expect(await service.getUserModelName("website.page")).toBe("Page");
    expect(attempts).toBe(2);
});

test("unknown model names cannot resolve inherited object properties", async () => {
    const service = startWebsiteService({
        async call() {
            return [];
        },
    });
    for (const model of ["constructor", "__proto__", "toString"]) {
        expect(await service.getUserModelName(model)).toBe("Data");
    }
});
