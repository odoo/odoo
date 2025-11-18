import { describe, expect, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    makeMockServer,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { ConnectionLostError, rpc } from "@web/core/network/rpc";

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char();
    active = fields.Boolean({ default: true });

    _records = [
        {
            id: 1,
            name: "Jean-Michel",
        },
        {
            id: 2,
            name: "Raoul",
            active: false,
        },
    ];
}

class Bar extends models.Model {
    _name = "bar";

    name = fields.Char();
    bool = fields.Boolean();
    date = fields.Date();
    datetime = fields.Datetime();
    foo = fields.Integer();
    partner_id = fields.Many2one({ string: "Main buddy", relation: "res.partner" });
    partner_ids = fields.Many2many({ string: "Buddies", relation: "res.partner" });
    select = fields.Selection({
        string: "Stage",
        selection: [
            ["new", "New"],
            ["dev", "Ongoing"],
            ["done", "Done"],
        ],
    });
    many2one_field = fields.Many2one({ relation: "foo" });
    one2many_field = fields.One2many({
        relation: "foo",
        inverse_fname_by_model_name: { foo: "many2one_field" },
    });
    many2many_field = fields.Many2many({
        relation: "foo",
        inverse_fname_by_model_name: { foo: "many2many_field" },
    });
    partner_ref = fields.Reference({ selection: [["res.partner", "Partner"]] });

    _records = [
        {
            foo: 12,
            bool: true,
            date: "2016-12-14",
            datetime: "2016-12-14 12:34:56",
            name: "zzz",
            partner_ids: [1, 2],
            select: "dev",
            partner_ref: "res.partner,1",
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
            partner_ref: "res.partner,2",
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
    ];
}

class Foo extends models.Model {
    _name = "foo";

