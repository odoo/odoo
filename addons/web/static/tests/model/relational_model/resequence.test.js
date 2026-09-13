// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeTestRelationalModel } from "@web/../tests/model/relational_model/model_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { makeActiveField } from "@web/model/relational_model/field_metadata";
import {
    computeResequencePlan,
    resequenceRecords,
} from "@web/model/relational_model/resequence";

/** @param {{ reject?: boolean }} [opts] */
function makeMockOrm({ reject = false } = {}) {
    const calls = [];
    return {
        calls,
        webResequence: async (model, resIds, params) => {
            if (reject) {
                throw new Error("Server error");
            }
            calls.push({ model, resIds, params });
            return resIds.map((id, i) => ({
                id,
                [params.field_name]: params.offset + i,
            }));
        },
    };
}

function makeRecords(specs) {
    return specs.map(([id, sequence]) => ({ id, sequence }));
}

describe("resequence — move forward", () => {
    test("moves a record from index 0 to index 2", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 10],
            [2, 20],
            [3, 30],
        ]);

        await resequenceRecords({
            records,
            resModel: "product.product",
            orm,
            fieldName: "sequence",
            movedId: 1,
            targetId: 3,
        });

        expect(records[2].id).toBe(1);
        expect(orm.calls.length).toBe(1);
        expect(orm.calls[0].model).toBe("product.product");
    });

    test("moves a record from index 2 to index 0", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 10],
            [2, 20],
            [3, 30],
        ]);

        await resequenceRecords({
            records,
            resModel: "res.partner",
            orm,
            fieldName: "sequence",
            movedId: 3,
            targetId: null,
        });

        expect(records[0].id).toBe(3);
    });

    test("a movedId absent from the list is a no-op (no splice(-1) corruption)", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 10],
            [2, 20],
            [3, 30],
        ]);

        const result = await resequenceRecords({
            records,
            resModel: "product.product",
            orm,
            fieldName: "sequence",
            movedId: 99,
            targetId: 2,
        });

        expect(result).toEqual([]);
        expect(orm.calls.length).toBe(0);
        expect(records.map((r) => r.id)).toEqual([1, 2, 3]);
    });
});

describe("resequence — ORM call parameters", () => {
    test("passes fieldName as field_name param", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 10],
            [2, 20],
        ]);

        await resequenceRecords({
            records,
            resModel: "sale.order",
            orm,
            fieldName: "priority",
            movedId: 2,
            targetId: null,
        });

        expect(orm.calls[0].params.field_name).toBe("priority");
    });

    test("offset is the minimum sequence of affected records", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 5],
            [2, 10],
            [3, 15],
        ]);

        await resequenceRecords({
            records,
            resModel: "product.product",
            orm,
            fieldName: "sequence",
            movedId: 3,
            targetId: null,
        });

        expect(orm.calls[0].params.offset).toBe(5);
    });

    test("passes context to ORM when provided", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 1],
            [2, 2],
        ]);
        const context = { company_id: 1 };

        await resequenceRecords({
            records,
            resModel: "res.partner",
            orm,
            fieldName: "sequence",
            movedId: 2,
            targetId: null,
            context,
        });

        expect(orm.calls[0].params.context).toBe(context);
    });
});

describe("resequence — custom callbacks", () => {
    test("uses custom getSequence to read sequence", async () => {
        const orm = makeMockOrm();
        const records = [
            { id: 1, data: { order: 10 } },
            { id: 2, data: { order: 20 } },
        ];

        await resequenceRecords({
            records,
            resModel: "x",
            orm,
            fieldName: "order",
            movedId: 2,
            targetId: null,
            getSequence: (r) => r.data.order,
        });

        expect(records[0].id).toBe(2);
        expect(orm.calls.length).toBe(1);
    });

    test("uses custom getResId to extract id", async () => {
        const orm = makeMockOrm();
        const records = [
            { id: 1, res_id: 100, sequence: 1 },
            { id: 2, res_id: 200, sequence: 2 },
        ];

        await resequenceRecords({
            records,
            resModel: "x",
            orm,
            fieldName: "sequence",
            movedId: 2,
            targetId: null,
            getResId: (r) => r.res_id,
        });

        expect(orm.calls[0].resIds).toInclude(100);
    });
});

