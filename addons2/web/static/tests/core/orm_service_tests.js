/** @odoo-module **/

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture, mount } from "../helpers/utils";

import { Component, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");

QUnit.module("ORM Service", {
    async beforeEach() {
        serviceRegistry.add("orm", ormService);
    },
});

function makeFakeRPC() {
    const query = { route: null, params: null };
    const rpc = {
        start() {
            return async (route, params) => {
                query.route = route;
                query.params = params;
            };
        },
    };
    return [query, rpc];
}

QUnit.test("add user context to a simple read request", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.read("my.model", [3], ["id", "descr"]);
    assert.strictEqual(query.route, "/web/dataset/call_kw/my.model/read");
    assert.deepEqual(query.params, {
        args: [[3], ["id", "descr"]],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "read",
        model: "my.model",
    });
});

QUnit.test("context is combined with user context in read request", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    const context = { earth: "isfucked" };
    await env.services.orm.read("my.model", [3], ["id", "descr"], { context });
    assert.strictEqual(query.route, "/web/dataset/call_kw/my.model/read");
    assert.deepEqual(query.params, {
        args: [[3], ["id", "descr"]],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                earth: "isfucked",
            },
        },
        method: "read",
        model: "my.model",
    });
});

QUnit.test("basic method call of model", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.call("partner", "test", [], { context: { a: 1 } });
    assert.strictEqual(query.route, "/web/dataset/call_kw/partner/test");
    assert.deepEqual(query.params, {
        args: [],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
                a: 1,
            },
        },
        method: "test",
        model: "partner",
    });
});

QUnit.test("create method: one record", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.create("partner", [{ color: "red" }]);
    assert.strictEqual(query.route, "/web/dataset/call_kw/partner/create");
    assert.deepEqual(query.params, {
        args: [
            [
                {
                    color: "red",
                },
            ],
        ],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "create",
        model: "partner",
    });
});

QUnit.test("create method: several records", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.create("partner", [{ color: "red" }, { color: "green" }]);
    assert.strictEqual(query.route, "/web/dataset/call_kw/partner/create");
    assert.deepEqual(query.params, {
        args: [
            [
                {
                    color: "red",
                },
                {
                    color: "green",
                },
            ],
        ],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "create",
        model: "partner",
    });
});

QUnit.test("read method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    const context = { abc: 3 };
    await env.services.orm.read("sale.order", [2, 5], ["name", "amount"], {
        load: "none",
        context,
    });
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/read");
    assert.deepEqual(query.params, {
        args: [
            [2, 5],
            ["name", "amount"],
        ],
        kwargs: {
            load: "none",
            context: {
                abc: 3,
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "read",
        model: "sale.order",
    });
});

QUnit.test("unlink method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.unlink("partner", [43]);
    assert.strictEqual(query.route, "/web/dataset/call_kw/partner/unlink");
    assert.deepEqual(query.params, {
        args: [[43]],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "unlink",
        model: "partner",
    });
});

QUnit.test("write method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.write("partner", [43, 14], { active: false });
    assert.strictEqual(query.route, "/web/dataset/call_kw/partner/write");
    assert.deepEqual(query.params, {
        args: [[43, 14], { active: false }],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "write",
        model: "partner",
    });
});

QUnit.test("webReadGroup method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.webReadGroup(
        "sale.order",
        [["user_id", "=", 2]],
        ["amount_total:sum"],
        ["date_order"],
        { offset: 1 }
    );
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/web_read_group");
    assert.deepEqual(query.params, {
        args: [],
        kwargs: {
            domain: [["user_id", "=", 2]],
            fields: ["amount_total:sum"],
            groupby: ["date_order"],
            context: {
                lang: "en",
                uid: 7,
                tz: "taht",
            },
            offset: 1,
        },
        method: "web_read_group",
        model: "sale.order",
    });
});

QUnit.test("readGroup method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.readGroup(
        "sale.order",
        [["user_id", "=", 2]],
        ["amount_total:sum"],
        ["date_order"],
        { offset: 1 }
    );
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/read_group");
    assert.deepEqual(query.params, {
        args: [],
        kwargs: {
            domain: [["user_id", "=", 2]],
            fields: ["amount_total:sum"],
            groupby: ["date_order"],
            context: {
                lang: "en",
                uid: 7,
                tz: "taht",
            },
            offset: 1,
        },
        method: "read_group",
        model: "sale.order",
    });
});

