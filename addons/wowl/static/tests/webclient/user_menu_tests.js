/** @odoo-module **/
import { UserMenu } from "../../src/webclient/user_menu/user_menu";
import { click, getFixture, makeFakeUserService, makeTestEnv, mount } from "../helpers/index";
import { Registry } from "./../../src/core/registry";
let target;
let env;
let serviceRegistry;
let userMenu;
let baseConfig;
QUnit.module("UserMenu", {
  async beforeEach() {
    serviceRegistry = new Registry();
    serviceRegistry.add("user", makeFakeUserService({ name: "Sauron" }));
    target = getFixture();
    const browser = {
      location: {
        origin: "http://lordofthering",
      },
    };
    baseConfig = { browser, serviceRegistry };
  },
  afterEach() {
    userMenu.unmount();
  },
});
QUnit.test("can be rendered", async (assert) => {
  var _a, _b, _c;
  env = await makeTestEnv(baseConfig);
  odoo.userMenuRegistry.add("bad_item", function () {
    return {
      type: "item",
      description: "Bad",
      callback: () => {
        assert.step("callback bad_item");
      },
      sequence: 10,
    };
  });
  odoo.userMenuRegistry.add("ring_item", function () {
    return {
      type: "item",
      description: "Ring",
      callback: () => {
        assert.step("callback ring_item");
      },
      sequence: 5,
    };
  });
  odoo.userMenuRegistry.add("separator", function () {
    return {
      type: "separator",
      sequence: 15,
    };
  });
  odoo.userMenuRegistry.add("invisible_item", function () {
    return {
      type: "item",
      description: "Hidden Power",
      callback: () => {},
      sequence: 5,
      hide: true,
    };
  });
  odoo.userMenuRegistry.add("eye_item", function () {
    return {
      type: "item",
      description: "Eye",
      callback: () => {
        assert.step("callback eye_item");
      },
    };
  });
  userMenu = await mount(UserMenu, { env, target });
  let userMenuEl = userMenu.el;
  assert.containsOnce(userMenuEl, "img.o_user_avatar");
  assert.strictEqual(
    userMenuEl.querySelector("img.o_user_avatar").src,
    "http://lordofthering/web/image?model=res.users&field=image_128&id=7"
  );
  assert.containsOnce(userMenuEl, "span.o_user_name");
  assert.strictEqual(
    (_a = userMenuEl.querySelector(".o_user_name")) === null || _a === void 0
      ? void 0
      : _a.textContent,
    "Sauron"
  );
  assert.containsNone(userMenuEl, "ul.o_dropdown_menu li.o_dropdown_item");
  await click(
    (_b = userMenu.el) === null || _b === void 0
      ? void 0
      : _b.querySelector("button.o_dropdown_toggler")
  );
  userMenuEl = userMenu.el;
  assert.containsN(userMenuEl, "ul.o_dropdown_menu li.o_dropdown_item", 3);
  assert.containsOnce(userMenuEl, "div.dropdown-divider");
  const children = [
    ...(((_c = userMenuEl.querySelector("ul.o_dropdown_menu")) === null || _c === void 0
      ? void 0
      : _c.children) || []),
  ];
  assert.deepEqual(
    children.map((el) => el.tagName),
    ["LI", "LI", "DIV", "LI"]
  );
  const items =
    [...userMenuEl.querySelectorAll("ul.o_dropdown_menu li.o_dropdown_item span")] || [];
  assert.deepEqual(
    items.map((el) => el.textContent),
    ["Ring", "Bad", "Eye"]
  );
  for (const item of items) {
    click(item);
  }
  assert.verifySteps(["callback ring_item", "callback bad_item", "callback eye_item"]);
});
QUnit.test("display the correct name in debug mode", async (assert) => {
  var _a;
  env = await makeTestEnv(Object.assign(baseConfig, { debug: "1" }));
  userMenu = await mount(UserMenu, { env, target });
  let userMenuEl = userMenu.el;
  assert.containsOnce(userMenuEl, "img.o_user_avatar");
  assert.containsOnce(userMenuEl, "span.o_user_name");
  assert.strictEqual(
    (_a = userMenuEl.querySelector(".o_user_name")) === null || _a === void 0
      ? void 0
      : _a.textContent,
    "Sauron (test)"
  );
});
