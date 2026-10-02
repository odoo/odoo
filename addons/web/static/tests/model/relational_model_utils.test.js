import { describe, expect, test } from "@odoo/hoot";

import { getFieldsSpec } from "@web/model/relational_model/utils";

describe.current.tags("headless");

test("getFieldsSpec ignores active fields missing from the field definitions", () => {
    const activeFields = {
        display_name: {},
        missing_field: {},
    };
    const fields = {
        display_name: { type: "char" },
    };

    expect(getFieldsSpec(activeFields, fields)).toEqual({ display_name: {} });
});
