/** @odoo-module alias=@web/../tests/mock_server_tests default=false */

import { MockServer } from "./helpers/mock_server";

let data;
QUnit.module("MockServer", (hooks) => {
    hooks.beforeEach(() => {
        data = {
            models: {
                partner: {
                    fields: {
                        active: { string: "Active", type: "bool", default: true },
                    },
                    records: [
                        { id: 1, name: "Jean-Michel" },
                        { id: 2, name: "Raoul", active: false },
                    ],
                },
                bar: {
                    fields: {
                        bool: { string: "Boolean", type: "boolean" },
                        date: { string: "Date", type: "date" },
                        datetime: { string: "DateTime", type: "datetime" },
                        foo: { string: "Foo", type: "integer" },
                        partner_id: { string: "Main buddy", type: "many2one", relation: "partner" },
                        partner_ids: { string: "Buddies", type: "many2many", relation: "partner" },
                        select: {
                            string: "Stage",
                            type: "selection",
                            selection: [
                                ["new", "New"],
                                ["dev", "Ongoing"],
                                ["done", "Done"],
                            ],
                        },
                        many2one_field: { type: "many2one", relation: "foo" },
                        one2many_field: {
                            type: "one2many",
                            relation: "foo",
                            inverse_fname_by_model_name: { foo: "many2one_field" },
                        },
                        many2many_field: {
                            type: "many2many",
                            relation: "foo",
                            inverse_fname_by_model_name: { foo: "many2many_field" },
                        },
                        partner_ref: {
                            type: "reference",
                            selection: [["partner", "Partner"]],
                        },
                    },
                    records: [
                        {
                            foo: 12,
                            bool: true,
                            date: "2016-12-14",
                            datetime: "2016-12-14 12:34:56",
                            name: "zzz",
                            partner_ids: [1, 2],
                            select: "dev",
                            partner_ref: "partner,1",
                        },
                        {
                            foo: 1,
                            bool: true,
                            date: "2016-10-26",
                            datetime: "2016-10-26 12:34:56",
                            name: "ddd",
                            partner_id: 2,
                            partner_ids: [1],
                            select: "new",
                            partner_ref: "partner,2",
                        },
                        {
                            foo: 17,
                            bool: false,
                            date: "2016-12-15",
                            datetime: "2016-12-15 12:34:56",
                            name: "xxx",
                            partner_ids: [2],
                            select: "done",
                        },
                        {
                            foo: 2,
                            bool: true,
                            date: "2016-04-11",
                            datetime: "2016-04-11 12:34:56",
                            name: "zzz",
                            partner_id: 1,
                            select: "new",
                        },
                        {
                            foo: 0,
                            bool: false,
                            date: "2016-12-15",
                            datetime: "2016-12-15 12:34:56",
                            name: "aaa",
                            select: "done",
                        },
                        {
                            foo: 42,
                            bool: true,
                            date: "2019-12-30",
                            datetime: "2019-12-30 12:34:56",
                            name: "mmm",
                            partner_id: 1,
                            select: "new",
                        },
                    ],
                },
                foo: {
                    fields: {
                        one2many_field: {
                            type: "one2many",
                            relation: "bar",
                            inverse_fname_by_model_name: { bar: "many2one_field" },
                        },
                        many2one_field: {
                            type: "many2one",
                            relation: "bar",
                            inverse_fname_by_model_name: { bar: "one2many_field" },
                        },
                        many2many_field: {
                            type: "many2many",
                            relation: "bar",
                            inverse_fname_by_model_name: { bar: "many2many_field" },
                        },
                        many2one_reference: {
                            type: "many2one_reference",
                            model_name_ref_fname: "res_model",
                            inverse_fname_by_model_name: { bar: "one2many_field" },
                        },
                        res_model: { type: "char" },
                    },
                    records: [],
                },
            },
        };
    });

    QUnit.test("performRPC: search with active_test=false", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search",
            args: [[]],
            kwargs: {
                context: { active_test: false },
            },
        });
        assert.deepEqual(result, [1, 2]);
    });

    QUnit.test("performRPC: search with active_test=true", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search",
            args: [[]],
            kwargs: {
                context: { active_test: true },
            },
        });
        assert.deepEqual(result, [1]);
    });

    QUnit.test("performRPC: search_read with active_test=false", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search_read",
            args: [[]],
            kwargs: {
                fields: ["name"],
                context: { active_test: false },
            },
        });
        assert.deepEqual(result, [
            { id: 1, name: "Jean-Michel" },
            { id: 2, name: "Raoul" },
        ]);
    });

    QUnit.test("performRPC: search_read with active_test=true", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search_read",
            args: [[]],
            kwargs: {
                fields: ["name"],
                context: { active_test: true },
            },
        });
        assert.deepEqual(result, [{ id: 1, name: "Jean-Michel" }]);
    });

    QUnit.test("performRPC: search_count", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search_count",
            args: [[]],
            kwargs: {},
        });
        assert.deepEqual(result, 1);
    });

    QUnit.test("performRPC: search_count with domain", async function (assert) {
        data.models.partner.records.push({ id: 4, name: "José" });
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search_count",
            args: [[["name", "=", "José"]]],
            kwargs: {},
        });
        assert.deepEqual(result, 1);
    });

    QUnit.test("performRPC: search_count with domain matching no record", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search_count",
            args: [[[0, "=", 1]]],
            kwargs: {},
        });
        assert.deepEqual(result, 0);
    });

    QUnit.test("performRPC: search_count with archived records", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "partner",
            method: "search_count",
            args: [[]],
            kwargs: {
                context: { active_test: false },
            },
        });
        assert.deepEqual(result, 2);
    });

    QUnit.test("performRPC: formatted_read_group, no group", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [["foo", "=", -10]],
                groupby: [],
                aggregates: ["__count"],
            },
        });
        assert.deepEqual(result, [{ __count: 0, __extra_domain: [] }]);
    });

    QUnit.test("performRPC: formatted_read_group, group by char", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [],
                groupby: ["name"],
                aggregates: ["__count"],
            },
        });
        assert.deepEqual(result, [
            { name: "aaa", __extra_domain: [["name", "=", "aaa"]], __count: 1 },
            { name: "ddd", __extra_domain: [["name", "=", "ddd"]], __count: 1 },
            { name: "mmm", __extra_domain: [["name", "=", "mmm"]], __count: 1 },
            { name: "xxx", __extra_domain: [["name", "=", "xxx"]], __count: 1 },
            { name: "zzz", __extra_domain: [["name", "=", "zzz"]], __count: 2 },
        ]);
    });

    QUnit.test("performRPC: formatted_read_group, group by boolean", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [],
                groupby: ["bool"],
                aggregates: ["__count"],
            },
        });
        assert.deepEqual(result, [
            { bool: false, __extra_domain: [["bool", "=", false]], __count: 2 },
            { bool: true, __extra_domain: [["bool", "=", true]], __count: 4 },
        ]);
    });

    QUnit.test("performRPC: formatted_read_group, group by date", async function (assert) {
        const server = new MockServer(data, {});
        let result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [],
                groupby: ["date:month"],
                aggregates: ["__count"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["date:month"][1]),
            ["April 2016", "October 2016", "December 2016", "December 2019"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 3, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["date", ">=", "2016-04-01"],
                    ["date", "<", "2016-05-01"],
                ],
                [
                    ["date", ">=", "2016-10-01"],
                    ["date", "<", "2016-11-01"],
                ],
                [
                    ["date", ">=", "2016-12-01"],
                    ["date", "<", "2017-01-01"],
                ],
                [
                    ["date", ">=", "2019-12-01"],
                    ["date", "<", "2020-01-01"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["date:day"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["date:day"][1]),
            ["2016-04-11", "2016-10-26", "2016-12-14", "2016-12-15", "2019-12-30"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 1, 2, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["date", ">=", "2016-04-11"],
                    ["date", "<", "2016-04-12"],
                ],
                [
                    ["date", ">=", "2016-10-26"],
                    ["date", "<", "2016-10-27"],
                ],
                [
                    ["date", ">=", "2016-12-14"],
                    ["date", "<", "2016-12-15"],
                ],
                [
                    ["date", ">=", "2016-12-15"],
                    ["date", "<", "2016-12-16"],
                ],
                [
                    ["date", ">=", "2019-12-30"],
                    ["date", "<", "2019-12-31"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [],
                aggregates: ["__count"],
                groupby: ["date:week"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["date:week"][1]),
            ["W15 2016", "W43 2016", "W50 2016", "W01 2020"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 3, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["date", ">=", "2016-04-11"],
                    ["date", "<", "2016-04-18"],
                ],
                [
                    ["date", ">=", "2016-10-24"],
                    ["date", "<", "2016-10-31"],
                ],
                [
                    ["date", ">=", "2016-12-12"],
                    ["date", "<", "2016-12-19"],
                ],
                [
                    ["date", ">=", "2019-12-30"],
                    ["date", "<", "2020-01-06"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [],
                aggregates: ["__count"],
                groupby: ["date:quarter"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["date:quarter"][1]),
            ["Q2 2016", "Q4 2016", "Q4 2019"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 4, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["date", ">=", "2016-04-01"],
                    ["date", "<", "2016-07-01"],
                ],
                [
                    ["date", ">=", "2016-10-01"],
                    ["date", "<", "2017-01-01"],
                ],
                [
                    ["date", ">=", "2019-10-01"],
                    ["date", "<", "2020-01-01"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                domain: [],
                groupby: ["date:year"],
                aggregates: ["__count"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["date:year"][1]),
            ["2016", "2019"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [5, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["date", ">=", "2016-01-01"],
                    ["date", "<", "2017-01-01"],
                ],
                [
                    ["date", ">=", "2019-01-01"],
                    ["date", "<", "2020-01-01"],
                ],
            ]
        );
    });

    QUnit.test(
        "performRPC: formatted_read_group, group by date with number granularity",
        async function (assert) {
            const server = new MockServer(data, {});
            const allGranularity = [
                {
                    granularity: "day_of_week",
                    result: [1, 3, 4],
                    count: [2, 2, 2],
                },
                {
                    granularity: "day_of_month",
                    result: [11, 14, 15, 26, 30],
                    count: [1, 1, 2, 1, 1],
                },
                {
                    granularity: "day_of_year",
                    result: [102, 300, 349, 350, 364],
                    count: [1, 1, 1, 2, 1],
                },
                {
                    granularity: "iso_week_number",
                    result: [1, 15, 43, 50],
                    count: [1, 1, 1, 3],
                },
                {
                    granularity: "month_number",
                    result: [4, 10, 12],
                    count: [1, 1, 4],
                },
                {
                    granularity: "quarter_number",
                    result: [2, 4],
                    count: [1, 5],
                },
                {
                    granularity: "year_number",
                    result: [2016, 2019],
                    count: [5, 1],
                },
            ];

            for (const { granularity, result, count } of allGranularity) {
                const response = await server.performRPC("", {
                    model: "bar",
                    method: "formatted_read_group",
                    args: [[]],
                    kwargs: {
                        domain: [],
                        groupby: [`date:${granularity}`],
                        aggregates: ["__count"],
                    },
                });

                assert.deepEqual(
                    response.map((x) => x[`date:${granularity}`]),
                    result
                );
                assert.deepEqual(
                    response.map((x) => x.__count),
                    count
                );
                assert.deepEqual(
                    response.map((x) => x.__extra_domain),
                    result.map((r) => [[`date.${granularity}`, "=", r]])
                );
            }
        }
    );

    QUnit.test("performRPC: formatted_read_group datetime:day_of_week", async function (assert) {
        data.models.bar.records = [
            { foo: 11, datetime: "2025-02-17" }, // Monday
            { foo: 22, datetime: "2025-02-18" }, // Tuesday
            { foo: 33, datetime: "2025-02-19" }, // Wednesday
            { foo: 44, datetime: "2025-02-20" }, // Thursday
            { foo: 55, datetime: "2025-02-21" }, // Friday
            { foo: 66, datetime: "2025-02-22" }, // Saturday
            { foo: 77, datetime: "2025-02-23" }, // Sunday
        ];
        const server = new MockServer(data, {});
        const response = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["foo:sum"],
                domain: [],
                groupby: ["datetime:day_of_week"],
            },
        });
        assert.deepEqual(
            response.map((x) => x["datetime:day_of_week"]),
            [0, 1, 2, 3, 4, 5, 6]
        );
        assert.deepEqual(
            response.map((x) => x["foo:sum"]),
            [77, 11, 22, 33, 44, 55, 66]
        );
    });

    QUnit.test("performRPC: formatted_read_group date:day_of_week", async function (assert) {
        data.models.bar.records = [
            { foo: 11, date: "2025-02-17" }, // Monday
            { foo: 22, date: "2025-02-18" }, // Tuesday
            { foo: 33, date: "2025-02-19" }, // Wednesday
            { foo: 44, date: "2025-02-20" }, // Thursday
            { foo: 55, date: "2025-02-21" }, // Friday
            { foo: 66, date: "2025-02-22" }, // Saturday
            { foo: 77, date: "2025-02-23" }, // Sunday
        ];
        const server = new MockServer(data, {});
        const response = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["foo:sum"],
                domain: [],
                groupby: ["date:day_of_week"],
            },
        });
        assert.deepEqual(
            response.map((x) => x["date:day_of_week"]),
            [0, 1, 2, 3, 4, 5, 6]
        );
        assert.deepEqual(
            response.map((x) => x["foo:sum"]),
            [77, 11, 22, 33, 44, 55, 66]
        );
    });

    QUnit.test("performRPC: formatted_read_group, group by datetime", async function (assert) {
        const server = new MockServer(data, {});
        let result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["datetime:month"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["datetime:month"][1]),
            ["April 2016", "October 2016", "December 2016", "December 2019"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 3, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["datetime", ">=", "2016-03-31 23:00:00"],
                    ["datetime", "<", "2016-04-30 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-09-30 23:00:00"],
                    ["datetime", "<", "2016-10-31 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-11-30 23:00:00"],
                    ["datetime", "<", "2016-12-31 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2019-11-30 23:00:00"],
                    ["datetime", "<", "2019-12-31 23:00:00"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["datetime:hour"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["datetime:hour"][1]),
            ["13:00 11 Apr", "13:00 26 Oct", "13:00 14 Dec", "13:00 15 Dec", "13:00 30 Dec"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 1, 2, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["datetime", ">=", "2016-04-11 12:00:00"],
                    ["datetime", "<", "2016-04-11 13:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-10-26 12:00:00"],
                    ["datetime", "<", "2016-10-26 13:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-12-14 12:00:00"],
                    ["datetime", "<", "2016-12-14 13:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-12-15 12:00:00"],
                    ["datetime", "<", "2016-12-15 13:00:00"],
                ],
                [
                    ["datetime", ">=", "2019-12-30 12:00:00"],
                    ["datetime", "<", "2019-12-30 13:00:00"],
                ],
            ]
        );
        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["datetime:day"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["datetime:day"][1]),
            ["2016-04-11", "2016-10-26", "2016-12-14", "2016-12-15", "2019-12-30"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 1, 2, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["datetime", ">=", "2016-04-10 23:00:00"],
                    ["datetime", "<", "2016-04-11 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-10-25 23:00:00"],
                    ["datetime", "<", "2016-10-26 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-12-13 23:00:00"],
                    ["datetime", "<", "2016-12-14 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-12-14 23:00:00"],
                    ["datetime", "<", "2016-12-15 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2019-12-29 23:00:00"],
                    ["datetime", "<", "2019-12-30 23:00:00"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["datetime:week"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["datetime:week"][1]),
            ["W15 2016", "W43 2016", "W50 2016", "W01 2020"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 1, 3, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["datetime", ">=", "2016-04-10 23:00:00"],
                    ["datetime", "<", "2016-04-17 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-10-23 23:00:00"],
                    ["datetime", "<", "2016-10-30 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-12-11 23:00:00"],
                    ["datetime", "<", "2016-12-18 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2019-12-29 23:00:00"],
                    ["datetime", "<", "2020-01-05 23:00:00"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["datetime:quarter"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["datetime:quarter"][1]),
            ["Q2 2016", "Q4 2016", "Q4 2019"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [1, 4, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["datetime", ">=", "2016-03-31 23:00:00"],
                    ["datetime", "<", "2016-06-30 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2016-09-30 23:00:00"],
                    ["datetime", "<", "2016-12-31 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2019-09-30 23:00:00"],
                    ["datetime", "<", "2019-12-31 23:00:00"],
                ],
            ]
        );

        result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["datetime:year"],
            },
        });
        assert.deepEqual(
            result.map((x) => x["datetime:year"][1]),
            ["2016", "2019"]
        );
        assert.deepEqual(
            result.map((x) => x.__count),
            [5, 1]
        );
        assert.deepEqual(
            result.map((x) => x.__extra_domain),
            [
                [
                    ["datetime", ">=", "2015-12-31 23:00:00"],
                    ["datetime", "<", "2016-12-31 23:00:00"],
                ],
                [
                    ["datetime", ">=", "2018-12-31 23:00:00"],
                    ["datetime", "<", "2019-12-31 23:00:00"],
                ],
            ]
        );
    });

    QUnit.test(
        "performRPC: formatted_read_group, group by datetime with number granularity",
        async function (assert) {
            const server = new MockServer(data, {});
            const allGranularity = [
                {
                    granularity: "second_number",
                    result: [56],
                    count: [6],
                },
                {
                    granularity: "minute_number",
                    result: [34],
                    count: [6],
                },
                {
                    granularity: "hour_number",
                    result: [13],
                    count: [6],
                },
                {
                    granularity: "day_of_week",
                    result: [1, 3, 4],
                    count: [2, 2, 2],
                },
                {
                    granularity: "day_of_month",
                    result: [11, 14, 15, 26, 30],
                    count: [1, 1, 2, 1, 1],
                },
                {
                    granularity: "day_of_year",
                    result: [102, 300, 349, 350, 364],
                    count: [1, 1, 1, 2, 1],
                },
                {
                    granularity: "iso_week_number",
                    result: [1, 15, 43, 50],
                    count: [1, 1, 1, 3],
                },
                {
                    granularity: "month_number",
                    result: [4, 10, 12],
                    count: [1, 1, 4],
                },
                {
                    granularity: "quarter_number",
                    result: [2, 4],
                    count: [1, 5],
                },
                {
                    granularity: "year_number",
                    result: [2016, 2019],
                    count: [5, 1],
                },
            ];

            for (const { granularity, result, count } of allGranularity) {
                const response = await server.performRPC("", {
                    model: "bar",
                    method: "formatted_read_group",
                    args: [[]],
                    kwargs: {
                        aggregates: ["__count"],
                        domain: [],
                        groupby: [`datetime:${granularity}`],
                    },
                });

                assert.deepEqual(
                    response.map((x) => x[`datetime:${granularity}`]),
                    result
                );
                assert.deepEqual(
                    response.map((x) => x.__count),
                    count
                );
                assert.deepEqual(
                    response.map((x) => x.__extra_domain),
                    result.map((r) => [[`datetime.${granularity}`, "=", r]])
                );
            }
        }
    );

    QUnit.test("performRPC: formatted_read_group, group by m2m", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["partner_ids"],
            },
        });
        assert.deepEqual(result, [
            { partner_ids: false, __extra_domain: [["partner_ids", "=", false]], __count: 3 },
            {
                partner_ids: [1, "Jean-Michel"],
                __extra_domain: [["partner_ids", "=", 1]],
                __count: 2,
            },
            {
                partner_ids: [2, "Raoul"],
                __extra_domain: [["partner_ids", "=", 2]],
                __count: 2,
            },
        ]);
    });

    QUnit.test(
        "performRPC: formatted_read_group, order by date with granularity",
        async function (assert) {
            const server = new MockServer(data, {});
            let result = await server.performRPC("", {
                model: "bar",
                method: "formatted_read_group",
                args: [[]],
                kwargs: {
                    aggregates: [],
                    domain: [],
                    groupby: ["date:day"],
                    order: "date:day ASC",
                },
            });
            assert.deepEqual(
                result.map((x) => x["date:day"][1]),
                ["2016-04-11", "2016-10-26", "2016-12-14", "2016-12-15", "2019-12-30"]
            );

            result = await server.performRPC("", {
                model: "bar",
                method: "formatted_read_group",
                args: [[]],
                kwargs: {
                    aggregates: [],
                    domain: [],
                    groupby: ["date:day"],
                    order: "date:day DESC",
                },
            });
            assert.deepEqual(
                result.map((x) => x["date:day"][1]),
                ["2019-12-30", "2016-12-15", "2016-12-14", "2016-10-26", "2016-04-11"]
            );
        }
    );

    QUnit.test("performRPC: formatted_read_group, group by m2o", async function (assert) {
        data.models.partner.fields.sequence = { type: "integer" };
        data.models.partner.records[0].sequence = 1;
        data.models.partner.records[1].sequence = 0;

        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["partner_id"],
            },
        });
        assert.deepEqual(result, [
            { partner_id: false, __extra_domain: [["partner_id", "=", false]], __count: 3 },
            { partner_id: [2, "Raoul"], __extra_domain: [["partner_id", "=", 2]], __count: 1 },
            {
                partner_id: [1, "Jean-Michel"],
                __extra_domain: [["partner_id", "=", 1]],
                __count: 2,
            },
        ]);
    });

    QUnit.test("performRPC: formatted_read_group, group by integer", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["foo"],
            },
        });
        assert.deepEqual(result, [
            {
                __extra_domain: [["foo", "=", 0]],
                foo: 0,
                __count: 1,
            },
            {
                __extra_domain: [["foo", "=", 1]],
                foo: 1,
                __count: 1,
            },
            {
                __extra_domain: [["foo", "=", 2]],
                foo: 2,
                __count: 1,
            },
            {
                __extra_domain: [["foo", "=", 12]],
                foo: 12,
                __count: 1,
            },
            {
                __extra_domain: [["foo", "=", 17]],
                foo: 17,
                __count: 1,
            },
            {
                __extra_domain: [["foo", "=", 42]],
                foo: 42,
                __count: 1,
            },
        ]);
    });

    QUnit.test("performRPC: formatted_read_group, group by selection", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["select"],
            },
        });
        assert.deepEqual(result, [
            { select: "new", __extra_domain: [["select", "=", "new"]], __count: 3 },
            { select: "dev", __extra_domain: [["select", "=", "dev"]], __count: 1 },
            { select: "done", __extra_domain: [["select", "=", "done"]], __count: 2 },
        ]);
    });

    QUnit.test("performRPC: formatted_read_group, group by two levels", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["__count"],
                domain: [],
                groupby: ["bool", "partner_ids"],
            },
        });
        assert.deepEqual(result, [
            {
                __extra_domain: [
                    ["partner_ids", "=", false],
                    ["bool", "=", false],
                ],
                __count: 1,
                bool: false,
                partner_ids: false,
            },
            {
                __extra_domain: [
                    ["partner_ids", "=", 2],
                    ["bool", "=", false],
                ],
                __count: 1,
                bool: false,
                partner_ids: [2, "Raoul"],
            },
            {
                __extra_domain: [
                    ["partner_ids", "=", false],
                    ["bool", "=", true],
                ],
                __count: 2,
                bool: true,
                partner_ids: false,
            },
            {
                __extra_domain: [
                    ["partner_ids", "=", 1],
                    ["bool", "=", true],
                ],
                __count: 2,
                bool: true,
                partner_ids: [1, "Jean-Michel"],
            },
            {
                __extra_domain: [
                    ["partner_ids", "=", 2],
                    ["bool", "=", true],
                ],
                __count: 1,
                bool: true,
                partner_ids: [2, "Raoul"],
            },
        ]);
    });

    QUnit.test(
        "performRPC: formatted_read_group with special measure specifications",
        async function (assert) {
            data.models.bar.fields.float = { string: "Float", type: "float" };
            data.models.bar.records[0].float = 2;
            const server = new MockServer(data, {});
            const result = await server.performRPC("", {
                model: "bar",
                method: "formatted_read_group",
                args: [[]],
                kwargs: {
                    aggregates: ["float:sum", "__count"],
                    domain: [],
                    groupby: ["bool"],
                },
            });
            assert.deepEqual(result, [
                {
                    __count: 2,
                    __extra_domain: [["bool", "=", false]],
                    bool: false,
                    "float:sum": 0,
                },
                {
                    __count: 4,
                    __extra_domain: [["bool", "=", true]],
                    bool: true,
                    "float:sum": 2,
                },
            ]);
        }
    );

    QUnit.test("performRPC: formatted_read_group with array_agg", async function (assert) {
        const server = new MockServer(data, {});
        const aggregateValue = [null, 2, null, 1, null, 1];
        const result2 = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["partner_id:array_agg", "__count"],
                domain: [],
                groupby: [],
            },
        });
        assert.deepEqual(result2, [
            {
                __count: 6,
                __extra_domain: [],
                "partner_id:array_agg": aggregateValue,
            },
        ]);
    });

    QUnit.test("performRPC: formatted_read_group with array_agg on id", async function (assert) {
        const server = new MockServer(data, {});
        const result2 = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["id:array_agg"],
                domain: [["id", "in", [2, 3, 5]]],
                groupby: [],
            },
        });
        assert.deepEqual(result2, [
            {
                __extra_domain: [],
                "id:array_agg": [2, 3, 5],
            },
        ]);
    });

    QUnit.test(
        "performRPC: formatted_read_group with array_agg on an integer field",
        async function (assert) {
            const server = new MockServer(data, {});
            const aggregateValue = [12, 1, 17, 2, 0, 42];
            const result2 = await server.performRPC("", {
                model: "bar",
                method: "formatted_read_group",
                args: [[]],
                kwargs: {
                    aggregates: ["foo:array_agg"],
                    domain: [],
                    groupby: [],
                },
            });
            assert.deepEqual(result2, [
                {
                    __extra_domain: [],
                    "foo:array_agg": aggregateValue,
                },
            ]);
        }
    );

    QUnit.test("performRPC: formatted_read_group with count_distinct", async function (assert) {
        const server = new MockServer(data, {});
        const result2 = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["partner_id:count_distinct", "__count"],
                domain: [],
                groupby: [],
            },
        });
        assert.deepEqual(result2, [
            {
                __count: 6,
                __extra_domain: [],
                "partner_id:count_distinct": 2,
            },
        ]);

        const result3 = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["partner_id:count_distinct"],
                domain: [[0, "=", 1]],
                groupby: [],
            },
        });
        assert.deepEqual(result3, [
            {
                __extra_domain: [],
                "partner_id:count_distinct": 0,
            },
        ]);

        const result4 = await server.performRPC("", {
            model: "bar",
            method: "formatted_read_group",
            args: [[]],
            kwargs: {
                aggregates: ["partner_ref:count_distinct"],
                domain: [],
                groupby: [],
            },
        });
        assert.deepEqual(result4, [
            {
                __extra_domain: [],
                "partner_ref:count_distinct": 2,
            },
        ]);
    });

    QUnit.test("performRPC: read_progress_bar grouped by boolean", async (assert) => {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "read_progress_bar",
            args: [],
            kwargs: {
                domain: [],
                group_by: "bool",
                progress_bar: {
                    colors: { new: "success", dev: "warning", done: "danger" },
                    field: "select",
                },
            },
        });

        assert.deepEqual(result, {
            False: { new: 0, dev: 0, done: 2 },
            True: { new: 3, dev: 1, done: 0 },
        });
    });

    QUnit.test("performRPC: read_progress_bar grouped by datetime", async (assert) => {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "read_progress_bar",
            args: [],
            kwargs: {
                domain: [],
                group_by: "datetime:week",
                progress_bar: {
                    colors: { new: "aaa", dev: "bbb", done: "ccc" },
                    field: "select",
                },
            },
        });

        assert.deepEqual(result, {
            "2019-12-29 23:00:00": { dev: 0, done: 0, new: 1 },
            "2016-04-10 23:00:00": { dev: 0, done: 0, new: 1 },
            "2016-10-23 23:00:00": { dev: 0, done: 0, new: 1 },
            "2016-12-11 23:00:00": { dev: 1, done: 2, new: 0 },
        });
    });

    QUnit.test("many2one_ref should auto fill inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }];
        data.models.foo.records = [
            {
                id: 2,
                res_model: "bar",
                many2one_reference: 1,
            },
        ];
        const mockServer = new MockServer(data);
        assert.deepEqual(mockServer.models.bar.records[0].one2many_field, [2]);

        mockServer.mockUnlink("foo", [2]);
        assert.deepEqual(mockServer.models.bar.records[0].one2many_field, []);
    });

    QUnit.test("many2one should auto fill inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }];
        data.models.foo.records = [
            {
                id: 2,
                many2one_field: 1,
            },
        ];
        const mockServer = new MockServer(data);
        assert.deepEqual(mockServer.models.bar.records[0].one2many_field, [2]);

        mockServer.mockUnlink("foo", [2]);
        assert.deepEqual(mockServer.models.bar.records[0].one2many_field, []);
    });

    QUnit.test("one2many should auto fill inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }, { id: 2 }];
        data.models.foo.records = [
            {
                id: 3,
                one2many_field: [1, 2],
            },
        ];
        const mockServer = new MockServer(data);
        assert.strictEqual(mockServer.models.bar.records[0].many2one_field, 3);
        assert.strictEqual(mockServer.models.bar.records[1].many2one_field, 3);

        mockServer.mockUnlink("foo", [3]);
        assert.strictEqual(mockServer.models.bar.records[0].many2one_field, false);
        assert.strictEqual(mockServer.models.bar.records[1].many2one_field, false);
    });

    QUnit.test("many2many should auto fill inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }];
        data.models.foo.records = [
            {
                id: 2,
                many2many_field: [1],
            },
        ];
        const mockServer = new MockServer(data);
        assert.deepEqual(mockServer.models.bar.records[0].many2many_field, [2]);

        mockServer.mockUnlink("foo", [2]);
        assert.deepEqual(mockServer.models.bar.records[0].many2many_field, []);
    });

    QUnit.test("one2many update should update inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }, { id: 2 }];
        data.models.foo.records = [
            {
                id: 3,
                one2many_field: [1, 2],
            },
        ];
        const mockServer = new MockServer(data);
        mockServer.mockWrite("foo", [[3], { one2many_field: [1] }]);
        assert.strictEqual(mockServer.models.bar.records[0].many2one_field, 3);
        assert.strictEqual(mockServer.models.bar.records[1].many2one_field, false);
    });

    QUnit.test("many2many update should update inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }];
        data.models.foo.records = [
            {
                id: 2,
                many2many_field: [1],
            },
        ];
        const mockServer = new MockServer(data);
        mockServer.mockWrite("foo", [[2], { many2many_field: [] }]); // save nothing
        assert.deepEqual(mockServer.models.bar.records[0].many2many_field, [2]);
    });

    QUnit.test("many2one update should update inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }];
        data.models.foo.records = [
            {
                id: 2,
                many2one_field: 1,
            },
        ];
        const mockServer = new MockServer(data);
        mockServer.mockWrite("foo", [[2], { many2one_field: false }]);
        assert.deepEqual(mockServer.models.bar.records[0].one2many_field, []);
    });

    QUnit.test("many2one_ref update should update inverse field", async function (assert) {
        data.models.bar.records = [{ id: 1 }];
        data.models.foo.records = [
            {
                id: 2,
                res_model: "bar",
                many2one_reference: 1,
            },
        ];
        const mockServer = new MockServer(data);
        mockServer.mockWrite("foo", [[2], { many2one_reference: false }]);
        assert.deepEqual(mockServer.models.bar.records[0].one2many_field, []);
    });

    QUnit.test("webRead sub-fields of a many2one field", async function (assert) {
        data.models.partner.fields.test_name = { string: "Test Name", type: "char" };
        data.models.partner.fields.test_number = { string: "Number", type: "integer" };

        data.models.partner.records = [{ id: 1, test_name: "Jean-Michel", test_number: 5 }];
        data.models.bar.records = [{ id: 1, partner_id: 1 }];

        const mockServer = new MockServer(data);
        const result = mockServer.mockWebRead("bar", [[1]], {
            specification: { partner_id: { fields: { test_name: {}, test_number: {} } } },
        });
        assert.deepEqual(result, [
            { id: 1, partner_id: { id: 1, test_name: "Jean-Michel", test_number: 5 } },
        ]);
    });

    QUnit.test("List View: invisible on processed Arch", async function (assert) {
        data.views = {
            "bar,10001,list": `
                <list>
                    <field name="bool" column_invisible="1"/>
                    <field name="foo"/>
                </list>
            `,
            "bar,10001,search": `<search></search>`,
        };
        const expectedList = `<list>
                    <field name="bool" column_invisible="True"/>
                    <field name="foo"/>
                </list>`;
        const mockServer = new MockServer(data);
        const { views } = mockServer.mockGetViews("bar", { views: [[10001, "list"]], options: {} });
        assert.deepEqual(views.list.arch, expectedList);
    });

    QUnit.test("performRPC: create one record (old API)", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "create",
            args: [{ foo: "A" }],
        });
        assert.strictEqual(result, 7);
        assert.strictEqual(data.models.bar.records.find((r) => r.id === 7).foo, "A");
    });

    QUnit.test("performRPC: create one record (new API)", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "create",
            args: [[{ foo: "A" }]],
        });
        assert.deepEqual(result, [7]);
        assert.strictEqual(data.models.bar.records.find((r) => r.id === 7).foo, "A");
    });

    QUnit.test("performRPC: create several records (new API)", async function (assert) {
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "create",
            args: [[{ foo: "A" }, { foo: "B" }]],
        });
        assert.deepEqual(result, [7, 8]);
        assert.strictEqual(data.models.bar.records.find((r) => r.id === 7).foo, "A");
        assert.strictEqual(data.models.bar.records.find((r) => r.id === 8).foo, "B");
    });

    QUnit.test("performRPC: trigger onchange for new record", async function (assert) {
        data.models.bar.onchanges = {
            foo: (obj) => {
                obj.bool = true;
            },
        };
        const server = new MockServer(data, {});
        const result = await server.performRPC("", {
            model: "bar",
            method: "onchange",
            args: [[], {}, [], { foo: {} }],
        });
        assert.deepEqual(result.value, { foo: 0 });
    });

    QUnit.test(
        "access rights attributes are present on an editable many2one field",
        async function (assert) {
            data.views = {
                "bar,10001,form": `<form>
                    <field name="partner_id"/>
                </form>`,
                "bar,10001,search": `<search></search>`,
            };

            const expectedForm = `<form>
                    <field name="partner_id" can_create="true" can_write="true"/>
                </form>`;
            const mockServer = new MockServer(data);
            const { views } = mockServer.mockGetViews("bar", {
                views: [[10001, "form"]],
                options: {},
            });
            assert.deepEqual(views.form.arch, expectedForm);
        }
    );

    QUnit.test(
        "access rights attributes are missing on an editable many2one field",
        async function (assert) {
            // The access rights attributes should be present,
            // but are actually missing when a field definition is readonly and readonly=0 is on the view.
            // @see the commit description for more details.

            data.models.bar.fields.partner_id.readonly = true;
            data.views = {
                "bar,10001,form": `<form>
                    <field name="partner_id" readonly="0"/>
                </form>`,
                "bar,10001,search": `<search></search>`,
            };

            const expectedForm = `<form>
                    <field name="partner_id" readonly="0"/>
                </form>`;
            const mockServer = new MockServer(data);
            const { views } = mockServer.mockGetViews("bar", {
                views: [[10001, "form"]],
                options: {},
            });
            assert.deepEqual(views.form.arch, expectedForm);
        }
    );
});
