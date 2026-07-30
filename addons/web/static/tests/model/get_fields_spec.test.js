import { expect, test } from "@odoo/hoot";

import { getFieldsSpec } from "@web/model/relational_model/utils";

test("getFieldsSpec skips activeFields missing from fields (sample/empty state)", () => {
    // Reproduces bank-rec KanbanSampleModel crash path (#276570): activeFields can
    // contain keys that are not present on the fields meta dict.
    const activeFields = {
        name: { invisible: "False" },
        ghost_field: { invisible: "False" },
        partner_id: {
            invisible: "False",
            related: {
                activeFields: { display_name: { invisible: "False" } },
                fields: { display_name: { type: "char", name: "display_name" } },
            },
        },
    };
    const fields = {
        name: { type: "char", name: "name" },
        partner_id: { type: "many2one", name: "partner_id", relation: "res.partner" },
        // ghost_field intentionally omitted
    };

    let spec;
    expect(() => {
        spec = getFieldsSpec(activeFields, fields, {});
    }).not.toThrow();

    expect("name" in spec).toBe(true);
    expect("partner_id" in spec).toBe(true);
    expect("ghost_field" in spec).toBe(false);
    expect("display_name" in (spec.partner_id.fields || {})).toBe(true);
});

test("getFieldsSpec skips relatedPropertyField entries safely", () => {
    const activeFields = {
        x: { invisible: "False" },
        prop_like: { invisible: "False" },
    };
    const fields = {
        x: { type: "char", name: "x" },
        prop_like: {
            type: "char",
            name: "prop_like",
            relatedPropertyField: { name: "properties" },
        },
    };
    const spec = getFieldsSpec(activeFields, fields, {});
    expect("x" in spec).toBe(true);
    expect("prop_like" in spec).toBe(false);
});
