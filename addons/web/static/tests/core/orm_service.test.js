import { after, describe, expect, test } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { getService, makeMockEnv, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { rpcBus } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

describe.current.tags("headless");

const getRelevantParams = (params) => pick(params, "args", "kwargs", "method", "model");

test("add user context to a simple read request", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[3], ["id", "descr"]],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "read",
            model: "res.partner",
        });
        return false; // Don't want to call the actual read method
    });

    const { services } = await makeMockEnv();
    await services.orm.read("res.partner", [3], ["id", "descr"]);

    expect(["/web/dataset/call_kw/res.partner/read"]).toVerifySteps();
});

test("context is combined with user context in read request", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[3], ["id", "descr"]],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    earth: "isfucked",
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "read",
            model: "res.partner",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.read("res.partner", [3], ["id", "descr"], {
        context: {
            earth: "isfucked",
        },
    });

    expect(["/web/dataset/call_kw/res.partner/read"]).toVerifySteps();
});

test("basic method call of model", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [],
            kwargs: {
                context: {
                    a: 1,
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "test",
            model: "res.partner",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.call("res.partner", "test", [], { context: { a: 1 } });

    expect(["/web/dataset/call_kw/res.partner/test"]).toVerifySteps();
});

test("create method: one record", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[{ color: "red" }]],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "create",
            model: "res.partner",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.create("res.partner", [{ color: "red" }]);

    expect(["/web/dataset/call_kw/res.partner/create"]).toVerifySteps();
});

test("create method: several records", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[{ color: "red" }, { color: "green" }]],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "create",
            model: "res.partner",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.create("res.partner", [{ color: "red" }, { color: "green" }]);

    expect(["/web/dataset/call_kw/res.partner/create"]).toVerifySteps();
});

test("read method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [
                [2, 5],
                ["name", "amount"],
            ],
            kwargs: {
                load: "none",
                context: {
                    abc: 3,
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "read",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.read("sale.order", [2, 5], ["name", "amount"], {
        load: "none",
        context: { abc: 3 },
    });

    expect(["/web/dataset/call_kw/sale.order/read"]).toVerifySteps();
});

test("unlink method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[43]],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "unlink",
            model: "res.partner",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.unlink("res.partner", [43]);

    expect(["/web/dataset/call_kw/res.partner/unlink"]).toVerifySteps();
});

test("write method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[43, 14], { active: false }],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "write",
            model: "res.partner",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.write("res.partner", [43, 14], { active: false });

    expect(["/web/dataset/call_kw/res.partner/write"]).toVerifySteps();
});

test("webReadGroup method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [],
            kwargs: {
                domain: [["user_id", "=", 2]],
                fields: ["amount_total:sum"],
                groupby: ["date_order"],
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    uid: 7,
                    tz: "taht",
                },
                offset: 1,
            },
            method: "web_read_group",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.webReadGroup(
        "sale.order",
        [["user_id", "=", 2]],
        ["amount_total:sum"],
        ["date_order"],
        { offset: 1 }
    );

    expect(["/web/dataset/call_kw/sale.order/web_read_group"]).toVerifySteps();
});

test("readGroup method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [],
            kwargs: {
                domain: [["user_id", "=", 2]],
                fields: ["amount_total:sum"],
                groupby: ["date_order"],
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    uid: 7,
                    tz: "taht",
                },
                offset: 1,
            },
            method: "read_group",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.readGroup(
        "sale.order",
        [["user_id", "=", 2]],
        ["amount_total:sum"],
        ["date_order"],
        { offset: 1 }
    );

    expect(["/web/dataset/call_kw/sale.order/read_group"]).toVerifySteps();
});

test("test readGroup method removes duplicate values from groupby", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params).kwargs.groupby).toEqual(["date_order:month"], {
            message: "Duplicate values should be removed from groupby",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.readGroup(
        "sale.order",
        [["user_id", "=", 2]],
        ["amount_total:sum"],
        ["date_order:month", "date_order:month"],
        { offset: 1 }
    );

    expect(["/web/dataset/call_kw/sale.order/read_group"]).toVerifySteps();
});

