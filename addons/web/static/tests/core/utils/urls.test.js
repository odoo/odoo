import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { getDataURLFromFile, getOrigin, redirect, url } from "@web/core/utils/urls";

describe.current.tags("headless");

beforeEach(() => {
    patchWithCleanup(browser, {
        location: { protocol: "http:", host: "testhost" },
    });
});

test("getOrigin", () => {
    expect(getOrigin()).toBe("http://testhost");
    expect(getOrigin("protocol://host")).toBe("protocol://host");
});

test("can return current origin", () => {
    patchWithCleanup(browser, {
        location: { protocol: "testprotocol:", host: "testhost" },
    });
    expect(url()).toBe("testprotocol://testhost");
});

test("can return custom origin", () => {
    const testUrl = url(null, null, { origin: "customProtocol://customHost/" });
    expect(testUrl).toBe("customProtocol://customHost");
});

test("can return custom origin with route", () => {
    const testUrl = url("/my_route", null, { origin: "customProtocol://customHost/" });
    expect(testUrl).toBe("customProtocol://customHost/my_route");
});

test("can return full route", () => {
    const testUrl = url("/my_route");
    expect(testUrl).toBe("http://testhost/my_route");
});

test("can return full route with params", () => {
    const testUrl = url("/my_route", { my_param: [1, 2], other: 9 });
    expect(testUrl).toBe("http://testhost/my_route?my_param=1%2C2&other=9");
});

test("can return cors urls", () => {
    const testUrl = url("https://cors_server/cors_route/");
    expect(testUrl).toBe("https://cors_server/cors_route/");
});

test("can be used for cors urls", () => {
    const testUrl = url("https://cors_server/cors_route/", { my_param: [1, 2] });
    expect(testUrl).toBe("https://cors_server/cors_route/?my_param=1%2C2");
});

test("getDataURLFromFile handles empty file", async () => {
    const emptyFile = new File([""], "empty.txt", { type: "text/plain" });
    const dataUrl = await getDataURLFromFile(emptyFile);
    expect(dataUrl).toBe("data:text/plain;base64,", {
        message: "dataURL for empty file is not proper",
    });
});

test("redirect", () => {
    function testRedirect(url) {
        browser.location = {
            protocol: "http:",
            host: "testhost",
            origin: "http://www.test.com",
            pathname: "/some/tests",
            href: "http://www.test.com",
            assign: (url) => {
                browser.location.href = url;
            },
        };
        redirect(url);
        return browser.location.href;
    }

    expect(testRedirect("abc")).toBe("http://www.test.com/some/abc");
    expect(testRedirect("./abc")).toBe("http://www.test.com/some/abc");
    expect(testRedirect("../abc/def")).toBe("http://www.test.com/abc/def");
    expect(testRedirect("/abc/def")).toBe("http://www.test.com/abc/def");
    expect(testRedirect("/abc/def?x=y")).toBe("http://www.test.com/abc/def?x=y");
    expect(testRedirect("/abc?x=y#a=1&b=2")).toBe("http://www.test.com/abc?x=y#a=1&b=2");

    expect(() => testRedirect("https://www.odoo.com")).toThrow(/Can't redirect/);
    expect(() => testRedirect("javascript:alert('boom');")).toThrow(/Can't redirect/);
});
