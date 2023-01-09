/** @odoo-module **/

import { loadJS, loadCSS } from "@web/core/assets";

QUnit.module("utils", () => {
    QUnit.module("Assets");

    QUnit.test("loadJS: load invalid JS lib", function (assert) {
        assert.rejects(
            loadJS("/some/invalid/file.js"),
            new RegExp("The loading of /some/invalid/file.js failed"),
            "Trying to load an invalid file rejects the promise"
        );
        assert.ok(
            document.querySelector("script[src='/some/invalid/file.js']"),
            "Document contains a script with the src we asked to load"
        );
    });

    QUnit.test("loadCSS: load invalid CSS lib", function (assert) {
        assert.rejects(
            loadCSS("/some/invalid/file.css"),
            new RegExp("The loading of /some/invalid/file.css failed"),
            "Trying to load an invalid file rejects the promise"
        );
        assert.ok(
            document.querySelector("link[href='/some/invalid/file.css']"),
            "Document contains a link with the href we asked to load"
        );
    });
});