test("search_read method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
                domain: [["user_id", "=", 2]],
                fields: ["amount_total"],
            },
            method: "search_read",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.searchRead("sale.order", [["user_id", "=", 2]], ["amount_total"]);

    expect(["/web/dataset/call_kw/sale.order/search_read"]).toVerifySteps();
});

test("search_count method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[["user_id", "=", 2]]],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "search_count",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.searchCount("sale.order", [["user_id", "=", 2]]);

    expect(["/web/dataset/call_kw/sale.order/search_count"]).toVerifySteps();
});

test("webRead method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [[2, 5]],
            kwargs: {
                specification: { name: {}, amount: {} },
                context: {
                    abc: 3,
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
            },
            method: "web_read",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.webRead("sale.order", [2, 5], {
        specification: { name: {}, amount: {} },
        context: { abc: 3 },
    });

    expect(["/web/dataset/call_kw/sale.order/web_read"]).toVerifySteps();
});

test("webSearchRead method", async () => {
    onRpc(async (params) => {
        expect.step(params.route);
        expect(getRelevantParams(params)).toEqual({
            args: [],
            kwargs: {
                context: {
                    allowed_company_ids: [1],
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                },
                domain: [["user_id", "=", 2]],
                specification: { amount_total: {} },
            },
            method: "web_search_read",
            model: "sale.order",
        });
        return false;
    });

    const { services } = await makeMockEnv();
    await services.orm.webSearchRead("sale.order", [["user_id", "=", 2]], {
        specification: { amount_total: {} },
    });

    expect(["/web/dataset/call_kw/sale.order/web_search_read"]).toVerifySteps();
});

test("orm is specialized for component", async () => {
    await makeMockEnv();

    class MyComponent extends Component {
        static props = {};
        static template = xml`<div />`;
        setup() {
            this.orm = useService("orm");
        }
    }

    const component = await mountWithCleanup(MyComponent);

    expect(component.orm).not.toBe(getService("orm"));
});

test("silent mode", async () => {
    onRpc((params) => {
        expect.step(params.route);
        return false;
    });

    const { services } = await makeMockEnv();
    after(
        on(rpcBus, "RPC:RESPONSE", (ev) =>
            expect.step(`response${ev.detail.settings.silent ? " (silent)" : ""}`)
        )
    );

    await services.orm.call("res.partner", "partner_method");
    await services.orm.silent.call("res.partner", "partner_method");
    await services.orm.call("res.partner", "partner_method");
    await services.orm.read("res.partner", [1], []);
    await services.orm.silent.read("res.partner", [1], []);
    await services.orm.read("res.partner", [1], []);

    expect([
        "/web/dataset/call_kw/res.partner/partner_method",
        "response",
        "/web/dataset/call_kw/res.partner/partner_method",
        "response (silent)",
        "/web/dataset/call_kw/res.partner/partner_method",
        "response",
        "/web/dataset/call_kw/res.partner/read",
        "response",
        "/web/dataset/call_kw/res.partner/read",
        "response (silent)",
        "/web/dataset/call_kw/res.partner/read",
        "response",
    ]).toVerifySteps();
});

test("validate some obviously wrong calls", async () => {
    expect.assertions(2);

    const { services } = await makeMockEnv();

    expect(() => services.orm.read(false, [3], ["id", "descr"])).toThrow(
        "Invalid model name: false"
    );
    expect(() => services.orm.read("res.res.partner", false, ["id", "descr"])).toThrow(
        "Invalid ids list: false"
    );
});

test("optimize read and unlink if no ids", async () => {
    onRpc((params) => {
        expect.step(params.route);
        return false;
    });

    const { services } = await makeMockEnv();

    await services.orm.read("res.partner", [1], []);
    expect(["/web/dataset/call_kw/res.partner/read"]).toVerifySteps();

    await services.orm.read("res.partner", [], []);
    expect([]).toVerifySteps();

    await services.orm.unlink("res.partner", [1], {});
    expect(["/web/dataset/call_kw/res.partner/unlink"]).toVerifySteps();

    await services.orm.unlink("res.partner", [], {});
    expect([]).toVerifySteps();
});
