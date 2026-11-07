/** @odoo-module **/

import { range } from "@web/core/utils/numbers";

QUnit.module("utils", () => {
    QUnit.module("Numbers", () => {
        QUnit.test("test range function from core/utils/numbers.js", (assert) => {
            assert.deepEqual(range(0, 10), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
            assert.deepEqual(range(0, -10, -1), [0, -1, -2, -3, -4, -5, -6, -7, -8, -9]);
            assert.deepEqual(range(0, 35, 5), [0, 5, 10, 15, 20, 25, 30]);
            assert.deepEqual(range(-10, 6, 2), [-10, -8, -6, -4, -2, 0, 2, 4]);
            assert.deepEqual(range(4, -4, -1), [4, 3, 2, 1, 0, -1, -2, -3]);
        });
    });
});
