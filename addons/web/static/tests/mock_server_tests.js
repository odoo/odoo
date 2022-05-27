/** @odoo-module **/

import { MockServer } from "./helpers/mock_server";

QUnit.module("Mock Server", {
    beforeEach() {
        this.data = {
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
            },
        };
    },
});

QUnit.test("performRPC: search with active_test=false", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
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
    assert.expect(1);
    const server = new MockServer(this.data, {});
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
    assert.expect(1);
    const server = new MockServer(this.data, {});
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
    assert.expect(1);
    const server = new MockServer(this.data, {});
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

QUnit.test("performRPC: name_get with no args", async function (assert) {
    assert.expect(2);
    const server = new MockServer(this.data, {});
    try {
        await server.performRPC("", {
            model: "partner",
            method: "name_get",
            args: [],
            kwargs: {},
        });
    } catch (_) {
        assert.step("name_get failed")
    }
    assert.verifySteps(["name_get failed"])
});

QUnit.test("performRPC: name_get with undefined arg", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "partner",
        method: "name_get",
        args: [undefined],
        kwargs: {},
    });
    assert.deepEqual(result, [])
});

QUnit.test("performRPC: name_get with a single id", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "partner",
        method: "name_get",
        args: [1],
        kwargs: {},
    });
    assert.deepEqual(result, [[1, "Jean-Michel"]]);
});

QUnit.test("performRPC: name_get with array of ids", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "partner",
        method: "name_get",
        args: [[1]],
        kwargs: {},
    });
    assert.deepEqual(result, [[1, "Jean-Michel"]]);
});

QUnit.test("performRPC: name_get with invalid id", async function (assert) {
    assert.expect(2);
    const server = new MockServer(this.data, {});
    try {
        await server.performRPC("", {
            model: "partner",
            method: "name_get",
            args: [11111],
            kwargs: {},
        });
    } catch (_) {
        assert.step("name_get failed")
    }
    assert.verifySteps(["name_get failed"])
});

QUnit.test("performRPC: name_get with id and undefined id", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "partner",
        method: "name_get",
        args: [[undefined, 1]],
        kwargs: {},
    });
    assert.deepEqual(result, [[null, ""], [1, "Jean-Michel"]]);
});

QUnit.test("performRPC: name_get with single id 0", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "partner",
        method: "name_get",
        args: [0],
        kwargs: {},
    });
    assert.deepEqual(result, []);
});

QUnit.test("performRPC: name_get with array of id 0", async function (assert) {
    assert.expect(1);
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "partner",
        method: "name_get",
        args: [[0]],
        kwargs: {},
    });
    assert.deepEqual(result, [[null, ""]]);
});

QUnit.test("performRPC: read_group, group by char", async function (assert) {
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["name"],
            domain: [],
            groupby: ["name"],
        },
    });
    assert.deepEqual(result, [
        { name: "aaa", __domain: [["name", "=", "aaa"]], name_count: 1 },
        { name: "ddd", __domain: [["name", "=", "ddd"]], name_count: 1 },
        { name: "mmm", __domain: [["name", "=", "mmm"]], name_count: 1 },
        { name: "xxx", __domain: [["name", "=", "xxx"]], name_count: 1 },
        { name: "zzz", __domain: [["name", "=", "zzz"]], name_count: 2 },
    ]);
});

