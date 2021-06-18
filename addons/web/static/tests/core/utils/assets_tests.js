/** @odoo-module **/

import { loadAssets } from "@web/core/assets";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

QUnit.module("utils", () => {
    QUnit.module("Assets");

    QUnit.test("loadAssets: load invalid JS lib", function (assert) {
        assert.rejects(
            loadAssets({ jsLibs: ["/some/invalid/file.js"] }),
            new RegExp("The loading of /some/invalid/file.js failed"),
            "Trying to load an invalid file rejects the promise"
        );
        assert.ok(
            document.querySelector("script[src='/some/invalid/file.js']"),
            "Document contains a script with the src we asked to load"
        );
    });

    QUnit.test("loadAssets: load invalid CSS lib", function (assert) {
        assert.rejects(
            loadAssets({ cssLibs: ["/some/invalid/file.css"] }),
            new RegExp("The loading of /some/invalid/file.css failed"),
            "Trying to load an invalid file rejects the promise"
        );
        assert.ok(
            document.querySelector("link[href='/some/invalid/file.css']"),
            "Document contains a link with the href we asked to load"
        );
    });

    QUnit.test("loadAssets: load invalid bundle", function (assert) {
        let lastFetchedURL;
        patchWithCleanup(browser, {
            fetch: function (url) {
                lastFetchedURL = url;
                return Promise.reject(`Failed to load ressource at "${url}"`);
            },
        });
        assert.rejects(
            loadAssets({
                bundles: {
                    "web.some_invalid_bundle": { templates: true },
                },
            }),
            "Trying to load an invalid bundle rejects the promise"
        );
        assert.ok(
            /\/web\/webclient\/qweb\/.*\?bundle=web\.some_invalid_bundle$/.test(lastFetchedURL),
            "Loading a bundle calls the /web/webclient/qweb route with the corresponding bundle query parameter"
        );
    });
});
