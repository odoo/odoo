/** @odoo-module **/

import {
    escape,
    escapeRegExp,
    intersperse,
    isEmail,
    sprintf,
    unaccent,
} from "@web/core/utils/strings";
import { _t, translatedTerms } from "@web/core/l10n/translation";
import { patchWithCleanup } from "../../helpers/utils";

QUnit.module("utils", () => {
    QUnit.module("strings");

    QUnit.test("escapeRegExp", (assert) => {
        assert.deepEqual(escapeRegExp(""), "");
        assert.deepEqual(escapeRegExp("wowl"), "wowl");
        assert.deepEqual(escapeRegExp("[wowl]"), "\\[wowl\\]");
        assert.deepEqual(escapeRegExp("[wowl.odoo]"), "\\[wowl\\.odoo\\]");
        assert.deepEqual(
            escapeRegExp("^odoo.define([.]*)$"),
            "\\^odoo\\.define\\(\\[\\.\\]\\*\\)\\$"
        );
        assert.deepEqual(
            escapeRegExp("[.*+?^${}()|[]\\"),
            "\\[\\.\\*\\+\\?\\^\\$\\{\\}\\(\\)\\|\\[\\]\\\\"
        );
    });

    QUnit.test("intersperse", (assert) => {
        assert.deepEqual(intersperse("", []), "");
        assert.deepEqual(intersperse("0", []), "0");
        assert.deepEqual(intersperse("012", []), "012");
        assert.deepEqual(intersperse("1", []), "1");
        assert.deepEqual(intersperse("12", []), "12");
        assert.deepEqual(intersperse("123", []), "123");
        assert.deepEqual(intersperse("1234", []), "1234");
        assert.deepEqual(intersperse("123456789", []), "123456789");
        assert.deepEqual(intersperse("&ab%#@1", []), "&ab%#@1");
        assert.deepEqual(intersperse("0", []), "0");
        assert.deepEqual(intersperse("0", [1]), "0");
        assert.deepEqual(intersperse("0", [2]), "0");
        assert.deepEqual(intersperse("0", [200]), "0");
        assert.deepEqual(intersperse("12345678", [0], "."), "12345678");
        assert.deepEqual(intersperse("", [1], "."), "");
        assert.deepEqual(intersperse("12345678", [1], "."), "1234567.8");
        assert.deepEqual(intersperse("12345678", [1], "."), "1234567.8");
        assert.deepEqual(intersperse("12345678", [2], "."), "123456.78");
        assert.deepEqual(intersperse("12345678", [2, 1], "."), "12345.6.78");
        assert.deepEqual(intersperse("12345678", [2, 0], "."), "12.34.56.78");
        assert.deepEqual(intersperse("12345678", [-1, 2], "."), "12345678");
        assert.deepEqual(intersperse("12345678", [2, -1], "."), "123456.78");
        assert.deepEqual(intersperse("12345678", [2, 0, 1], "."), "12.34.56.78");
        assert.deepEqual(intersperse("12345678", [2, 0, 0], "."), "12.34.56.78");
        assert.deepEqual(intersperse("12345678", [2, 0, -1], "."), "12.34.56.78");
        assert.deepEqual(intersperse("12345678", [3, 3, 3, 3], "."), "12.345.678");
        assert.deepEqual(intersperse("12345678", [3, 0], "."), "12.345.678");
    });

    QUnit.test("unaccent", function (assert) {
        assert.strictEqual(unaccent("éèàôù"), "eeaou");
        assert.strictEqual(unaccent("ⱮɀꝾƶⱵȥ"), "mzgzhz"); // single characters
        assert.strictEqual(unaccent("ǱǄꝎꜩꝡƕ"), "dzdzootzvyhv"); // doubled characters
        assert.strictEqual(unaccent("ⱮɀꝾƶⱵȥ", true), "MzGzHz"); // case sensitive characters
    });

    QUnit.test("sprintf properly formats strings", (assert) => {
        assert.deepEqual(sprintf("Hello %s!", "ged"), "Hello ged!");
        assert.deepEqual(sprintf("Hello %s and %s!", "ged", "lpe"), "Hello ged and lpe!");
        assert.deepEqual(sprintf("Hello %(x)s!", { x: "ged" }), "Hello ged!");
        assert.deepEqual(
            sprintf("Hello %(x)s and %(y)s!", { x: "ged", y: "lpe" }),
            "Hello ged and lpe!"
        );
        assert.deepEqual(sprintf("Hello!"), "Hello!");
        assert.deepEqual(sprintf("Hello %s!"), "Hello %s!");
        assert.deepEqual(sprintf("Hello %(value)s!"), "Hello %(value)s!");
    });

    QUnit.test("sprintf properly formats numbers", (assert) => {
        assert.deepEqual(sprintf("Hello %s!", 5), "Hello 5!");
        assert.deepEqual(sprintf("Hello %s and %s!", 9, 10), "Hello 9 and 10!");
        assert.deepEqual(sprintf("Hello %(x)s!", { x: 11 }), "Hello 11!");
        assert.deepEqual(sprintf("Hello %(x)s and %(y)s!", { x: 12, y: 13 }), "Hello 12 and 13!");
    });

    QUnit.test("sprintf set behavior when value is an Array", (assert) => {
        assert.deepEqual(sprintf("Hello %s!", ["inarray"]), "Hello inarray!");
        assert.deepEqual(sprintf("Hello %s and %s!", [9, "10"], [11]), "Hello 9,10 and 11!");
        assert.deepEqual(sprintf("Hello %(x)s!", { x: [11] }), "Hello 11!");
        assert.deepEqual(
            sprintf("Hello %(x)s and %(y)s!", { x: [12], y: ["13"] }),
            "Hello 12 and 13!"
        );
    });

    QUnit.test("sprintf supports lazy translated string", (assert) => {
        patchWithCleanup(translatedTerms, {
            one: "en",
            two: "två",
        });

        assert.deepEqual(sprintf("Hello %s", _t("one")), "Hello en");
        assert.deepEqual(sprintf("Hello %s %s", _t("one"), _t("two")), "Hello en två");

        const vals = {
            one: _t("one"),
            two: _t("two"),
        };
        assert.deepEqual(sprintf("Hello %(two)s %(one)s", vals), "Hello två en");
    });

    QUnit.test("escape", (assert) => {
        assert.strictEqual(escape("<a>this is a link</a>"), "&lt;a&gt;this is a link&lt;/a&gt;");
        assert.strictEqual(
            escape(`<a href="https://www.odoo.com">odoo<a>`),
            `&lt;a href=&quot;https://www.odoo.com&quot;&gt;odoo&lt;a&gt;`
        );
        assert.strictEqual(
            escape(`<a href='https://www.odoo.com'>odoo<a>`),
            `&lt;a href=&#x27;https://www.odoo.com&#x27;&gt;odoo&lt;a&gt;`
        );
        assert.strictEqual(
            escape("<a href='https://www.odoo.com'>Odoo`s website<a>"),
            `&lt;a href=&#x27;https://www.odoo.com&#x27;&gt;Odoo&#x60;s website&lt;a&gt;`
        );
    });

    QUnit.test("isEmail", (assert) => {
        assert.notOk(isEmail(""));
        assert.notOk(isEmail("test"));
        assert.notOk(isEmail("test@odoo"));
        assert.notOk(isEmail("test@odoo@odoo.com"));
        assert.notOk(isEmail("te st@odoo.com"));

        assert.ok(isEmail("test@odoo.com"));
    });
});
