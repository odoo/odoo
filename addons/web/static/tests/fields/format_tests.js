/** @odoo-module **/

import { formatMany2one } from "@web/fields/format";

QUnit.module("Format Fields", {}, () => {
    QUnit.test("formatMany2one", function (assert) {
        assert.strictEqual(formatMany2one(null), "");
        assert.strictEqual(formatMany2one([1, "A M2O value"]), "A M2O value");
        assert.strictEqual(
            formatMany2one({
                data: { display_name: "A M2O value" },
            }),
            "A M2O value"
        );

        assert.strictEqual(formatMany2one([1, "A M2O value"], { escape: true }), "A%20M2O%20value");
        assert.strictEqual(
            formatMany2one(
                {
                    data: { display_name: "A M2O value" },
                },
                { escape: true }
            ),
            "A%20M2O%20value"
        );
    });
});
