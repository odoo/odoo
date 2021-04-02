/** @odoo-module **/

import { browser } from "../../src/core/browser";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { uiService } from "../../src/services/ui_service";
import { patch, unpatch } from "../../src/utils/patch";
import { UserMenu } from "../../src/webclient/user_menu/user_menu";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeUserService } from "../helpers/mock_services";
import { click, getFixture } from "../helpers/utils";
import { Registry } from "./../../src/core/registry";

const { mount } = owl;

let target;
let env;
let serviceRegistry;
let userMenu;
let baseConfig;

QUnit.module("UserMenu", {
  async beforeEach() {
    serviceRegistry = new Registry();
    serviceRegistry.add("user", makeFakeUserService({ name: "Sauron" }));
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("ui", uiService);
    target = getFixture();
    patch(browser, "usermenutest", {
      location: {
        origin: "http://lordofthering",
      },
    });
    baseConfig = { serviceRegistry };
  },
  afterEach() {
    userMenu.unmount();
    unpatch(browser, "usermenutest");
  },
});

QUnit.test("can be rendered", async (assert) => {
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
  assert.strictEqual(userMenuEl.querySelector(".o_user_name").textContent, "Sauron");
  assert.containsNone(userMenuEl, "ul.o_dropdown_menu li.o_dropdown_item");
  await click(userMenu.el.querySelector("button.o_dropdown_toggler"));
  userMenuEl = userMenu.el;
  assert.containsN(userMenuEl, "ul.o_dropdown_menu li.o_dropdown_item", 3);
  assert.containsOnce(userMenuEl, "div.dropdown-divider");
  const children = [...(userMenuEl.querySelector("ul.o_dropdown_menu").children || [])];
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
  env = await makeTestEnv(Object.assign(baseConfig, { debug: "1" }));
  userMenu = await mount(UserMenu, { env, target });
  let userMenuEl = userMenu.el;
  assert.containsOnce(userMenuEl, "img.o_user_avatar");
  assert.containsOnce(userMenuEl, "span.o_user_name");
  assert.strictEqual(userMenuEl.querySelector(".o_user_name").textContent, "Sauron (test)");
});
