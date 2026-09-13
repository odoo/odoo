// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import {
    completeActiveFields,
    makeActiveField,
    patchActiveFields,
} from "@web/model/relational_model/field_metadata";
import { getAggregateSpecifications } from "@web/model/relational_model/field_values";
import { getModifierDependencies } from "@web/model/relational_model/record_utils";

describe.current.tags("headless");

function makeX2manyActiveField() {
    return {
        ...makeActiveField(),
        related: {
            activeFields: { qty: makeActiveField() },
            fields: { qty: { type: "integer", name: "qty" } },
        },
    };
}

describe("patchActiveFields", () => {
    test("invalidates the nested modifier-dependency memo", () => {
        const activeField = makeX2manyActiveField();
        const nested = activeField.related.activeFields;
        expect(getModifierDependencies(nested).dependents.get("qty")).toBe(undefined);

        patchActiveFields(activeField, {
            ...makeActiveField(),
            related: {
                activeFields: { name: makeActiveField({ required: "qty > 0" }) },
                fields: { name: { type: "char", name: "name" } },
            },
        });

        const deps = getModifierDependencies(nested);
        expect([...(deps.dependents.get("qty") || [])]).toEqual(["name"]);
    });

    test("invalidates the nested aggregate-spec memo", () => {
        const activeField = makeX2manyActiveField();
        const nestedFields = activeField.related.fields;
        expect(getAggregateSpecifications(nestedFields)).toEqual([]);

        patchActiveFields(activeField, {
            ...makeActiveField(),
            related: {
                activeFields: { total: makeActiveField() },
                fields: {
                    total: { type: "float", name: "total", aggregator: "sum" },
                },
            },
        });

        expect(getAggregateSpecifications(nestedFields)).toEqual([
            "total:sum",
            "total:count",
        ]);
    });
});

describe("completeActiveFields", () => {
    test("invalidates the top-level and nested modifier-dependency memos", () => {
        const listActiveFields = { line_ids: makeX2manyActiveField() };
        const nested = listActiveFields.line_ids.related.activeFields;
        expect(getModifierDependencies(listActiveFields).dependents.size).toBe(0);
        expect(getModifierDependencies(nested).dependents.get("qty")).toBe(undefined);

        completeActiveFields(listActiveFields, {
            line_ids: {
                ...makeActiveField(),
                related: {
                    activeFields: { name: makeActiveField({ required: "qty > 0" }) },
                    fields: { name: { type: "char", name: "name" } },
                },
            },
            state: makeActiveField(),
            extra: makeActiveField({ required: "state == 'done'" }),
        });

        expect([
            ...(getModifierDependencies(nested).dependents.get("qty") || []),
        ]).toEqual(["name"]);
        expect([
            ...(getModifierDependencies(listActiveFields).dependents.get("state") ||
                []),
        ]).toEqual(["extra"]);
    });
});
