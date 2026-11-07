/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import {
    getDataURLFromFile,
    getOrigin,
    redirect,
    RedirectionError,
    url,
} from "@web/core/utils/urls";
import { patchWithCleanup } from "../../helpers/utils";

QUnit.module("URLS", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(browser, {
            location: { protocol: "http:", host: "testhost" },
        });
    });

    QUnit.test("urls.getOrigin", (assert) => {
        assert.strictEqual(getOrigin(), "http://testhost");
        assert.strictEqual(getOrigin("protocol://host"), "protocol://host");
    });

    QUnit.test("can return current origin", (assert) => {
        patchWithCleanup(browser, {
            location: { protocol: "testprotocol:", host: "testhost" },
        });

        const testUrl = url();
        assert.strictEqual(testUrl, "testprotocol://testhost");
    });

    QUnit.test("can return custom origin", (assert) => {
        const testUrl = url(null, null, { origin: "customProtocol://customHost/" });
        assert.strictEqual(testUrl, "customProtocol://customHost");
    });

    QUnit.test("can return custom origin with route", (assert) => {
        const testUrl = url("/my_route", null, { origin: "customProtocol://customHost/" });
        assert.strictEqual(testUrl, "customProtocol://customHost/my_route");
    });

    QUnit.test("can return full route", (assert) => {
        const testUrl = url("/my_route");
        assert.strictEqual(testUrl, "http://testhost/my_route");
    });

    QUnit.test("can return full route with params", (assert) => {
        const testUrl = url("/my_route", {
            my_param: [1, 2],
            other: 9,
        });
        assert.strictEqual(testUrl, "http://testhost/my_route?my_param=1%2C2&other=9");
    });

    QUnit.test("can return cors urls", (assert) => {
        const testUrl = url("https://cors_server/cors_route/");
        assert.strictEqual(testUrl, "https://cors_server/cors_route/");
    });

    QUnit.test("can be used for cors urls", (assert) => {
        const testUrl = url("https://cors_server/cors_route/", {
            my_param: [1, 2],
        });
        assert.strictEqual(testUrl, "https://cors_server/cors_route/?my_param=1%2C2");
    });

    QUnit.test("getDataURLFromFile handles empty file", async (assert) => {
        const emptyFile = new File([""], "empty.txt", { type: "text/plain" });
        const dataUrl = await getDataURLFromFile(emptyFile);
        assert.strictEqual(
            dataUrl,
            "data:text/plain;base64,",
            "dataURL for empty file is not proper"
        );
    });

    QUnit.test("redirect", (assert) => {
        function testRedirect(url) {
            browser.location = {
                protocol: "http:",
                host: "testhost",
                origin: "http://www.test.com",
                pathname: "/some/tests",
            };
            redirect(url);
            return browser.location;
        }

        assert.strictEqual(testRedirect("abc"), "http://www.test.com/some/abc");
        assert.strictEqual(testRedirect("./abc"), "http://www.test.com/some/abc");
        assert.strictEqual(testRedirect("../abc/def"), "http://www.test.com/abc/def");
        assert.strictEqual(testRedirect("/abc/def"), "http://www.test.com/abc/def");
        assert.strictEqual(testRedirect("/abc/def?x=y"), "http://www.test.com/abc/def?x=y");
        assert.strictEqual(testRedirect("/abc?x=y#a=1&b=2"), "http://www.test.com/abc?x=y#a=1&b=2");

        assert.throws(() => testRedirect("https://www.odoo.com"), RedirectionError);
        assert.throws(() => testRedirect("javascript:alert('boom');"), RedirectionError);
    });
});
