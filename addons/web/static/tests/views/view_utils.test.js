// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { computeAggregatedValue } from "@web/views/view_measurements";
import {
    archiveConfirmationProps,
    computeArchiveEnabled,
    drillDownAction,
    drillDownContext,
    drillDownViews,
    getColorIndex,
    getOpenActionParams,
    handleBeforeUnload,
    prepareStaticActionMenuItems,
} from "@web/views/view_utils";

describe.current.tags("headless");

describe("computeAggregatedValue", () => {
    test("sum", () => {
        expect(computeAggregatedValue([], "sum")).toBe(0);
        expect(computeAggregatedValue([7], "sum")).toBe(7);
        expect(computeAggregatedValue([7, 3], "sum")).toBe(10);
        expect(computeAggregatedValue([7.23, 3.1], "sum")).toBe(10.33);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "sum")).toBe(35);
    });

    test("min", () => {
        expect(computeAggregatedValue([], "min")).toBe(Infinity);
        expect(computeAggregatedValue([7], "min")).toBe(7);
        expect(computeAggregatedValue([7, 3], "min")).toBe(3);
        expect(computeAggregatedValue([7.23, 3.1], "min")).toBe(3.1);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "min")).toBe(-5);
    });

    test("max", () => {
        expect(computeAggregatedValue([], "max")).toBe(-Infinity);
        expect(computeAggregatedValue([7], "max")).toBe(7);
        expect(computeAggregatedValue([7, 3], "max")).toBe(7);
        expect(computeAggregatedValue([7.23, 3.1], "max")).toBe(7.23);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "max")).toBe(27);
    });

    test("avg", () => {
        expect(computeAggregatedValue([], "avg")).toBe(NaN);
        expect(computeAggregatedValue([7], "avg")).toBe(7);
        expect(computeAggregatedValue([7, 3], "avg")).toBe(5);
        expect(computeAggregatedValue([7.23, 3.1], "avg")).toBe(5.165);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "avg")).toBe(5);
    });

    test("count", () => {
        expect(computeAggregatedValue([], "count")).toBe(0);
        expect(computeAggregatedValue([7], "count")).toBe(1);
        expect(computeAggregatedValue([7, 3], "count")).toBe(2);
        expect(computeAggregatedValue([7.23, 3.1], "count")).toBe(2);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "count")).toBe(7);
    });

    test("count_distinct", () => {
        expect(computeAggregatedValue([], "count_distinct")).toBe(0);
        expect(computeAggregatedValue([7], "count_distinct")).toBe(1);
        expect(computeAggregatedValue([7, 3], "count_distinct")).toBe(2);
        expect(computeAggregatedValue([7.23, 3.1], "count_distinct")).toBe(2);
        expect(
            computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "count_distinct"),
        ).toBe(5);
    });

    test("invalid aggregator", () => {
        // @ts-expect-error
        expect(() => computeAggregatedValue([])).toThrow(
            "Invalid aggregator 'undefined'",
        );
        // @ts-expect-error
        expect(() => computeAggregatedValue([], "oups")).toThrow(
            "Invalid aggregator 'oups'",
        );
    });
});

describe("computeArchiveEnabled", () => {
    const fields = {
        active: { readonly: false },
        x_active: { readonly: true },
        name: { readonly: false },
    };

    test("presence and readonly both read from fields by default", () => {
        expect(computeArchiveEnabled(fields)).toBe(true);
        expect(computeArchiveEnabled({ active: { readonly: true } })).toBe(false);
        expect(computeArchiveEnabled({ x_active: { readonly: false } })).toBe(true);
        expect(computeArchiveEnabled({ name: { readonly: false } })).toBe(false);
    });

    test("presentIn scopes presence without changing where readonly is read", () => {
        expect(computeArchiveEnabled(fields, { presentIn: { active: {} } })).toBe(true);
        expect(computeArchiveEnabled(fields, { presentIn: { name: {} } })).toBe(false);
        expect(computeArchiveEnabled(fields, { presentIn: { x_active: {} } })).toBe(
            false,
        );
    });

    test("a field present only in presentIn does not throw", () => {
        expect(computeArchiveEnabled({}, { presentIn: { active: {} } })).toBe(false);
    });
});

describe("handleBeforeUnload", () => {
    const makeEvent = () => {
        const ev = {
            prevented: false,
            returnValue: "",
            preventDefault() {
                this.prevented = true;
            },
        };
        return /** @type {BeforeUnloadEvent & { prevented: boolean }} */ (
            /** @type {unknown} */ (ev)
        );
    };
    const record = /** @type {any} */ ({ resId: 1, dirty: true });

    test("beacon branch: successful urgent save does not prompt", async () => {
        const ev = makeEvent();
        await handleBeforeUnload(ev, {
            record,
            inDialog: false,
            useSendBeacon: true,
            urgentSave: () => Promise.resolve(true),
        });
        expect(ev.prevented).toBe(false);
    });

    test("beacon branch: unconfirmed urgent save prompts", async () => {
        const ev = makeEvent();
        await handleBeforeUnload(ev, {
            record,
            inDialog: false,
            useSendBeacon: true,
            urgentSave: () => Promise.resolve(false),
        });
        expect(ev.prevented).toBe(true);
        expect(ev.returnValue).toBe("Unsaved changes");
    });

    test("beacon branch: rejected urgent save prompts", async () => {
        const ev = makeEvent();
        await handleBeforeUnload(ev, {
            record,
            inDialog: false,
            useSendBeacon: true,
            urgentSave: () => Promise.reject(new Error("boom")),
        });
        expect(ev.prevented).toBe(true);
        expect(ev.returnValue).toBe("Unsaved changes");
    });
});

