// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeLogger } from "@web/core/debug/debug_logger";
import {
    getBasicEvalContext,
    getFieldContext,
    getId,
    isRelational,
} from "@web/model/relational_model/field_context";

describe.current.tags("headless");

test("two live consumers of one field retain independent context identities", () => {
    const record = {
        context: {},
        fields: { owner: {} },
        activeFields: { owner: { context: "{}" } },
        evalContext: {},
    };
    const firstWidget = {};
    const secondWidget = {};
    const first = getFieldContext(record, "owner", "{'limit': 10}", firstWidget);
    const second = getFieldContext(record, "owner", "{'limit': 20}", secondWidget);
    const repeated = getFieldContext(record, "owner", "{'limit': 10}", firstWidget);
    makeLogger("web.model.audit").logic("field context owner isolation", {
        first,
        second,
        reused: repeated === first,
    });
    expect(repeated).toBe(first);
    expect(getFieldContext(record, "owner", "{'limit': 20}", secondWidget)).toBe(
        second,
    );
});

test("equivalent context expressions preserve identity while changing values invalidate it", () => {
    const record = {
        context: {
            lang: "en_US",
            default_name: "excluded",
            search_default_name: 1,
            form_view_ref: "excluded",
        },
        fields: { owner: { context: { lang: "fr_FR" } } },
        activeFields: { owner: { context: "{}" } },
        evalContext: { chosen: 7 },
    };
    const first = getFieldContext(record, "owner", "{'owner': chosen}");
    const same = getFieldContext(record, "owner", "{'owner': 7}");
    expect(first).toEqual({ lang: "fr_FR", owner: 7 });
    expect(same).toBe(first);
    record.evalContext.chosen = 8;
    const changed = getFieldContext(record, "owner", "{'owner': chosen}");
    makeLogger("web.model.audit").logic("field context invalidation", {
        first,
        changed,
    });
    expect(changed).toEqual({ lang: "fr_FR", owner: 8 });
    expect(changed).not.toBe(first);
});

describe("getId", () => {
    test("returns unique string IDs on successive calls", () => {
        const id1 = getId();
        const id2 = getId();
        expect(id1).not.toBe(id2);
    });

    test("includes prefix when provided", () => {
        const id = getId("virtual");
        expect(id.startsWith("virtual_")).toBe(true);
    });

    test("uses empty prefix when not provided", () => {
        const id = getId();
        expect(id.startsWith("_")).toBe(true);
    });

    test("each call increments the ID", () => {
        const before = getId("x");
        const after = getId("x");
        const numBefore = parseInt(before.split("_")[1], 10);
        const numAfter = parseInt(after.split("_")[1], 10);
        expect(numAfter).toBe(numBefore + 1);
    });
});

describe("isRelational", () => {
    test("returns true for many2one", () => {
        expect(isRelational({ type: "many2one" })).toBe(true);
    });

    test("returns true for one2many", () => {
        expect(isRelational({ type: "one2many" })).toBe(true);
    });

    test("returns true for many2many", () => {
        expect(isRelational({ type: "many2many" })).toBe(true);
    });

    test("returns false for char", () => {
        expect(isRelational({ type: "char" })).toBe(false);
    });

    test("returns false for float", () => {
        expect(isRelational({ type: "float" })).toBe(false);
    });

    test("returns null/undefined for null/undefined field", () => {
        expect(isRelational(null)).toBe(null);
        expect(isRelational(undefined)).toBe(undefined);
    });
});

describe("getBasicEvalContext", () => {
    test("extracts uid and allowed_company_ids from config context", () => {
        const config = {
            context: { uid: 3, allowed_company_ids: [1, 2] },
        };
        const result = getBasicEvalContext(config);
        expect(result.uid).toBe(3);
        expect(result.allowed_company_ids).toEqual([1, 2]);
    });

    test("sets current_company_id to first of allowed_company_ids", () => {
        const config = {
            context: { uid: 1, allowed_company_ids: [5, 7] },
        };
        expect(getBasicEvalContext(config).current_company_id).toBe(5);
    });

    test("current_company_id is undefined when allowed_company_ids absent", () => {
        const config = { context: { uid: 1 } };
        const result = getBasicEvalContext(config);
        expect(result.current_company_id).toBe(undefined);
    });

    test("passes context reference through", () => {
        /** @type {{ uid: number, allowed_company_ids: number[] }} */
        const ctx = { uid: 2, allowed_company_ids: [] };
        const config = { context: ctx };
        expect(getBasicEvalContext(config).context).toBe(ctx);
    });
});