describe("resequence — rollback on ORM error", () => {
    test("restores original order when ORM throws", async () => {
        const orm = makeMockOrm({ reject: true });
        const records = makeRecords([
            [1, 10],
            [2, 20],
            [3, 30],
        ]);
        const originalOrder = records.map((r) => r.id);

        let thrown = false;
        try {
            await resequenceRecords({
                records,
                resModel: "x",
                orm,
                fieldName: "sequence",
                movedId: 1,
                targetId: 3,
            });
        } catch {
            thrown = true;
        }

        expect(thrown).toBe(true);
        expect(records.map((r) => r.id)).toEqual(originalOrder);
    });
});

describe("computeResequencePlan", () => {
    const getSequence = (r) => r.sequence;

    test("partial reorder on monotonic sequences only touches the moved span", () => {
        const records = makeRecords([
            [1, 10],
            [2, 20],
            [3, 30],
            [4, 40],
        ]);

        const plan = computeResequencePlan({
            records,
            movedId: 1,
            targetId: 3,
            getSequence,
        });

        expect(plan.reorderAll).toBe(false);
        expect(plan.toReorder.map((r) => r.id)).toEqual([2, 3, 1]);
        expect(plan.offset).toBe(10);
        expect(plan.fromIndex).toBe(0);
        expect(plan.toIndex).toBe(2);
        expect(records.map((r) => r.id)).toEqual([1, 2, 3, 4]);
    });

    test("non-monotonic (duplicate) sequences force a full reorder", () => {
        const records = makeRecords([
            [1, 10],
            [2, 10],
            [3, 10],
        ]);

        const plan = computeResequencePlan({
            records,
            movedId: 3,
            targetId: null,
            getSequence,
        });

        expect(plan.reorderAll).toBe(true);
        expect(plan.toReorder.map((r) => r.id)).toEqual([3, 1, 2]);
    });

    test("a record with an undefined sequence forces a full reorder", () => {
        const records = [{ id: 1, sequence: 10 }, { id: 2 }, { id: 3, sequence: 30 }];

        const plan = computeResequencePlan({
            records,
            movedId: 3,
            targetId: 1,
            getSequence,
        });

        expect(plan.reorderAll).toBe(true);
        expect(plan.toReorder.length).toBe(3);
    });

    test("offset ignores null/NaN sequence values", () => {
        const records = [
            { id: 1, sequence: null },
            { id: 2, sequence: 7 },
            { id: 3, sequence: 12 },
        ];

        const plan = computeResequencePlan({
            records,
            movedId: 3,
            targetId: null,
            getSequence,
        });

        expect(plan.offset).toBe(7);
    });

    test("offset falls back to 0 when no record has a numeric sequence", () => {
        const records = [{ id: 1 }, { id: 2 }];

        const plan = computeResequencePlan({
            records,
            movedId: 2,
            targetId: null,
            getSequence,
        });

        expect(plan.offset).toBe(0);
    });

    test("descending order reverses the write order", () => {
        const records = makeRecords([
            [1, 30],
            [2, 20],
            [3, 10],
        ]);

        const plan = computeResequencePlan({
            records,
            movedId: 1,
            targetId: 2,
            getSequence,
            asc: false,
        });

        expect(plan.reorderAll).toBe(false);
        expect(plan.toReorder.map((r) => r.id)).toEqual([1, 2]);
        expect(plan.offset).toBe(20);
    });
});

describe("resequence — descending order", () => {
    test("asc=false reverses the sequence direction", async () => {
        const orm = makeMockOrm();
        const records = makeRecords([
            [1, 30],
            [2, 20],
            [3, 10],
        ]);

        await resequenceRecords({
            records,
            resModel: "x",
            orm,
            fieldName: "sequence",
            movedId: 1,
            targetId: 3,
            asc: false,
        });

        expect(orm.calls.length).toBe(1);
    });
});

describe("resequence stale drag inputs", () => {
    /** @type {[string, number[][], number, number | null][]} */
    const cases = [
        ["empty list", [], 99, null],
        [
            "missing source",
            [
                [1, 10],
                [2, 20],
            ],
            99,
            1,
        ],
        [
            "missing target",
            [
                [1, 10],
                [2, 20],
            ],
            2,
            99,
        ],
    ];
    for (const [name, specs, movedId, targetId] of cases) {
        test(`${name} leaves the list and server untouched`, async () => {
            const records = makeRecords(specs);
            const orm = makeMockOrm();
            const plan = computeResequencePlan({
                records,
                movedId,
                targetId,
                getSequence: (r) => r.sequence,
            });
            expect(plan.toReorder).toEqual([]);
            const result = await resequenceRecords({
                records,
                movedId,
                targetId,
                orm,
                resModel: "x",
                fieldName: "sequence",
            });
            expect(result).toEqual([]);
            expect(orm.calls).toEqual([]);
            expect(records).toEqual(makeRecords(specs));
        });
    }
});

