// @ts-check

/**
 * Pure unit tests for record_utils.js.
 *
 * These tests run without OWL, without a browser DOM, and without any
 * mock server. They verify the pure domain logic extracted from Record.
 */

import { describe, expect, test } from "@odoo/hoot";
import {
    computeChangeset,
    evaluateFieldAttr,
    isFieldInvisible,
    isFieldReadonly,
    isFieldRequired,
} from "@web/model/relational_model/record_utils";

// ---------------------------------------------------------------------------
// evaluateFieldAttr
// ---------------------------------------------------------------------------

describe("evaluateFieldAttr", () => {
    test("returns false for falsy expression", () => {
        expect(evaluateFieldAttr(false, {})).toBe(false);
        expect(evaluateFieldAttr("", {})).toBe(false);
    });

    test("evaluates simple truthy expression", () => {
        expect(evaluateFieldAttr("True", {})).toBe(true);
        expect(evaluateFieldAttr("False", {})).toBe(false);
    });

    test("evaluates expression against context", () => {
        const ctx = { state: "done" };
        expect(evaluateFieldAttr("state == 'done'", ctx)).toBe(true);
        expect(evaluateFieldAttr("state == 'draft'", ctx)).toBe(false);
    });

    test("evaluates compound boolean expressions", () => {
        const ctx = { state: "done", active: true };
        expect(evaluateFieldAttr("state == 'done' and active", ctx)).toBe(true);
        expect(evaluateFieldAttr("state == 'draft' or active", ctx)).toBe(true);
        expect(evaluateFieldAttr("state == 'draft' and active", ctx)).toBe(false);
    });

    test("evaluates numeric comparisons", () => {
        const ctx = { amount: 100 };
        expect(evaluateFieldAttr("amount > 50", ctx)).toBe(true);
        expect(evaluateFieldAttr("amount > 200", ctx)).toBe(false);
        expect(evaluateFieldAttr("amount == 100", ctx)).toBe(true);
    });

    test("handles 'not' operator", () => {
        const ctx = { active: false };
        expect(evaluateFieldAttr("not active", ctx)).toBe(true);
    });

    test("handles 'in' operator", () => {
        const ctx = { state: "done" };
        expect(evaluateFieldAttr("state in ('done', 'cancel')", ctx)).toBe(true);
        expect(evaluateFieldAttr("state in ('draft', 'open')", ctx)).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// isFieldInvisible / isFieldReadonly / isFieldRequired
// ---------------------------------------------------------------------------

describe("isFieldInvisible", () => {
    test("returns false when no invisible expression", () => {
        expect(isFieldInvisible({ invisible: false }, {})).toBe(false);
    });

    test("evaluates invisible expression", () => {
        const activeField = { invisible: "state == 'done'" };
        expect(isFieldInvisible(activeField, { state: "done" })).toBe(true);
        expect(isFieldInvisible(activeField, { state: "draft" })).toBe(false);
    });
});

describe("isFieldReadonly", () => {
    test("returns false when no readonly expression", () => {
        expect(isFieldReadonly({ readonly: false }, {})).toBe(false);
    });

    test("evaluates readonly expression", () => {
        const activeField = { readonly: "state == 'done'" };
        expect(isFieldReadonly(activeField, { state: "done" })).toBe(true);
        expect(isFieldReadonly(activeField, { state: "draft" })).toBe(false);
    });
});

describe("isFieldRequired", () => {
    test("returns false when no required expression", () => {
        expect(isFieldRequired({ required: false }, {})).toBe(false);
    });

    test("evaluates required expression", () => {
        const activeField = { required: "True" };
        expect(isFieldRequired(activeField, {})).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// computeChangeset
// ---------------------------------------------------------------------------

describe("computeChangeset", () => {
    const fields = {
        id: { type: "integer" },
        name: { type: "char" },
        amount: { type: "float" },
        date: { type: "date" },
        partner_id: { type: "many2one" },
        tag_ids: { type: "many2many" },
        line_ids: { type: "one2many" },
        prop: { type: "char", relatedPropertyField: true },
    };

    const activeFields = {
        name: { readonly: false, forceSave: false },
        amount: { readonly: false, forceSave: false },
        partner_id: { readonly: false, forceSave: false },
        tag_ids: { readonly: false, forceSave: false },
        line_ids: { readonly: false, forceSave: false },
        prop: { readonly: false, forceSave: false },
    };

    const noopGetCommands = (fieldName, value) => [];

    test("skips id field", () => {
        const result = computeChangeset({
            changes: { id: 1, name: "test" },
            values: {},
            isNew: false,
            fields,
            activeFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect("id" in result).toBe(false);
        expect(result.name).toBe("test");
    });

    test("skips relatedPropertyField", () => {
        const result = computeChangeset({
            changes: { prop: "value", name: "test" },
            values: {},
            isNew: false,
            fields,
            activeFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect("prop" in result).toBe(false);
        expect(result.name).toBe("test");
    });

    test("skips readonly fields by default", () => {
        const readonlyActiveFields = {
            ...activeFields,
            amount: { readonly: "True", forceSave: false },
        };
        const result = computeChangeset({
            changes: { name: "test", amount: 42 },
            values: {},
            isNew: false,
            fields,
            activeFields: readonlyActiveFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect("amount" in result).toBe(false);
        expect(result.name).toBe("test");
    });

    test("includes readonly fields when withReadonly is true", () => {
        const readonlyActiveFields = {
            ...activeFields,
            amount: { readonly: "True", forceSave: false },
        };
        const result = computeChangeset({
            changes: { name: "test", amount: 42 },
            values: {},
            isNew: false,
            fields,
            activeFields: readonlyActiveFields,
            evalContext: {},
            options: { withReadonly: true },
            getCommands: noopGetCommands,
        });
        expect(result.amount).toBe(42);
    });

    test("includes readonly fields with forceSave", () => {
        const forceSaveActiveFields = {
            ...activeFields,
            amount: { readonly: "True", forceSave: true },
        };
        const result = computeChangeset({
            changes: { amount: 42 },
            values: {},
            isNew: false,
            fields,
            activeFields: forceSaveActiveFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect(result.amount).toBe(42);
    });

    test("merges values into changes for new records", () => {
        const result = computeChangeset({
            changes: { amount: 99 },
            values: { name: "default" },
            isNew: true,
            fields,
            activeFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect(result.name).toBe("default");
        expect(result.amount).toBe(99);
    });

    test("changes override values for new records", () => {
        const result = computeChangeset({
            changes: { name: "overridden" },
            values: { name: "default" },
            isNew: true,
            fields,
            activeFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect(result.name).toBe("overridden");
    });

    test("formats char empty string as false", () => {
        const result = computeChangeset({
            changes: { name: "" },
            values: {},
            isNew: false,
            fields,
            activeFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect(result.name).toBe(false);
    });

    test("formats many2one as id", () => {
        const result = computeChangeset({
            changes: { partner_id: { id: 7, display_name: "Partner" } },
            values: {},
            isNew: false,
            fields,
            activeFields,
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect(result.partner_id).toBe(7);
    });

    test("delegates x2many to getCommands callback", () => {
        const mockCommands = [[0, "virtual_1", { name: "new line" }]];
        const getCommands = (fieldName, value, withReadonly) => {
            expect(fieldName).toBe("tag_ids");
            return mockCommands;
        };
        const result = computeChangeset({
            changes: { tag_ids: { _getCommands: () => mockCommands } },
            values: {},
            isNew: false,
            fields,
            activeFields,
            evalContext: {},
            getCommands,
        });
        expect(result.tag_ids).toBe(mockCommands);
    });

    test("skips x2many with empty commands on existing record", () => {
        const result = computeChangeset({
            changes: { tag_ids: {} },
            values: {},
            isNew: false,
            fields,
            activeFields,
            evalContext: {},
            getCommands: () => [],
        });
        expect("tag_ids" in result).toBe(false);
    });

    test("includes x2many with empty commands on new record", () => {
        const result = computeChangeset({
            changes: { tag_ids: {} },
            values: {},
            isNew: true,
            fields,
            activeFields,
            evalContext: {},
            getCommands: () => [],
        });
        expect(result.tag_ids).toEqual([]);
    });

    test("skips fields not in activeFields for readonly check", () => {
        // A field may exist in `fields` but not in `activeFields` (e.g., computed
        // fields fetched by default but not in the view). These should pass through.
        const result = computeChangeset({
            changes: { name: "test" },
            values: {},
            isNew: false,
            fields,
            activeFields: {},
            evalContext: {},
            getCommands: noopGetCommands,
        });
        expect(result.name).toBe("test");
    });
});