QUnit.test("performRPC: read_group, group by boolean", async function (assert) {
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["bool"],
            domain: [],
            groupby: ["bool"],
        },
    });
    assert.deepEqual(result, [
        { bool: false, __domain: [["bool", "=", false]], bool_count: 2 },
        { bool: true, __domain: [["bool", "=", true]], bool_count: 4 },
    ]);
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
        ["April 2016", "October 2016", "December 2016", "December 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [1, 1, 3, 1]
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
        ["2016-04-11", "2016-10-26", "2016-12-14", "2016-12-15", "2019-12-30"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [1, 1, 1, 2, 1]
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
        ["W15 2016", "W43 2016", "W50 2016", "W01 2020"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [1, 1, 3, 1]
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
        ["Q2 2016", "Q4 2016", "Q4 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.date_count),
        [1, 4, 1]
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
        ["April 2016", "October 2016", "December 2016", "December 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 1, 3, 1]
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
        ["12:00 11 Apr", "12:00 26 Oct", "12:00 14 Dec", "12:00 15 Dec", "12:00 30 Dec"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 1, 1, 2, 1]
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
        ["2016-04-11", "2016-10-26", "2016-12-14", "2016-12-15", "2019-12-30"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 1, 1, 2, 1]
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
        ["W15 2016", "W43 2016", "W50 2016", "W01 2020"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 1, 3, 1]
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
        ["Q2 2016", "Q4 2016", "Q4 2019"]
    );
    assert.deepEqual(
        result.map((x) => x.datetime_count),
        [1, 4, 1]
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
            fields: ["partner_ids"],
            domain: [],
            groupby: ["partner_ids"],
        },
    });
    assert.deepEqual(result, [
        { partner_ids: false, __domain: [["partner_ids", "=", false]], partner_ids_count: 3 },
        {
            partner_ids: [1, "Jean-Michel"],
            __domain: [["partner_ids", "=", 1]],
            partner_ids_count: 2,
        },
        { partner_ids: [2, "Raoul"], __domain: [["partner_ids", "=", 2]], partner_ids_count: 2 },
    ]);
});

QUnit.test("performRPC: read_group, group by m2o", async function (assert) {
    this.data.models.partner.fields.sequence = { type: "integer" };
    this.data.models.partner.records[0].sequence = 1;
    this.data.models.partner.records[1].sequence = 0;

    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["partner_id"],
            domain: [],
            groupby: ["partner_id"],
        },
    });
    assert.deepEqual(result, [
        { partner_id: false, __domain: [["partner_id", "=", false]], partner_id_count: 3 },
        { partner_id: [2, "Raoul"], __domain: [["partner_id", "=", 2]], partner_id_count: 1 },
        { partner_id: [1, "Jean-Michel"], __domain: [["partner_id", "=", 1]], partner_id_count: 2 },
    ]);
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
            __domain: [["foo", "=", 0]],
            foo: 0,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 1]],
            foo: 1,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 2]],
            foo: 2,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 12]],
            foo: 12,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 17]],
            foo: 17,
            foo_count: 1,
        },
        {
            __domain: [["foo", "=", 42]],
            foo: 42,
            foo_count: 1,
        },
    ]);
});

QUnit.test("performRPC: read_group, group by selection", async function (assert) {
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["select"],
            domain: [],
            groupby: ["select"],
        },
    });
    assert.deepEqual(result, [
        { select: "new", __domain: [["select", "=", "new"]], select_count: 3 },
        { select: "dev", __domain: [["select", "=", "dev"]], select_count: 1 },
        { select: "done", __domain: [["select", "=", "done"]], select_count: 2 },
    ]);
});

QUnit.test("performRPC: read_group, group by two levels", async function (assert) {
    const server = new MockServer(this.data, {});
    const result = await server.performRPC("", {
        model: "bar",
        method: "read_group",
        args: [[]],
        kwargs: {
            fields: ["bool", "partner_ids"],
            domain: [],
            groupby: ["bool", "partner_ids"],
            lazy: false,
        },
    });
    assert.deepEqual(result, [
        {
            __domain: [
                ["partner_ids", "=", false],
                ["bool", "=", false],
            ],
            __count: 1,
            bool: false,
            partner_ids: false,
        },
        {
            __domain: [
                ["partner_ids", "=", 2],
                ["bool", "=", false],
            ],
            __count: 1,
            bool: false,
            partner_ids: [2, "Raoul"],
        },
        {
            __domain: [
                ["partner_ids", "=", false],
                ["bool", "=", true],
            ],
            __count: 2,
            bool: true,
            partner_ids: false,
        },
        {
            __domain: [
                ["partner_ids", "=", 1],
                ["bool", "=", true],
            ],
            __count: 2,
            bool: true,
            partner_ids: [1, "Jean-Michel"],
        },
        {
            __domain: [
                ["partner_ids", "=", 2],
                ["bool", "=", true],
            ],
            __count: 1,
            bool: true,
            partner_ids: [2, "Raoul"],
        },
    ]);
});