QUnit.test("test readGroup method removes duplicate values from groupby", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.readGroup(
        "sale.order",
        [["user_id", "=", 2]],
        ["amount_total:sum"],
        ["date_order:month", "date_order:month"],
        { offset: 1 }
    );
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/read_group");
    assert.deepEqual(
        query.params.kwargs.groupby,
        ["date_order:month"],
        "Duplicate values should be removed from groupby"
    );
});

QUnit.test("searchRead method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.searchRead("sale.order", [["user_id", "=", 2]], ["amount_total"]);
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/search_read");
    assert.deepEqual(query.params, {
        args: [],
        kwargs: {
            context: {
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
});

QUnit.test("searchCount method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    await env.services.orm.searchCount("sale.order", [["user_id", "=", 2]]);
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/search_count");
    assert.deepEqual(query.params, {
        args: [[["user_id", "=", 2]]],
        kwargs: {
            context: {
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "search_count",
        model: "sale.order",
    });
});

QUnit.test("webRead method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    const context = { abc: 3 };
    await env.services.orm.webRead("sale.order", [2, 5], {
        specification: { name: {}, amount: {} },
        context,
    });
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/web_read");
    assert.deepEqual(query.params, {
        args: [[2, 5]],
        kwargs: {
            specification: { name: {}, amount: {} },
            context: {
                abc: 3,
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        },
        method: "web_read",
        model: "sale.order",
    });
});

QUnit.test("webSearchRead method", async (assert) => {
    const [query, rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    const specification = { amount_total: {} };
    await env.services.orm.webSearchRead("sale.order", [["user_id", "=", 2]], { specification });
    assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/web_search_read");
    assert.deepEqual(query.params, {
        args: [],
        kwargs: {
            context: {
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
});

QUnit.test("orm is specialized for component", async (assert) => {
    const [, /* query */ rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();

    class MyComponent extends Component {
        setup() {
            this.rpc = useService("rpc");
            this.orm = useService("orm");
        }
    }
    MyComponent.template = xml`<div/>`;

    const target = getFixture();
    const component = await mount(MyComponent, target, { env });
    assert.notStrictEqual(component.orm, env.services.orm);
});

QUnit.test("silent mode", async (assert) => {
    serviceRegistry.add("rpc", {
        start() {
            return async (route, params, settings) => {
                assert.step(`${route}${settings.silent ? " (silent)" : ""}`);
            };
        },
    });
    const env = await makeTestEnv();
    const orm = env.services.orm;

    orm.call("my_model", "my_method");
    orm.silent.call("my_model", "my_method");
    orm.call("my_model", "my_method");
    orm.read("my_model", [1], []);
    orm.silent.read("my_model", [1], []);
    orm.read("my_model", [1], []);

    assert.verifySteps([
        "/web/dataset/call_kw/my_model/my_method",
        "/web/dataset/call_kw/my_model/my_method (silent)",
        "/web/dataset/call_kw/my_model/my_method",
        "/web/dataset/call_kw/my_model/read",
        "/web/dataset/call_kw/my_model/read (silent)",
        "/web/dataset/call_kw/my_model/read",
    ]);
});

QUnit.test("validate some obviously wrong calls", async (assert) => {
    assert.expect(2);
    const [, /* query*/ rpc] = makeFakeRPC();
    serviceRegistry.add("rpc", rpc);
    const env = await makeTestEnv();
    try {
        await env.services.orm.read(false, [3], ["id", "descr"]);
    } catch (error) {
        assert.strictEqual(error.message, "Invalid model name: false");
    }
    try {
        await env.services.orm.read("res.partner", false, ["id", "descr"]);
    } catch (error) {
        assert.strictEqual(error.message, "Invalid ids list: false");
    }
});

QUnit.test("optimize read and unlink if no ids", async (assert) => {
    serviceRegistry.add("rpc", {
        start() {
            return async (route) => {
                assert.step(route);
            };
        },
    });
    const env = await makeTestEnv();
    const orm = env.services.orm;

    await orm.read("my_model", [1], []);
    assert.verifySteps(["/web/dataset/call_kw/my_model/read"]);

    await orm.read("my_model", [], []);
    assert.verifySteps([]);

    await orm.unlink("my_model", [1], {});
    assert.verifySteps(["/web/dataset/call_kw/my_model/unlink"]);

    await orm.unlink("my_model", [], {});
    assert.verifySteps([]);
});
