import { describe, expect, test } from "@odoo/hoot";

import { DEFAULT_INTERVAL } from "@web/search/utils/dates";
import { getGroupBy } from "@web/search/utils/group_by";

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

describe("Without field validation", () => {
    test("simple valid group by", async () => {
        let groupBy = getGroupBy("display_name");
        expect(groupBy.fieldName).toBe("display_name");
        expect(groupBy.interval).toBe(null);
        expect(groupBy.spec).toBe("display_name");

        groupBy = getGroupBy("display_name:quarter");
        expect(groupBy.fieldName).toBe("display_name");
        expect(groupBy.interval).toBe("quarter");
        expect(groupBy.spec).toBe("display_name:quarter");
    });

    test("simple invalid group by", async () => {
        expect(() => getGroupBy(":day")).toThrow();
        expect(() => getGroupBy("diay_name:yar")).toThrow();
    });
});

describe("With field validation", () => {
    test("simple valid group by", async () => {
        const groupBy = getGroupBy("display_name", fields);
        expect(groupBy.fieldName).toBe("display_name");
        expect(groupBy.interval).toBe(null);
        expect(groupBy.spec).toBe("display_name");
    });

    test("simple invalid group by", async () => {
        expect(() => getGroupBy("", fields)).toThrow();
        expect(() => getGroupBy("display_name:day", fields)).toThrow();
        expect(() => getGroupBy("diay_name:year", fields)).toThrow();
        expect(() => getGroupBy("diay_name:yar", fields)).toThrow();
    });

    test("simple valid date group by", async () => {
        let groupBy = getGroupBy("date_field:year", fields);
        expect(groupBy.fieldName).toBe("date_field");
        expect(groupBy.interval).toBe("year");
        expect(groupBy.spec).toBe("date_field:year");

        groupBy = getGroupBy("date_field", fields);
        expect(groupBy.fieldName).toBe("date_field");
        expect(groupBy.interval).toBe(DEFAULT_INTERVAL);
        expect(groupBy.spec).toBe(`date_field:${DEFAULT_INTERVAL}`);
    });

    test("simple invalid date group by", async () => {
        expect(() => getGroupBy("date_field:yar", fields)).toThrow();
    });
});
