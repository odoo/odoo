/** @odoo-module **/
import { Registry } from "../../src/core/registry";
import { titleService } from "../../src/services/title_service";
import { makeTestEnv } from "../helpers/index";
// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------
let env;
let serviceRegistry;
let title;
QUnit.module("Title", {
  async beforeEach() {
    title = document.title;
    serviceRegistry = new Registry();
    serviceRegistry.add(titleService.name, titleService);
    env = await makeTestEnv({ serviceRegistry });
  },
  afterEach() {
    document.title = title;
  },
});
QUnit.test("simple title", async (assert) => {
  assert.expect(1);
  env.services.title.setParts({ zopenerp: "Odoo" });
  assert.strictEqual(env.services.title.current, "Odoo");
});
QUnit.test("add title part", async (assert) => {
  assert.expect(2);
  env.services.title.setParts({ zopenerp: "Odoo", chat: null });
  assert.strictEqual(env.services.title.current, "Odoo");
  env.services.title.setParts({ action: "Import" });
  assert.strictEqual(env.services.title.current, "Odoo - Import");
});
QUnit.test("modify title part", async (assert) => {
  assert.expect(2);
  env.services.title.setParts({ zopenerp: "Odoo" });
  assert.strictEqual(env.services.title.current, "Odoo");
  env.services.title.setParts({ zopenerp: "Zopenerp" });
  assert.strictEqual(env.services.title.current, "Zopenerp");
});
QUnit.test("delete title part", async (assert) => {
  assert.expect(2);
  env.services.title.setParts({ zopenerp: "Odoo" });
  assert.strictEqual(env.services.title.current, "Odoo");
  env.services.title.setParts({ zopenerp: null });
  assert.strictEqual(env.services.title.current, "");
});
QUnit.test("all at once", async (assert) => {
  assert.expect(2);
  env.services.title.setParts({ zopenerp: "Odoo", action: "Import" });
  assert.strictEqual(env.services.title.current, "Odoo - Import");
  env.services.title.setParts({ action: null, zopenerp: "Zopenerp", chat: "Sauron" });
  assert.strictEqual(env.services.title.current, "Zopenerp - Sauron");
});
QUnit.test("get title parts", async (assert) => {
  assert.expect(3);
  env.services.title.setParts({ zopenerp: "Odoo", action: "Import" });
  assert.strictEqual(env.services.title.current, "Odoo - Import");
  const parts = env.services.title.getParts();
  assert.deepEqual(parts, { zopenerp: "Odoo", action: "Import" });
  parts.action = "Export";
  assert.strictEqual(env.services.title.current, "Odoo - Import"); // parts is a copy!
});