    one2many_field = fields.One2many({
        relation: "bar",
        inverse_fname_by_model_name: { bar: "many2one_field" },
    });
    many2one_field = fields.Many2one({
        relation: "bar",
        inverse_fname_by_model_name: { bar: "one2many_field" },
    });
    many2many_field = fields.Many2many({
        relation: "bar",
        inverse_fname_by_model_name: { bar: "many2many_field" },
    });
    many2one_reference = fields.Many2oneReference({
        model_field: "res_model",
        relation: "bar",
        inverse_fname_by_model_name: { bar: "one2many_field" },
        model_name_ref_fname: "res_model",
    });
    res_model = fields.Char();
}

defineModels([Partner, Bar, Foo]);

/**
 * @param {{
 *  model: string;
 *  method: string;
 *  args: any[];
 *  kwargs: Record<string, any>;
 *  [key: string]: any;
 * }} params
 */
function fetchCallKw(params) {
    return fetch(`/web/dataset/call_kw/${params.model}/${params.method}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            id: nextJsonRpcId++,
            jsonrpc: "2.0",
            method: "call",
            params: {
                args: [],
                kwargs: {},
                ...params,
            },
        }),
    });
}

/**
 * @param {{
 *  model: string;
 *  method: string;
 *  args: any[];
 *  kwargs: Record<string, any>;
 *  [key: string]: any;
 * }} params
 */
const ormRequest = async (params) => {
    const response = await fetchCallKw(params);
    const { error, result } = await response.json();
    if (error) {
        console.error(error);
        throw error;
    }
    return result;
};

/**
 * Minimal parameters to have a request considered as a JSON-RPC request
 */
const JSON_RPC_BASIC_PARAMS = {
    body: "{}",
    headers: {
        ["Content-Type"]: "application/json",
    },
};
let nextJsonRpcId = 0;

describe.current.tags("headless");

test("onRpc: normal result", async () => {
    onRpc("/get_result", () => "result");

    await makeMockServer();

    const response = await fetch("/get_result");

    expect(response).toBeInstanceOf(Response);

    await expect(response.text()).resolves.toBe("result");
});

test("onRpc: error handling", async () => {
    onRpc("/boom", () => {
        throw new Error("boom");
    });

    await makeMockServer();

    await expect(fetch("/boom")).rejects.toThrow("boom");
});

test("onRpc: pure, normal result", async () => {
    onRpc("/get_result", () => "result", { pure: true });

    await makeMockServer();

    const response = await fetch("/get_result");

    expect(response).toBeInstanceOf(Response);

    await expect(response.text()).resolves.toBe("result");
});

test("onRpc: pure, error handling", async () => {
    onRpc(
        "/boom",
        () => {
            throw new Error("boom");
        },
        { pure: true }
    );

    await makeMockServer();

    await expect(fetch("/boom")).rejects.toThrow("boom");
});

test("onRpc: JSON-RPC normal result", async () => {
    onRpc("/get_result", () => "get_result value");

    await makeMockServer();

    const response = await fetch("/get_result", JSON_RPC_BASIC_PARAMS);

    expect(response).toBeInstanceOf(Response);

    const result = await response.json();
    expect(result).toMatchObject({
        result: "get_result value",
    });
    expect(result).not.toInclude("error");
});

test("onRpc: JSON-RPC error handling", async () => {
    class CustomError extends Error {
        name = "CustomError";
    }

    onRpc("/boom", () => {
        throw new CustomError("boom");
    });

    await makeMockServer();

    const response = await fetch("/boom", JSON_RPC_BASIC_PARAMS);

    expect(response).toBeInstanceOf(Response);

    const result = await response.json();
    expect(result).not.toInclude("result");
    expect(result).toMatchObject({
        error: {
            code: 200,
            data: {
                name: "CustomError",
                message: "boom",
            },
            message: "boom",
            type: "server",
        },
    });
});

test("rpc: calls on mock server", async () => {
    onRpc("/route", () => "pure route response");
    onRpc("http://pure.route.com/", () => "external route response");
    onRpc("/boom", () => {
        throw new Error("Boom");
    });
    onRpc(
        "/boom/pure",
        () => {
            throw new Error("Pure boom");
        },
        { pure: true }
    );
    await makeMockServer();

    await expect(rpc("/route")).resolves.toBe("pure route response");
    await expect(rpc("http://pure.route.com/")).resolves.toBe("external route response");

    await expect(rpc("/boom")).rejects.toThrow("RPC_ERROR: Boom");
    await expect(rpc("/boom/pure")).rejects.toThrow(ConnectionLostError);

    // MockServer error handling with 'rpc'
    await expect(rpc("/unknown/route")).rejects.toThrow(
        "Unimplemented server route: /unknown/route"
    );
    await expect(rpc("https://unknown.route")).rejects.toThrow(
        "Unimplemented server external URL: https://unknown.route"
    );
    await expect(
        rpc("/web/dataset/call_kw/fake.model/fake_method", {
            model: "fake.model",
            method: "fake_method",
        })
    ).rejects.toThrow(
        `Cannot find a definition for model "fake.model": could not get model from server environment`
    );
});

test("performRPC: custom response", async () => {
    const customResponse = new Response("{}", { status: 418 });
    onRpc(() => customResponse);
    await makeMockServer();
    await expect(fetchCallKw({})).resolves.toBe(customResponse);
});

test("performRPC: search with active_test=false", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search",
        kwargs: {
            context: { active_test: false },
        },
    });

    expect(result).toEqual([1, 2]);
});

test("performRPC: search with active_test=true", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search",
        kwargs: {
            context: { active_test: true },
        },
    });
    expect(result).toEqual([1]);
});

test("performRPC: search_read with active_test=false", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search_read",
        kwargs: {
            fields: ["name"],
            context: { active_test: false },
        },
    });
    expect(result).toEqual([
        { id: 1, name: "Jean-Michel" },
        { id: 2, name: "Raoul" },
    ]);
});

test("performRPC: search_read with active_test=true", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search_read",
        kwargs: {
            fields: ["name"],
            context: { active_test: true },
        },
    });
    expect(result).toEqual([{ id: 1, name: "Jean-Michel" }]);
});

test("performRPC: search_count", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search_count",
    });
    expect(result).toBe(1);
});

test("performRPC: search_count with domain", async () => {
    Partner._records.push({ id: 4, name: "José" });

    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search_count",
        args: [[["name", "=", "José"]]],
    });
    expect(result).toBe(1);
});

test("performRPC: search_count with domain matching no record", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search_count",
        args: [[[0, "=", 1]]],
    });
    expect(result).toBe(0);
});

test("performRPC: search_count with archived records", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "res.partner",
        method: "search_count",
        kwargs: {
            context: { active_test: false },
        },
    });
    expect(result).toBe(2);
});

test("performRPC: read_group, no group", async function (assert) {
    await makeMockServer();
    const result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo:count"],
            domain: [["foo", "=", -10]],
            groupby: [],
        },
    });
    expect(result).toEqual([{ __count: 0, foo: false, __domain: [["foo", "=", -10]] }]);
});

test("performRPC: read_group, group by char", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["name"],
            domain: [],
            groupby: ["name"],
        },
    });
    expect(result).toEqual([
        { name: "aaa", __domain: [["name", "=", "aaa"]], name_count: 1 },
        { name: "ddd", __domain: [["name", "=", "ddd"]], name_count: 1 },
        { name: "mmm", __domain: [["name", "=", "mmm"]], name_count: 1 },
        { name: "xxx", __domain: [["name", "=", "xxx"]], name_count: 1 },
        { name: "zzz", __domain: [["name", "=", "zzz"]], name_count: 2 },
    ]);
});

test("performRPC: read_group, group by boolean", async () => {
    await makeMockServer();
    const result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["bool"],
            domain: [],
            groupby: ["bool"],
        },
    });
    expect(result).toEqual([
        { bool: false, __domain: [["bool", "=", false]], bool_count: 2 },
        { bool: true, __domain: [["bool", "=", true]], bool_count: 4 },
    ]);
});

test("performRPC: read_group, group by date", async () => {
    await makeMockServer();
    let result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date"], //Month by default
        },
    });

    expect(result.map((x) => x.date)).toEqual([
        "April 2016",
        "October 2016",
        "December 2016",
        "December 2019",
    ]);
    expect(result.map((x) => x.date_count)).toEqual([1, 1, 3, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["date"])).toEqual([
        { from: "2016-04-01", to: "2016-05-01" },
        { from: "2016-10-01", to: "2016-11-01" },
        { from: "2016-12-01", to: "2017-01-01" },
        { from: "2019-12-01", to: "2020-01-01" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:day"],
        },
    });

    expect(result.map((x) => x["date:day"])).toEqual([
        "2016-04-11",
        "2016-10-26",
        "2016-12-14",
        "2016-12-15",
        "2019-12-30",
    ]);
    expect(result.map((x) => x.date_count)).toEqual([1, 1, 1, 2, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["date:day"])).toEqual([
        { from: "2016-04-11", to: "2016-04-12" },
        { from: "2016-10-26", to: "2016-10-27" },
        { from: "2016-12-14", to: "2016-12-15" },
        { from: "2016-12-15", to: "2016-12-16" },
        { from: "2019-12-30", to: "2019-12-31" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:week"],
        },
    });

    expect(result.map((x) => x["date:week"])).toEqual([
        "W15 2016",
        "W43 2016",
        "W50 2016",
        "W01 2020",
    ]);
    expect(result.map((x) => x.date_count)).toEqual([1, 1, 3, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["date:week"])).toEqual([
        { from: "2016-04-11", to: "2016-04-18" },
        { from: "2016-10-24", to: "2016-10-31" },
        { from: "2016-12-12", to: "2016-12-19" },
        { from: "2019-12-30", to: "2020-01-06" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:quarter"],
        },
    });

    expect(result.map((x) => x["date:quarter"])).toEqual(["Q2 2016", "Q4 2016", "Q4 2019"]);
    expect(result.map((x) => x.date_count)).toEqual([1, 4, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["date:quarter"])).toEqual([
        { from: "2016-04-01", to: "2016-07-01" },
        { from: "2016-10-01", to: "2017-01-01" },
        { from: "2019-10-01", to: "2020-01-01" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:year"],
        },
    });

    expect(result.map((x) => x["date:year"])).toEqual(["2016", "2019"]);
    expect(result.map((x) => x.date_count)).toEqual([5, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
        [
            ["date", ">=", "2016-01-01"],
            ["date", "<", "2017-01-01"],
        ],
        [
            ["date", ">=", "2019-01-01"],
            ["date", "<", "2020-01-01"],
        ],
    ]);
    expect(result.map((x) => x.__range["date:year"])).toEqual([
        { from: "2016-01-01", to: "2017-01-01" },
        { from: "2019-01-01", to: "2020-01-01" },
    ]);
});

test("performRPC: read_group, group by date with number granularity", async () => {
    await makeMockServer();

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
        const response = await ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["foo"],
                domain: [],
                groupby: [`date:${granularity}`],
            },
        });

        expect(response.map((x) => x[`date:${granularity}`])).toEqual(result);
        expect(response.map((x) => x.date_count)).toEqual(count);
        expect(response.map((x) => x.__domain)).toEqual(
            result.map((r) => [[`date.${granularity}`, "=", r]])
        );
    }
});

test("performRPC: read_group, group by datetime", async () => {
    await makeMockServer();
    let result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime"], //Month by default
        },
    });

    expect(result.map((x) => x.datetime)).toEqual([
        "April 2016",
        "October 2016",
        "December 2016",
        "December 2019",
    ]);
    expect(result.map((x) => x.datetime_count)).toEqual([1, 1, 3, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["datetime"])).toEqual([
        { from: "2016-03-31 23:00:00", to: "2016-04-30 23:00:00" },
        { from: "2016-09-30 23:00:00", to: "2016-10-31 23:00:00" },
        { from: "2016-11-30 23:00:00", to: "2016-12-31 23:00:00" },
        { from: "2019-11-30 23:00:00", to: "2019-12-31 23:00:00" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:hour"],
        },
    });

    expect(result.map((x) => x["datetime:hour"])).toEqual([
        "13:00 11 Apr",
        "13:00 26 Oct",
        "13:00 14 Dec",
        "13:00 15 Dec",
        "13:00 30 Dec",
    ]);
    expect(result.map((x) => x.datetime_count)).toEqual([1, 1, 1, 2, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["datetime:hour"])).toEqual([
        { from: "2016-04-11 12:00:00", to: "2016-04-11 13:00:00" },
        { from: "2016-10-26 12:00:00", to: "2016-10-26 13:00:00" },
        { from: "2016-12-14 12:00:00", to: "2016-12-14 13:00:00" },
        { from: "2016-12-15 12:00:00", to: "2016-12-15 13:00:00" },
        { from: "2019-12-30 12:00:00", to: "2019-12-30 13:00:00" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:day"],
        },
    });

    expect(result.map((x) => x["datetime:day"])).toEqual([
        "2016-04-11",
        "2016-10-26",
        "2016-12-14",
        "2016-12-15",
        "2019-12-30",
    ]);
    expect(result.map((x) => x.datetime_count)).toEqual([1, 1, 1, 2, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["datetime:day"])).toEqual([
        { from: "2016-04-10 23:00:00", to: "2016-04-11 23:00:00" },
        { from: "2016-10-25 23:00:00", to: "2016-10-26 23:00:00" },
        { from: "2016-12-13 23:00:00", to: "2016-12-14 23:00:00" },
        { from: "2016-12-14 23:00:00", to: "2016-12-15 23:00:00" },
        { from: "2019-12-29 23:00:00", to: "2019-12-30 23:00:00" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:week"],
        },
    });

    expect(result.map((x) => x["datetime:week"])).toEqual([
        "W15 2016",
        "W43 2016",
        "W50 2016",
        "W01 2020",
    ]);
    expect(result.map((x) => x.datetime_count)).toEqual([1, 1, 3, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["datetime:week"])).toEqual([
        { from: "2016-04-10 23:00:00", to: "2016-04-17 23:00:00" },
        { from: "2016-10-23 23:00:00", to: "2016-10-30 23:00:00" },
        { from: "2016-12-11 23:00:00", to: "2016-12-18 23:00:00" },
        { from: "2019-12-29 23:00:00", to: "2020-01-05 23:00:00" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:quarter"],
        },
    });

    expect(result.map((x) => x["datetime:quarter"])).toEqual(["Q2 2016", "Q4 2016", "Q4 2019"]);
    expect(result.map((x) => x.datetime_count)).toEqual([1, 4, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
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
    ]);
    expect(result.map((x) => x.__range["datetime:quarter"])).toEqual([
        { from: "2016-03-31 23:00:00", to: "2016-06-30 23:00:00" },
        { from: "2016-09-30 23:00:00", to: "2016-12-31 23:00:00" },
        { from: "2019-09-30 23:00:00", to: "2019-12-31 23:00:00" },
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["datetime:year"],
        },
    });

    expect(result.map((x) => x["datetime:year"])).toEqual(["2016", "2019"]);
    expect(result.map((x) => x.datetime_count)).toEqual([5, 1]);
    expect(result.map((x) => x.__domain)).toEqual([
        [
            ["datetime", ">=", "2015-12-31 23:00:00"],
            ["datetime", "<", "2016-12-31 23:00:00"],
        ],
        [
            ["datetime", ">=", "2018-12-31 23:00:00"],
            ["datetime", "<", "2019-12-31 23:00:00"],
        ],
    ]);
    expect(result.map((x) => x.__range["datetime:year"])).toEqual([
        { from: "2015-12-31 23:00:00", to: "2016-12-31 23:00:00" },
        { from: "2018-12-31 23:00:00", to: "2019-12-31 23:00:00" },
    ]);
});

test("performRPC: read_group, group by datetime with number granularity", async () => {
    await makeMockServer();

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
        const response = await ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["foo"],
                domain: [],
                groupby: [`datetime:${granularity}`],
            },
        });

        expect(response.map((x) => x[`datetime:${granularity}`])).toEqual(result);
        expect(response.map((x) => x.datetime_count)).toEqual(count);
        expect(response.map((x) => x.__domain)).toEqual(
            result.map((r) => [[`datetime.${granularity}`, "=", r]])
        );
    }
});

test("performRPC: read_group day_of_week", async () => {
    Bar._records = [
        { foo: 11, datetime: "2025-02-17 13:00:00" }, // Monday
        { foo: 22, datetime: "2025-02-18 13:00:00" }, // Tuesday
        { foo: 33, datetime: "2025-02-19 13:00:00" }, // Wednesday
        { foo: 44, datetime: "2025-02-20 13:00:00" }, // Thursday
        { foo: 55, datetime: "2025-02-21 13:00:00" }, // Friday
        { foo: 66, datetime: "2025-02-22 13:00:00" }, // Saturday
        { foo: 77, datetime: "2025-02-23 13:00:00" }, // Sunday
    ];
    await makeMockServer();

    const response = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo:max"],
            domain: [],
            groupby: ["datetime:day_of_week"],
        },
    });

    expect(response.map((x) => x["datetime:day_of_week"])).toEqual([0, 1, 2, 3, 4, 5, 6]);
    expect(response.map((x) => x.foo)).toEqual([77, 11, 22, 33, 44, 55, 66]);
});

test("performRPC: read_group, group by m2m", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["partner_ids"],
                domain: [],
                groupby: ["partner_ids"],
            },
        })
    ).resolves.toEqual([
        {
            partner_ids: [1, "Jean-Michel"],
            __domain: [["partner_ids", "=", 1]],
            partner_ids_count: 2,
        },
        {
            partner_ids: [2, "Raoul"],
            __domain: [["partner_ids", "=", 2]],
            partner_ids_count: 2,
        },
        {
            partner_ids: false,
            __domain: [["partner_ids", "=", false]],
            partner_ids_count: 3,
        },
    ]);
});

test("performRPC: read_group, order by date with granularity", async () => {
    await makeMockServer();
    let result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:day"],
            orderby: "date:day ASC",
        },
    });
    expect(result.map((x) => x["date:day"])).toEqual([
        "2016-04-11",
        "2016-10-26",
        "2016-12-14",
        "2016-12-15",
        "2019-12-30",
    ]);

    result = await ormRequest({
        model: "bar",
        method: "read_group",
        kwargs: {
            fields: ["foo"],
            domain: [],
            groupby: ["date:day"],
            orderby: "date:day DESC",
        },
    });
    expect(result.map((x) => x["date:day"])).toEqual([
        "2019-12-30",
        "2016-12-15",
        "2016-12-14",
        "2016-10-26",
        "2016-04-11",
    ]);
});

test("performRPC: read_group, group by m2o", async () => {
    Partner._fields.sequence = fields.Integer();
    Partner._records[0].sequence = 1;
    Partner._records[1].sequence = 0;

    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["partner_id"],
                domain: [],
                groupby: ["partner_id"],
            },
        })
    ).resolves.toEqual([
        {
            partner_id: [2, "Raoul"],
            __domain: [["partner_id", "=", 2]],
            partner_id_count: 1,
        },
        {
            partner_id: [1, "Jean-Michel"],
            __domain: [["partner_id", "=", 1]],
            partner_id_count: 2,
        },
        {
            partner_id: false,
            __domain: [["partner_id", "=", false]],
            partner_id_count: 3,
        },
    ]);
});

test("performRPC: read_group, group by integer", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["foo"],
                domain: [],
                groupby: ["foo"],
            },
        })
    ).resolves.toEqual([
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

test("performRPC: read_group, group by selection", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["select"],
                domain: [],
                groupby: ["select"],
            },
        })
    ).resolves.toEqual([
        { select: "new", __domain: [["select", "=", "new"]], select_count: 3 },
        { select: "dev", __domain: [["select", "=", "dev"]], select_count: 1 },
        { select: "done", __domain: [["select", "=", "done"]], select_count: 2 },
    ]);
});

test("performRPC: read_group, group by two levels", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["bool", "partner_ids"],
                domain: [],
                groupby: ["bool", "partner_ids"],
                lazy: false,
            },
        })
    ).resolves.toEqual([
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
                ["bool", "=", false],
            ],
            __count: 1,
            bool: false,
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
        {
            __domain: [
                ["partner_ids", "=", false],
                ["bool", "=", true],
            ],
            __count: 2,
            bool: true,
            partner_ids: false,
        },
    ]);
});

test("performRPC: read_group with special measure specifications", async () => {
    Bar._fields.float = fields.Float();
    Bar._records[0].float = 2;

    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["float:sum", "foo_sum:sum(foo)"],
                domain: [],
                groupby: ["bool"],
                lazy: false,
            },
        })
    ).resolves.toEqual([
        {
            __count: 2,
            __domain: [["bool", "=", false]],
            bool: false,
            float: 0,
            foo_sum: 17,
        },
        {
            __count: 4,
            __domain: [["bool", "=", true]],
            bool: true,
            float: 2,
            foo_sum: 57,
        },
    ]);
});

test("performRPC: read_group with array_agg", async () => {
    await makeMockServer();

    const aggregateValue = [null, 2, null, 1, null, 1];

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["aggregateLabel:array_agg(partner_id)"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            aggregateLabel: aggregateValue,
        },
    ]);
    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["partner_id:array_agg"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            partner_id: aggregateValue,
        },
    ]);
});

test("performRPC: read_group with array_agg on id", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["aggregateLabel:array_agg(id)"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            aggregateLabel: [1, 2, 3, 4, 5, 6],
        },
    ]);
    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["id:array_agg"],
                domain: [["id", "in", [2, 3, 5]]],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 3,
            __domain: [["id", "in", [2, 3, 5]]],
            id: [2, 3, 5],
        },
    ]);
});

test("performRPC: read_group with array_agg on an integer field", async () => {
    await makeMockServer();

    const aggregateValue = [12, 1, 17, 2, 0, 42];

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["aggregateLabel:array_agg(foo)"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            aggregateLabel: aggregateValue,
        },
    ]);
    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["foo:array_agg"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            foo: aggregateValue,
        },
    ]);
});

test("performRPC: read_group with count_distinct", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["aggregateLabel:count_distinct(partner_id)"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            aggregateLabel: 2,
        },
    ]);
    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["partner_id:count_distinct"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            partner_id: 2,
        },
    ]);
    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["partner_id:count_distinct"],
                domain: [[0, "=", 1]],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 0,
            __domain: [[0, "=", 1]],
            partner_id: 0,
        },
    ]);
    await expect(
        ormRequest({
            model: "bar",
            method: "read_group",
            kwargs: {
                fields: ["partner_ref:count_distinct"],
                domain: [],
                groupby: [],
            },
        })
    ).resolves.toEqual([
        {
            __count: 6,
            __domain: [],
            partner_ref: 2,
        },
    ]);
});

test("performRPC: read_progress_bar grouped by boolean", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_progress_bar",
            kwargs: {
                domain: [],
                group_by: "bool",
                progress_bar: {
                    colors: { new: "success", dev: "warning", done: "danger" },
                    field: "select",
                },
            },
        })
    ).resolves.toEqual({
        False: { new: 0, dev: 0, done: 2 },
        True: { new: 3, dev: 1, done: 0 },
    });
});

test("performRPC: read_progress_bar grouped by datetime", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_progress_bar",
            kwargs: {
                domain: [],
                group_by: "datetime:week",
                progress_bar: {
                    colors: { new: "aaa", dev: "bbb", done: "ccc" },
                    field: "select",
                },
            },
        })
    ).resolves.toEqual({
        "W01 2020": { dev: 0, done: 0, new: 1 },
        "W15 2016": { dev: 0, done: 0, new: 1 },
        "W43 2016": { dev: 0, done: 0, new: 1 },
        "W50 2016": { dev: 1, done: 2, new: 0 },
    });
});

test("performRPC: read_progress_bar grouped by many2one", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "read_progress_bar",
            kwargs: {
                domain: [],
                group_by: "partner_id",
                progress_bar: {
                    colors: { new: "aaa", dev: "bbb", done: "ccc" },
                    field: "select",
                },
            },
        })
    ).resolves.toEqual({
        1: { dev: 0, done: 0, new: 2 },
        2: { dev: 0, done: 0, new: 1 },
        False: { dev: 1, done: 2, new: 0 },
    });
});

test("many2one_ref should auto fill inverse field", async () => {
    Bar._records = [{ id: 1 }];
    Foo._records = [{ id: 2, many2one_reference: 1, res_model: "bar" }];

    const { env } = await makeMockServer();
    expect(env["bar"][0].one2many_field).toEqual([2]);

    env["foo"].unlink(2);

    expect(env["bar"][0].one2many_field).toEqual([]);
});

test("many2one should auto fill inverse field", async () => {
    Bar._records = [{ id: 1 }];
    Foo._records = [{ id: 2, many2one_field: 1 }];

    const { env } = await makeMockServer();
    expect(env["bar"][0].one2many_field).toEqual([2]);

    env["foo"].unlink(2);

    expect(env["bar"][0].one2many_field).toEqual([]);
});

test("one2many should auto fill inverse field", async () => {
    Bar._records = [{ id: 1 }, { id: 2 }];
    Foo._records = [{ id: 3, one2many_field: [1, 2] }];

    const { env } = await makeMockServer();
    expect(env["bar"][0].many2one_field).toBe(3);
    expect(env["bar"][1].many2one_field).toBe(3);

    env["foo"].unlink(3);

    expect(env["bar"][0].many2one_field).toBe(false);
    expect(env["bar"][1].many2one_field).toBe(false);
});

test("many2many should auto fill inverse field", async () => {
    Bar._records = [{ id: 1 }];
    Foo._records = [{ id: 2, many2many_field: [1] }];

    const { env } = await makeMockServer();
    expect(env["bar"][0].many2many_field).toEqual([2]);

    env["foo"].unlink(2);

    expect(env["bar"][0].many2many_field).toEqual([]);
});

test("one2many update should update inverse field", async () => {
    Bar._records = [{ id: 1 }, { id: 2 }];
    Foo._records = [{ id: 3, one2many_field: [1, 2] }];

    const { env } = await makeMockServer();

    env["foo"].write(3, { one2many_field: [1] });

    expect(env["bar"][0].many2one_field).toBe(3);
    expect(env["bar"][1].many2one_field).toBe(false);
});

test("many2many update should update inverse field", async () => {
    Bar._records = [{ id: 1 }];
    Foo._records = [{ id: 2, many2many_field: [1] }];

    const { env } = await makeMockServer();

    env["foo"].write(2, { one2many_field: [] });

    expect(env["bar"][0].many2many_field).toEqual([2]);
});

test.todo("many2one update should update inverse field", async () => {
    Bar._records = [{ id: 1 }];
    Foo._records = [{ id: 2, many2one_field: 1 }];

    const { env } = await makeMockServer();

    env["foo"].write(2, { many2one_field: false });

    expect(env["bar"][0].one2many_field).toEqual([]);
});

test("many2one_ref update should update inverse field", async () => {
    Bar._records = [{ id: 1 }];
    Foo._records = [{ id: 2, res_model: "bar", many2one_reference: 1 }];

    const { env } = await makeMockServer();

    env["foo"].write(2, { many2one_reference: false });

    expect(env["bar"][0].one2many_field).toEqual([]);
});

test("webRead sub-fields of a many2one field", async () => {
    Partner._fields.test_name = fields.Char();
    Partner._fields.test_number = fields.Integer();

    Partner._records = [{ id: 1, test_name: "Jean-Michel", test_number: 5 }];
    Bar._records = [{ id: 1, partner_id: 1 }];

    await makeMockServer();

    await expect(
        ormRequest({
            method: "web_read",
            model: "bar",
            args: [[1]],
            kwargs: {
                specification: {
                    partner_id: {
                        fields: {
                            test_name: {},
                            test_number: {},
                        },
                    },
                },
            },
        })
    ).resolves.toEqual([
        {
            id: 1,
            partner_id: {
                id: 1,
                test_name: "Jean-Michel",
                test_number: 5,
            },
        },
    ]);
});

test("List View: invisible on processed Arch", async () => {
    Bar._views[["list", 10001]] = /* xml */ `
        <list>
            <field name="bool" column_invisible="1"/>
            <field name="foo"/>
        </list>
    `;
    Bar._views[["search", 10001]] = /* xml */ `
        <search></search>
    `;

    await makeMockServer();

    const expectedList = /* xml */ `
        <list>
            <field name="bool" column_invisible="True"/>
            <field name="foo"/>
        </list>
    `;

    const { views } = await ormRequest({
        method: "get_views",
        model: "bar",
        kwargs: {
            views: [[10001, "list"]],
            options: {},
        },
    });
    expect(views.list.arch).toMatch(expectedList.trim());
});

test("performRPC: create one record (old API)", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "create",
            args: [{ name: "A" }],
        })
    ).resolves.toBe(7);
});

test("performRPC: create one record (new API)", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "create",
            args: [[{ name: "A" }]],
        })
    ).resolves.toEqual([7]);
});

test("performRPC: create several records (new API)", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "create",
            args: [[{ name: "A" }, { name: "B" }]],
        })
    ).resolves.toEqual([7, 8]);
});

test("performRPC: trigger onchange for new record", async () => {
    await makeMockServer();

    await expect(
        ormRequest({
            model: "bar",
            method: "onchange",
            args: [[], {}, [], { foo: {} }],
        })
    ).resolves.toEqual({ value: { foo: 0 } });
});

test("access rights attributes are present on an editable many2one field", async () => {
    Bar._views[["form", 10001]] = /* xml */ `
        <form>
            <field name="partner_id" />
        </form>
    `;
    Bar._views[["search", 10001]] = /* xml */ `
        <search></search>
    `;

    await makeMockServer();

    const expectedForm = /* xml */ `
        <form>
            <field name="partner_id" can_create="true" can_write="true"/>
        </form>
    `;

    const { views } = await ormRequest({
        method: "get_views",
        model: "bar",
        kwargs: {
            views: [[10001, "form"]],
            options: {},
        },
    });
    expect(views.form.arch).toMatch(expectedForm.trim());
});

test("access rights attributes are missing on an editable many2one field", async () => {
    // The access rights attributes should be present,
    // but are actually missing when a field definition is readonly and readonly=0 is on the view.
    // @see the commit description for more details.

    Bar._fields.partner_id = fields.Many2one({
        string: "Main buddy",
        relation: "res.partner",
        readonly: true,
    });
    Bar._views[["form", 10001]] = /* xml */ `
        <form>
            <field name="partner_id" readonly="0" />
        </form>
    `;
    Bar._views[["search", 10001]] = /* xml */ `
        <search></search>
    `;

    await makeMockServer();

    const expectedForm = /* xml */ `
        <form>
            <field name="partner_id" readonly="0"/>
        </form>
    `;

    const { views } = await ormRequest({
        method: "get_views",
        model: "bar",
        kwargs: {
            views: [[10001, "form"]],
            options: {},
        },
    });
    expect(views.form.arch).toMatch(expectedForm.trim());
});
