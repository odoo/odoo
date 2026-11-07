/** @odoo-module **/

import { humanSize } from "@web/core/utils/binary";

QUnit.module("utils", () => {
    QUnit.module("binary");

    QUnit.test("humanSize", (assert) => {
        assert.strictEqual(humanSize(0), "0.00 Bytes");
        assert.strictEqual(humanSize(3), "3.00 Bytes");
        assert.strictEqual(humanSize(2048), "2.00 Kb");
        assert.strictEqual(humanSize(2645000), "2.52 Mb");
    });
});
