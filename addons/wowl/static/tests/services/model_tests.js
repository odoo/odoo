/** @odoo-module **/
const { Component, tags } = owl;
import { Registry } from "../../src/core/registry";
import { useService } from "../../src/core/hooks";
import { modelService } from "../../src/services/model_service";
import { getFixture, makeFakeUserService, makeTestEnv, mount } from "../helpers/index";
const { xml } = tags;
let serviceRegistry;
QUnit.module("Model Service", {
  async beforeEach() {
    serviceRegistry = new Registry();
    serviceRegistry.add("user", makeFakeUserService());
    serviceRegistry.add(modelService.name, modelService);
  },
});
function makeFakeRPC() {
  const query = { route: null, params: null };
  const rpc = {
    name: "rpc",
    deploy() {
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
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("my.model").read([3], ["id", "descr"]);
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
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("my.model").read([3], ["id", "descr"], { earth: "isfucked" });
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
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("partner").call("test", [], { context: { a: 1 } });
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
QUnit.test("create method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("partner").create({ color: "red" });
  assert.strictEqual(query.route, "/web/dataset/call_kw/partner/create");
  assert.deepEqual(query.params, {
    args: [
      {
        color: "red",
      },
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
QUnit.test("unlink method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("partner").unlink([43]);
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
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("partner").write([43, 14], { active: false });
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
QUnit.test("readGroup method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services
    .model("sale.order")
    .readGroup([["user_id", "=", 2]], ["amount_total:sum"], ["date_order"], { offset: 1 });
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
QUnit.test("searchRead method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("sale.order").searchRead([["user_id", "=", 2]], ["amount_total"]);
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
QUnit.test("webSearchRead method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.model("sale.order").webSearchRead([["user_id", "=", 2]], ["amount_total"]);
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
      fields: ["amount_total"],
    },
    method: "web_search_read",
    model: "sale.order",
  });
});
QUnit.test("useModel take proper reference to rpc service", async (assert) => {
  class MyComponent extends Component {
    constructor() {
      super(...arguments);
      this.model = useService("model");
    }
  }
  MyComponent.template = xml`<div/>`;
  let component;
  serviceRegistry.add("rpc", {
    name: "rpc",
    deploy() {
      return async function () {
        assert.strictEqual(this, component);
      };
    },
  });
  const env = await makeTestEnv({ serviceRegistry });
  component = await mount(MyComponent, { env, target: getFixture() });
  await component.model("test").read([1], ["asfd"]);
});
