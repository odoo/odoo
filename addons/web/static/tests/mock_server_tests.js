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
                    },
                    records: [
                        { id: 1, foo: 12, date: "2016-12-14" },
                        { id: 2, foo: 1, date: "2016-10-26" },
                        { id: 3, foo: 17, date: "2016-12-15" },
                        { id: 4, foo: 2, date: "2016-04-11" },
                        { id: 5, foo: 22, date: "2016-12-15" },
                        { id: 6, foo: 42, date: "2019-12-30" },
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
    const ids = result.map((record) => record.id);
    assert.deepEqual(ids, [1, 2]);
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
    const ids = result.map((record) => record.id);
    assert.deepEqual(ids, [1]);
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