describe("prepareStaticActionMenuItems", () => {
    test("composes the shared presentation with the caller's behaviour", () => {
        const items = prepareStaticActionMenuItems({
            archive: { isAvailable: () => true, callback: () => "archived" },
            delete: { isAvailable: () => false, callback: () => "deleted" },
        });
        expect(items.archive.sequence).toBe(40);
        expect(items.archive.icon).toBe("oi oi-archive");
        expect(items.archive.isAvailable()).toBe(true);
        expect(items.archive.callback()).toBe("archived");
        expect(items.delete.danger).toBe(true);
        expect(items.delete.groupNumber).toBe(COG_GROUP.DANGER);
    });

    test("the caller may override presentation, and an unknown key throws", () => {
        expect(
            prepareStaticActionMenuItems({ delete: { skipSave: true } }).delete
                .skipSave,
        ).toBe(true);
        expect(() => prepareStaticActionMenuItems({ archiv: {} })).toThrow(
            /No static action menu descriptor for "archiv"/,
        );
    });
});

describe("archiveConfirmationProps", () => {
    test("is defaults, so an archiveDialogProps override extends rather than replaces", () => {
        let archived = 0;
        const defaults = archiveConfirmationProps(() => archived++);
        expect(defaults.confirmLabel.toString()).toBe("Archive");
        defaults.confirm();
        expect(archived).toBe(1);

        /** @type {Record<string, any>} */
        const merged = {
            ...archiveConfirmationProps(() => archived++),
            body: "custom",
        };
        expect(merged.body).toBe("custom");
        merged.confirm();
        expect(archived).toBe(2);
    });

    test("the multi variant asks about the selection, the single one about the record", () => {
        expect(archiveConfirmationProps(() => {}).body.toString()).toMatch(
            /this record/,
        );
        expect(
            archiveConfirmationProps(() => {}, { multi: true }).body.toString(),
        ).toMatch(/all the selected records/);
    });
});

describe("getOpenActionParams", () => {
    test("builds the doActionButton payload both views used to build inline", () => {
        let loaded = 0;
        const record = {
            resModel: "foo",
            resId: 3,
            resIds: [3, 4],
            context: { a: 1 },
            model: { root: { load: async () => loaded++ } },
        };
        const params = getOpenActionParams({ action: "act", type: "object" }, record);
        expect(params.name).toBe("act");
        expect(params.type).toBe("object");
        expect(params.resModel).toBe("foo");
        expect(params.resId).toBe(3);
        expect(params.resIds).toEqual([3, 4]);
        expect(params.context).toEqual({ a: 1 });
        params.onClose();
        expect(loaded).toBe(1);
    });
});

describe("drill-down", () => {
    test("drillDownContext drops the report's grouping and default filters, nothing else", () => {
        const context = { group_by: ["a"], search_default_x: 1, lang: "en", uid: 7 };
        expect(drillDownContext(context)).toEqual({ lang: "en", uid: 7 });
        expect(context.group_by).toEqual(["a"]);
    });

    test("drillDownViews keeps the action's list and form ids and falls back to false", () => {
        expect(
            drillDownViews([
                [67, "search"],
                [2, "form"],
                [5, "kanban"],
            ]),
        ).toEqual([
            [false, "list"],
            [2, "form"],
        ]);
        expect(drillDownViews()).toEqual([
            [false, "list"],
            [false, "form"],
        ]);
    });

    test("drillDownAction opens the report's model on the current search view", () => {
        const actionViews = /** @type {Array<[number | false, string]>} */ ([
            [67, "search"],
            [3, "list"],
        ]);
        const views = drillDownViews(actionViews);
        expect(
            drillDownAction({ title: "Foo Analysis", resModel: "foo" }, actionViews, {
                domain: [["bar", "=", 1]],
                views,
                context: { uid: 7 },
            }),
        ).toEqual({
            context: { uid: 7 },
            domain: [["bar", "=", 1]],
            name: "Foo Analysis",
            res_model: "foo",
            search_view_id: [67, "search"],
            target: "current",
            type: "ir.actions.act_window",
            views: [
                [3, "list"],
                [false, "form"],
            ],
        });
    });
});

describe("getColorIndex", () => {
    test("a number wraps into the palette, negatives included", () => {
        expect(getColorIndex(0)).toBe(0);
        expect(getColorIndex(5)).toBe(5);
        expect(getColorIndex(14)).toBe(2);
        expect(getColorIndex(-1)).toBe(11);
        expect(getColorIndex(2.6)).toBe(3);
        expect(getColorIndex(14, 5)).toBe(4);
    });

    test("a string hashes by code points", () => {
        expect(getColorIndex("a")).toBe(97 % 12);
        expect(getColorIndex("ab")).toBe((97 + 98) % 12);
    });

    test("a relational value colours by its id", () => {
        expect(getColorIndex({ id: 14, display_name: "x" })).toBe(2);
        expect(getColorIndex([14, "x"])).toBe(2);
    });

    test("anything else takes slot 0", () => {
        expect(getColorIndex(false)).toBe(0);
        expect(getColorIndex(null)).toBe(0);
        expect(getColorIndex(undefined)).toBe(0);
        expect(getColorIndex({ display_name: "no id" })).toBe(0);
    });
});
