// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { getWebReadGroupParams } from "@web/model/relational_model/read_group_builder";

describe.current.tags("headless");

const FIELDS = {
    id: { name: "id", type: "integer" },
    name: { name: "name", type: "char" },
    stage_id: { name: "stage_id", type: "many2one", relation: "stage" },
    amount: { name: "amount", type: "monetary", aggregator: "sum" },
    qty: { name: "qty", type: "integer", aggregator: "sum" },
};

/** @returns {any} */
function makeConfig(overrides = {}) {
    return {
        resModel: "task",
        fields: { ...FIELDS },
        activeFields: { name: { context: "{}", invisible: "False" } },
        fieldsToAggregate: ["amount", "qty"],
        domain: [],
        groupBy: ["stage_id"],
        orderBy: [{ name: "stage_id", asc: true }],
        context: { lang: "en_US" },
        limit: 80,
        offset: 0,
        groups: {},
        openGroupsByDefault: false,
        ...overrides,
    };
}

const DEPS = { groupByInfo: {}, initialLimit: 80 };

test("aggregates come from the declared scope, not the whole field set", () => {
    const { aggregates } = getWebReadGroupParams(makeConfig(), DEPS);
    expect(aggregates).toInclude("amount:sum");
    expect(aggregates).toInclude("qty:sum");
    expect(aggregates.join(",")).not.toInclude("name:");
});

test("a narrowed fieldsToAggregate narrows the request", () => {
    const { aggregates } = getWebReadGroupParams(
        makeConfig({ fieldsToAggregate: ["qty"] }),
        DEPS,
    );
    expect(aggregates).toEqual(["qty:sum", "qty:count"]);
});

test("an unlimited group list sends no limit rather than MAX_SAFE_INTEGER", () => {
    const { params } = getWebReadGroupParams(
        makeConfig({ limit: Number.MAX_SAFE_INTEGER }),
        DEPS,
    );
    expect(params.limit).toBe(undefined);
    expect(params.offset).toBe(0);
});

test("order is serialised, and the read_group_expand context is added", () => {
    const { params } = getWebReadGroupParams(makeConfig(), DEPS);
    expect(params.order).toBe("stage_id ASC");
    expect(params.context.read_group_expand).toBe(true);
    expect(params.context.lang).toBe("en_US");
});

describe("opening_info", () => {
    test("a folded group reports only its value and folded flag", () => {
        const config = makeConfig({
            groups: {
                7: {
                    fields: FIELDS,
                    groupByFieldName: "stage_id",
                    value: 7,
                    isFolded: true,
                    extraDomain: false,
                    list: { limit: 80, offset: 0 },
                },
            },
        });
        const { params } = getWebReadGroupParams(config, DEPS);
        expect(params.opening_info).toEqual([{ value: 7, folded: true }]);
    });

    test("an open group carries its page so the server returns the same rows", () => {
        const config = makeConfig({
            groups: {
                7: {
                    fields: FIELDS,
                    groupByFieldName: "stage_id",
                    value: 7,
                    isFolded: false,
                    extraDomain: [["amount", ">", 0]],
                    list: { limit: 20, offset: 40, groups: null },
                },
            },
        });
        const { params } = getWebReadGroupParams(config, DEPS);
        expect(params.opening_info).toEqual([
            {
                value: 7,
                folded: false,
                limit: 20,
                offset: 40,
                progressbar_domain: [["amount", ">", 0]],
                groups: null,
            },
        ]);
    });

    test("a many2many groupby keeps the raw value, other types are serialised", () => {
        const m2mFields = {
            ...FIELDS,
            tag_ids: { name: "tag_ids", type: "many2many", relation: "tag" },
        };
        const config = makeConfig({
            fields: m2mFields,
            groupBy: ["tag_ids"],
            orderBy: [],
            groups: {
                3: {
                    fields: m2mFields,
                    groupByFieldName: "tag_ids",
                    value: 3,
                    isFolded: true,
                    extraDomain: false,
                    list: {},
                },
            },
        });
        const { params } = getWebReadGroupParams(config, DEPS);
        expect(params.opening_info).toEqual([{ value: 3, folded: true }]);
    });

    test("nested open groups recurse", () => {
        const config = makeConfig({
            groups: {
                7: {
                    fields: FIELDS,
                    groupByFieldName: "stage_id",
                    value: 7,
                    isFolded: false,
                    extraDomain: false,
                    list: {
                        limit: 80,
                        offset: 0,
                        groups: {
                            9: {
                                fields: FIELDS,
                                groupByFieldName: "stage_id",
                                value: 9,
                                isFolded: true,
                                extraDomain: false,
                                list: {},
                            },
                        },
                    },
                },
            },
        });
        const { params } = getWebReadGroupParams(config, DEPS);
        expect(params.opening_info[0].groups).toEqual([{ value: 9, folded: true }]);
    });
});

test("groupby_read_specification is emitted only for declared groupByInfo", () => {
    const config = makeConfig({ groupBy: ["stage_id"] });
    const withInfo = getWebReadGroupParams(config, {
        initialLimit: 80,
        groupByInfo: {
            stage_id: {
                activeFields: { name: { context: "{}", invisible: "False" } },
                fields: { name: { name: "name", type: "char" } },
            },
        },
    });
    expect(Object.keys(withInfo.params.groupby_read_specification)).toEqual([
        "stage_id",
    ]);

    const withoutInfo = getWebReadGroupParams(config, DEPS);
    expect(withoutInfo.params.groupby_read_specification).toEqual({});
});
