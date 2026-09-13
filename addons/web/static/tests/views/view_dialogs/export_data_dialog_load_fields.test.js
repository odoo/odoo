// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";

describe.current.tags("headless");

/** @param {{onFetch?: (context: ReturnType<typeof makeContext>) => void}} [options] */
function makeContext({ onFetch } = {}) {
    const ctx = {
        knownFields: {
            partner_id: {
                id: "partner_id",
                string: "Partner",
                params: {},
                field_type: "many2one",
                relation_field: "x",
            },
        },
        expandedFields: {},
        state: { isCompatible: false },
        props: {
            getExportedFields: async () => {
                onFetch?.(ctx);
                return [{ id: "partner_id/name", string: "Name" }];
            },
        },
    };
    return ctx;
}

describe("loadFields", () => {
    test("registers every field it returns", async () => {
        const ctx = makeContext();
        const fields = await ExportDataDialog.prototype.loadFields.call(
            ctx,
            "partner_id",
            false,
        );
        for (const field of fields) {
            expect(ctx.knownFields[field.id]).toBe(field);
        }
        expect(ctx.expandedFields["partner_id"].fields).toBe(fields);
    });

    test("returns nothing when superseded by a compatibility toggle", async () => {
        const ctx = makeContext({
            onFetch: (c) => {
                c.state.isCompatible = true;
            },
        });
        const fields = await ExportDataDialog.prototype.loadFields.call(
            ctx,
            "partner_id",
            false,
        );
        expect(fields).toBe(undefined);
        expect("partner_id/name" in ctx.knownFields).toBe(false);
    });

    test("serves the cached expansion without refetching", async () => {
        const ctx = makeContext();
        ctx.expandedFields["partner_id"] = { fields: [{ id: "cached" }] };
        let fetched = false;
        ctx.props.getExportedFields = async () => {
            fetched = true;
            return [];
        };
        const fields = await ExportDataDialog.prototype.loadFields.call(
            ctx,
            "partner_id",
            false,
        );
        expect(fetched).toBe(false);
        expect(fields.map((f) => f.id)).toEqual(["cached"]);
    });

    test("preventLoad returns nothing and issues no fetch", async () => {
        const ctx = makeContext();
        let fetched = false;
        ctx.props.getExportedFields = async () => {
            fetched = true;
            return [];
        };
        const fields = await ExportDataDialog.prototype.loadFields.call(
            ctx,
            "partner_id",
            true,
        );
        expect(fields).toBe(undefined);
        expect(fetched).toBe(false);
    });
});

test("an old child response cannot populate replacement caches", async () => {
    const pending = new Deferred();
    const ctx = makeContext();
    ctx.props.getExportedFields = () => pending;
    const load = ExportDataDialog.prototype.loadFields.call(ctx, "partner_id");
    ctx.state.isCompatible = true;
    ctx.knownFields = { ...ctx.knownFields };
    ctx.expandedFields = {};
    ctx.state.isCompatible = false;
    pending.resolve([{ id: "partner_id/name", string: "Stale" }]);
    expect(await load).toBe(undefined);
    expect(ctx.expandedFields).toEqual({});
    expect(ctx.knownFields["partner_id/name"]).toBe(undefined);
});

test("an explicit cache target owns both lookup and registration", async () => {
    const ctx = makeContext();
    ctx.expandedFields.partner_id = { fields: [{ id: "stale" }] };
    const target = { knownFields: { ...ctx.knownFields }, expandedFields: {} };
    const result = await ExportDataDialog.prototype.loadFields.call(
        ctx,
        "partner_id",
        false,
        target,
    );
    expect(result.map((field) => field.id)).toEqual(["partner_id/name"]);
    expect(target.expandedFields.partner_id.fields).toBe(result);
    expect(ctx.knownFields["partner_id/name"]).toBe(undefined);
});

test("collapse during expansion ignores the pending response and permits reopening", async () => {
    const pending = new Deferred();
    let calls = 0;
    const ctx = {
        state: { subfields: [] },
        props: {
            isFieldExpandable: () => true,
            loadFields: () => {
                calls++;
                return pending;
            },
        },
    };
    const toggle = ExportDataDialog.components.ExportDataItem.prototype.toggleItem;
    const opening = toggle.call(ctx, "partner_id", true);
    await toggle.call(ctx, "partner_id", true);
    pending.resolve([{ id: "partner_id/name" }]);
    await opening;
    expect(calls).toBe(1);
    expect(ctx.state.subfields).toEqual([]);
    await toggle.call(ctx, "partner_id", true);
    expect(ctx.state.subfields).toEqual([{ id: "partner_id/name" }]);
});
