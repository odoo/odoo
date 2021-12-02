/** @odoo-module **/

import { MockServer } from "./helpers/mock_server";

QUnit.module("Mock Server", {
    beforeEach() {
        this.data = {
            models: {
                "res.partner": {
                    fields: {
                        name: {
                            string: "Name",
                            type: "string",
                        },
                        email: {
                            string: "Email",
                            type: "string",
                        },
                        active: {
                            string: "Active",
                            type: "bool",
                            default: true,
                        },
                    },
                    records: [
                        { id: 1, name: "Jean-Michel", email: "jean.michel@example.com" },
                        { id: 2, name: "Raoul", email: "raoul@example.com", active: false },
                    ],
                },
                bar: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "integer",
                            searchable: true,
                            group_operator: "sum",
                        },
                        date: { string: "Date", type: "date", store: true, sortable: true },
                        datetime: {
                            string: "DateTime",
                            type: "datetime",
                            store: true,
                            sortable: true,
                        },
                        partners: { string: "Buddies", type: "many2many", relation: "res.partner" },
                    },
                    records: [
                        {
                            id: 1,
                            foo: 12,
                            date: "2016-12-14",
                            datetime: "2016-12-14 12:34:56",
                            partners: [1, 2],
                        },
                        {
                            id: 2,
                            foo: 1,
                            date: "2016-10-26",
                            datetime: "2016-10-26 12:34:56",
                            partners: [1],
                        },
                        {
                            id: 3,
                            foo: 17,
                            date: "2016-12-15",
                            datetime: "2016-12-15 12:34:56",
                            partners: [2],
                        },
                        { id: 4, foo: 2, date: "2016-04-11", datetime: "2016-04-11 12:34:56" },
                        { id: 5, foo: 0, date: "2016-12-15", datetime: "2016-12-15 12:34:56" },
                        { id: 6, foo: 42, date: "2019-12-30", datetime: "2019-12-30 12:34:56" },
                    ],
                },
            },
        };
    },
});

QUnit.test("performRPC: search with active_test=false", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search",
        args: [[]],
        kwargs: {
            context: { active_test: false },
        },
    });
    assert.deepEqual(result, [1, 2]);
});

QUnit.test("performRPC: search with active_test=true", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search",
        args: [[]],
        kwargs: {
            context: { active_test: true },
        },
    });
    assert.deepEqual(result, [1]);
});

QUnit.test("performRPC: search_read with active_test=false", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
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
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "res.partner",
        method: "search_read",
        args: [[]],
        kwargs: {
            fields: ["name"],
            context: { active_test: true },
        },
    });
    assert.deepEqual(result, [{ id: 1, name: "Jean-Michel" }]);
});

QUnit.test("performRPC: read_group, group by date", async function (assert) {
    assert.expect(10);
    const server = new MockServer(this.data, {});
    let result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date"], //Month by default
        },
    });
    assert.deepEqual(
        result.map((x) => x.date),
        ["December 2016", "October 2016", "April 2016", "December 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [3, 1, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:day"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["date:day"]),
        ["2016-12-14", "2016-10-26", "2016-12-15", "2016-04-11", "2019-12-30"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [1, 1, 2, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:week"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["date:week"]),
        ["W50 2016", "W43 2016", "W15 2016", "W01 2020"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [3, 1, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:quarter"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["date:quarter"]),
        ["Q4 2016", "Q2 2016", "Q4 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [4, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:year"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["date:year"]),
        ["2016", "2019"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [5, 1]
    );
});

QUnit.test("performRPC: read_group, group by datetime", async function (assert) {
    const server = new MockServer(this.data, {});
    let result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime"], //Month by default
        },
    });
    assert.deepEqual(
        result.map((x) => x.datetime),
        ["December 2016", "October 2016", "April 2016", "December 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [3, 1, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:hour"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["datetime:hour"]),
        ["12:00 14 Dec", "12:00 26 Oct", "12:00 15 Dec", "12:00 11 Apr", "12:00 30 Dec"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 1, 2, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:day"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["datetime:day"]),
        ["2016-12-14", "2016-10-26", "2016-12-15", "2016-04-11", "2019-12-30"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 1, 2, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:week"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["datetime:week"]),
        ["W50 2016", "W43 2016", "W15 2016", "W01 2020"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [3, 1, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:quarter"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["datetime:quarter"]),
        ["Q4 2016", "Q2 2016", "Q4 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [4, 1, 1]
    );

    result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:year"],
        },
    });
    assert.deepEqual(
        result.map((x) => x["datetime:year"]),
        ["2016", "2019"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [5, 1]
    );
});

QUnit.test("performRPC: read_group, group by m2m", async function (assert) {
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["partners"],
            domain: [],
            groupby: ["partners"],
        },
    });
    assert.deepEqual(
        result,

        [
            {
                __domain: [["partners", "=", 1]],
                partners: [1, "Jean-Michel"],
                partners_count: 2,
            },
            {
                __domain: [["partners", "=", 2]],
                partners: [2, "Raoul"],
                partners_count: 2,
            },
            {
                __domain: [["partners", "=", false]],
                partners: false,
                partners_count: 3,
            },
        ]
    );
});

QUnit.test("performRPC: read_group, group by integer", async function (assert) {
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["foo"],
        },
    });
    assert.deepEqual(result, [
        {
            __domain: [["foo", "=", 12]],
            foo: 12,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 1]],
            foo: 1,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 17]],
            foo: 17,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 2]],
            foo: 2,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 0]],
            foo: 0,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 42]],
            foo: 42,
            foo_count: 1,
        },
    ]);
});
