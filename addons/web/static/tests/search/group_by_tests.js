/** @odoo-module **/

import { getGroupBy } from "@web/search/utils/group_by";
import { DEFAULT_INTERVAL } from "@web/search/utils/dates";

const fields = {
    display_name: { string: "Displayed name", type: "char" },
    foo: {
        string: "Foo",
        type: "char",
        default: "My little Foo Value",
        store: true,
        sortable: true,
    },
    date_field: { string: "Date", type: "date", store: true, sortable: true },
    float_field: { string: "Float", type: "float" },
    bar: { string: "Bar", type: "many2one", relation: "partner" },
};

QUnit.module("GroupBy Class", {}, () => {
    QUnit.module("Without field validation");
    QUnit.test("simple valid group by", async function (assert) {
        assert.expect(6);
        let groupBy = getGroupBy("display_name");
        assert.strictEqual(groupBy.fieldName, "display_name");
        assert.strictEqual(groupBy.interval, null);
        assert.strictEqual(groupBy.spec, "display_name");
        groupBy = getGroupBy("display_name:quarter");
        assert.strictEqual(groupBy.fieldName, "display_name");
        assert.strictEqual(groupBy.interval, "quarter");
        assert.strictEqual(groupBy.spec, "display_name:quarter");
    });
    QUnit.test("simple invalid group by", async function (assert) {
        assert.expect(3);
        try {
            getGroupBy(":day");
        } catch (_e) {
            assert.step("Error 1");
        }
        try {
            getGroupBy("diay_name:yar");
        } catch (_e) {
            assert.step("Error 2");
        }
        assert.verifySteps(["Error 1", "Error 2"]);
    });
    QUnit.module("With field validation");
    QUnit.test("simple valid group by", async function (assert) {
        assert.expect(3);
        const groupBy = getGroupBy("display_name", fields);
        assert.strictEqual(groupBy.fieldName, "display_name");
        assert.strictEqual(groupBy.interval, null);
        assert.strictEqual(groupBy.spec, "display_name");
    });
    QUnit.test("simple invalid group by", async function (assert) {
        assert.expect(5);
        try {
            getGroupBy("", fields);
        } catch (_e) {
            assert.step("Error 1");
        }
        try {
            getGroupBy("display_name:day", fields);
        } catch (_e) {
            assert.step("Error 2");
        }
        try {
            getGroupBy("diay_name:year", fields);
        } catch (_e) {
            assert.step("Error 3");
        }
        try {
            getGroupBy("diay_name:yar", fields);
        } catch (_e) {
            assert.step("Error 4");
        }
        assert.verifySteps(["Error 1", "Error 2", "Error 3", "Error 4"]);
    });
    QUnit.test("simple valid date group by", async function (assert) {
        assert.expect(6);
        let groupBy = getGroupBy("date_field:year", fields);
        assert.strictEqual(groupBy.fieldName, "date_field");
        assert.strictEqual(groupBy.interval, "year");
        assert.strictEqual(groupBy.spec, "date_field:year");
        groupBy = getGroupBy("date_field", fields);
        assert.strictEqual(groupBy.fieldName, "date_field");
        assert.strictEqual(groupBy.interval, DEFAULT_INTERVAL);
        assert.strictEqual(groupBy.spec, `date_field:${DEFAULT_INTERVAL}`);
    });
    QUnit.test("simple invalid date group by", async function (assert) {
        assert.expect(2);
        try {
            getGroupBy("date_field:yar", fields);
        } catch (_e) {
            assert.step("Error");
        }
        assert.verifySteps(["Error"]);
    });
});
