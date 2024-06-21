/** @odoo-module **/

import { pyToJsLocale } from "@web/core/l10n/utils";

QUnit.module("utils");

QUnit.test("pyToJsLocale", (assert) => {
    assert.strictEqual(pyToJsLocale("kab"), "kab");
    assert.strictEqual(pyToJsLocale("fr_BE"), "fr-BE");
    assert.strictEqual(pyToJsLocale("es_419"), "es-419");
    assert.strictEqual(pyToJsLocale("sr@latin"), "sr-Latn");
    assert.strictEqual(pyToJsLocale("sr_RS@latin"), "sr-Latn-RS");
    assert.strictEqual(pyToJsLocale("en-US"), "en-US");
});