test("descending full reorder keeps display order opposite to ascending server writes", async () => {
    const records = makeRecords([
        [1, 10],
        [2, 10],
        [3, 10],
    ]);
    const orm = makeMockOrm();
    const result = await resequenceRecords({
        records,
        orm,
        resModel: "x",
        fieldName: "sequence",
        movedId: 3,
        targetId: null,
        asc: false,
    });
    expect(records.map((r) => r.id)).toEqual([3, 1, 2]);
    expect(orm.calls[0].resIds).toEqual([2, 1, 3]);
    const sequences = new Map(result.map((r) => [r.id, r.sequence]));
    expect(records.map((r) => sequences.get(r.id))).toEqual([12, 11, 10]);
});

for (const span of [2, 64]) {
    test(`applying a ${span}-row resequence stops indexing after its last result`, async () => {
        const model = await makeTestRelationalModel({});
        model.orm = { ...model.orm, ...makeMockOrm() };
        const size = 64;
        let lookups = 0;
        class CountingList extends DynamicRecordList {
            _getDPresId(record) {
                lookups++;
                return super._getDPresId(record);
            }
        }
        const list = new CountingList(
            model,
            {
                ...model.config,
                fields: { sequence: { name: "sequence", type: "integer" } },
                activeFields: { sequence: makeActiveField({ isHandle: true }) },
                orderBy: [{ name: "sequence", asc: true }],
            },
            {
                records: Array.from({ length: size }, (_, index) => ({
                    id: index + 1,
                    sequence: index + 1,
                })),
                length: size,
            },
        );
        await list.resequence(list.records[0].id, list.records[span - 1].id);
        expect(list.records.map((r) => r.resId)).toEqual([
            ...Array.from({ length: span - 1 }, (_, index) => index + 2),
            1,
            ...Array.from({ length: size - span }, (_, index) => index + span + 1),
        ]);
        expect(list.records.map((r) => r.data.sequence)).toEqual(
            Array.from({ length: size }, (_, index) => index + 1),
        );
        expect(lookups).toBeLessThan(span * 3);
        makeLogger("web.model.audit").logic("resequence id lookups", {
            rows: size,
            span,
            lookups,
        });
    });
}

test("all small integer resequences agree with remove-and-insert after server sorting", async () => {
    let cases = 0;
    for (const asc of [true, false]) {
        for (const sequences of [
            [1, 2, 3, 4],
            [10, 20, 30, 40],
            [10, 10, 10, 10],
            [4, 1, 3, 2],
        ]) {
            const initial = asc ? sequences : [...sequences].reverse();
            for (const movedId of [1, 2, 3, 4]) {
                for (const targetId of [null, 1, 2, 3, 4]) {
                    const records = initial.map((sequence, i) => ({
                        id: i + 1,
                        sequence,
                    }));
                    const expected = records.map((r) => r.id);
                    if (targetId !== movedId) {
                        expected.splice(expected.indexOf(movedId), 1);
                        expected.splice(
                            targetId === null ? 0 : expected.indexOf(targetId) + 1,
                            0,
                            movedId,
                        );
                    }
                    const result = await resequenceRecords({
                        records,
                        orm: makeMockOrm(),
                        resModel: "x",
                        fieldName: "sequence",
                        movedId,
                        targetId,
                        asc,
                    });
                    for (const values of result) {
                        Object.assign(
                            records.find((r) => r.id === values.id),
                            values,
                        );
                    }
                    expect(records.map((r) => r.id)).toEqual(expected);
                    expect(
                        [...records]
                            .sort((a, b) => (asc ? 1 : -1) * (a.sequence - b.sequence))
                            .map((r) => r.id),
                    ).toEqual(expected);
                    cases++;
                }
            }
        }
    }
    makeLogger("web.model.audit").logic("resequence independent ordering oracle", {
        cases,
    });
});
