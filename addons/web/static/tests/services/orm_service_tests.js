/** @odoo-module **/

import { useService } from "../../src/core/hooks";
import { Registry } from "../../src/core/registry";
import { ormService } from "../../src/services/orm_service";
import { getFixture } from "../helpers/utils";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeUserService } from "../helpers/mock_services";

const { Component, mount, tags } = owl;
const { xml } = tags;

let serviceRegistry;

QUnit.module("ORM Service", {
  async beforeEach() {
    serviceRegistry = new Registry();
    serviceRegistry.add("user", makeFakeUserService());
    serviceRegistry.add("orm", ormService);
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
  await env.services.orm.read("my.model", [3], ["id", "descr"]);
  assert.strictEqual(query.route, "/web/dataset/call_kw/my.model/read");
  assert.deepEqual(query.params, {
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
    model: "my.model",
  });
});

QUnit.test("context is combined with user context in read request", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.orm.read("my.model", [3], ["id", "descr"], { earth: "isfucked" });
  assert.strictEqual(query.route, "/web/dataset/call_kw/my.model/read");
  assert.deepEqual(query.params, {
    args: [[3], ["id", "descr"]],
    kwargs: {
      context: {
        allowed_company_ids: [1],
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
  await env.services.orm.call("partner", "test", [], { context: { a: 1 } });
  assert.strictEqual(query.route, "/web/dataset/call_kw/partner/test");
  assert.deepEqual(query.params, {
    args: [],
    kwargs: {
      context: {
        allowed_company_ids: [1],
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
  await env.services.orm.create("partner", { color: "red" });
  assert.strictEqual(query.route, "/web/dataset/call_kw/partner/create");
  assert.deepEqual(query.params, {
    args: [
      {
        color: "red",
      },
    ],
    kwargs: {
      context: {
        allowed_company_ids: [1],
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
  await env.services.orm.unlink("partner", [43]);
  assert.strictEqual(query.route, "/web/dataset/call_kw/partner/unlink");
  assert.deepEqual(query.params, {
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
    model: "partner",
  });
});

QUnit.test("write method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.orm.write("partner", [43, 14], { active: false });
  assert.strictEqual(query.route, "/web/dataset/call_kw/partner/write");
  assert.deepEqual(query.params, {
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
    model: "partner",
  });
});

QUnit.test("readGroup method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.orm.readGroup(
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
});

QUnit.test("searchRead method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.orm.searchRead("sale.order", [["user_id", "=", 2]], ["amount_total"]);
  assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/search_read");
  assert.deepEqual(query.params, {
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
});

QUnit.test("webSearchRead method", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });
  await env.services.orm.webSearchRead("sale.order", [["user_id", "=", 2]], ["amount_total"]);
  assert.strictEqual(query.route, "/web/dataset/call_kw/sale.order/web_search_read");
  assert.deepEqual(query.params, {
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
    method: "web_search_read",
    model: "sale.order",
  });
});

QUnit.test("useModel is specialized for component", async (assert) => {
  const [query, rpc] = makeFakeRPC();
  serviceRegistry.add("rpc", rpc);
  const env = await makeTestEnv({ serviceRegistry });

  class MyComponent extends Component {
    setup() {
      this.rpc = useService("rpc");
      this.orm = useService("orm");
    }
  }
  MyComponent.template = xml`<div/>`;

  const target = getFixture();
  const component = await mount(MyComponent, { env, target });
  assert.strictEqual(component.rpc, component.orm.rpc);
  assert.notStrictEqual(component.orm, env.services.orm);
});
