/** @odoo-module **/

import { fuzzyLookup, fuzzyTest } from "@web/core/utils/search";

QUnit.module("utils", () => {
    QUnit.module("Fuzzy Search");

    QUnit.test("fuzzyLookup", function (assert) {
        const data = [
            { name: "Abby White" },
            { name: "Robert Black" },
            { name: "Jane Yellow" },
            { name: "Brandon Green" },
            { name: "Jérémy Red" },
        ];
        assert.deepEqual(
            fuzzyLookup("ba", data, (d) => d.name),
            [{ name: "Brandon Green" }, { name: "Robert Black" }]
        );
        assert.deepEqual(
            fuzzyLookup("g", data, (d) => d.name),
            [{ name: "Brandon Green" }]
        );
        assert.deepEqual(
            fuzzyLookup("z", data, (d) => d.name),
            []
        );
        assert.deepEqual(
            fuzzyLookup("brand", data, (d) => d.name),
            [{ name: "Brandon Green" }]
        );
        assert.deepEqual(
            fuzzyLookup("jâ", data, (d) => d.name),
            [{ name: "Jane Yellow" }]
        );
        assert.deepEqual(
            fuzzyLookup("je", data, (d) => d.name),
            [{ name: "Jérémy Red" }, { name: "Jane Yellow" }]
        );
        assert.deepEqual(
            fuzzyLookup("", data, (d) => d.name),
            []
        );
    });

    QUnit.test("fuzzyTest", function (assert) {
        assert.ok(fuzzyTest("a", "Abby White"));
        assert.ok(fuzzyTest("ba", "Brandon Green"));
        assert.ok(fuzzyTest("je", "Jérémy red"));
        assert.ok(fuzzyTest("jé", "Jeremy red"));
        assert.notOk(fuzzyTest("z", "Abby White"));
        assert.notOk(fuzzyTest("ba", "Abby White"));
    });
});
