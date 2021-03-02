/** @odoo-module **/
import { ActionDialog } from "../../src/actions/action_dialog";
import { Registry } from "../../src/core/registry";
import { DebugManager } from "../../src/debug/debug_manager";
import { debugManagerService } from "../../src/debug/debug_manager_service";
import { modelService } from "../../src/services/model";
import { useDebugManager } from "../../src/debug/debug_manager";
import { click, getFixture, makeTestEnv, mount } from "../helpers/index";

const { Component, hooks, tags } = owl;
const { useSubEnv } = hooks;

let target;
let testConfig;
QUnit.module("DebugManager", (hooks) => {
  hooks.beforeEach(async () => {
    target = getFixture();
    const serviceRegistry = new Registry();
    serviceRegistry.add(modelService.name, modelService);
    serviceRegistry.add(debugManagerService.name, debugManagerService);
    const mockRPC = async (route, args) => {
      if (args.method === "check_access_rights") {
        return Promise.resolve(true);
      }
    };
    testConfig = { serviceRegistry, mockRPC };
  });
  QUnit.test("can be rendered", async (assert) => {
    var _a, _b;
    testConfig.debugManagerRegistry = new Registry();
    testConfig.debugManagerRegistry.add("item_1", () => {
      return {
        type: "item",
        description: "Item 1",
        callback: () => {
          assert.step("callback item_1");
        },
        sequence: 10,
      };
    });
    testConfig.debugManagerRegistry.add("item_2", () => {
      return {
        type: "item",
        description: "Item 2",
        callback: () => {
          assert.step("callback item_2");
        },
        sequence: 5,
      };
    });
    testConfig.debugManagerRegistry.add("item_3", () => {
      return {
        type: "item",
        description: "Item 3",
        callback: () => {
          assert.step("callback item_3");
        },
      };
    });
    testConfig.debugManagerRegistry.add("separator", () => {
      return {
        type: "separator",
        sequence: 20,
      };
    });
    testConfig.debugManagerRegistry.add("separator_2", () => {
      return {
        type: "separator",
        sequence: 7,
        hide: true,
      };
    });
    testConfig.debugManagerRegistry.add("item_4", () => {
      return {
        type: "item",
        description: "Item 4",
        callback: () => {
          assert.step("callback item_4");
        },
        hide: true,
        sequence: 10,
      };
    });
    const env = await makeTestEnv(testConfig);
    const debugManager = await mount(DebugManager, { env, target });
    let debugManagerEl = debugManager.el;
    await click(
      (_a = debugManager.el) === null || _a === void 0
        ? void 0
        : _a.querySelector("button.o_dropdown_toggler")
    );
    debugManagerEl = debugManager.el;
    assert.containsN(debugManagerEl, "ul.o_dropdown_menu li.o_dropdown_item", 3);
    assert.containsOnce(debugManagerEl, "div.dropdown-divider");
    const children = [
      ...(((_b = debugManagerEl.querySelector("ul.o_dropdown_menu")) === null || _b === void 0
        ? void 0
        : _b.children) || []),
    ];
    assert.deepEqual(
      children.map((el) => el.tagName),
      ["LI", "LI", "DIV", "LI"]
    );
    const items =
      [...debugManagerEl.querySelectorAll("ul.o_dropdown_menu li.o_dropdown_item span")] || [];
    assert.deepEqual(
      items.map((el) => el.textContent),
      ["Item 2", "Item 1", "Item 3"]
    );
    for (const item of items) {
      click(item);
    }
    assert.verifySteps(["callback item_2", "callback item_1", "callback item_3"]);
    debugManager.destroy();
  });
  QUnit.test("Don't display the DebugManager if debug mode is disabled", async (assert) => {
    var _a;
    const dialogContainer = document.createElement("div");
    dialogContainer.classList.add("o_dialog_container");
    target.append(dialogContainer);
    const env = await makeTestEnv(testConfig);
    const actionDialog = await mount(ActionDialog, { env, target });
    assert.containsOnce(target, "div.o_dialog_container .o_dialog");
    assert.containsNone(target, ".o_dialog .o_debug_manager .fa-bug");
    actionDialog.destroy();
    (_a = target.querySelector(".o_dialog_container")) === null || _a === void 0
      ? void 0
      : _a.remove();
  });
  QUnit.test(
    "Display the DebugManager correctly in a ActionDialog if debug mode is enabled",
    async (assert) => {
      var _a;
      const dialogContainer = document.createElement("div");
      dialogContainer.classList.add("o_dialog_container");
      target.append(dialogContainer);
      testConfig.debugManagerRegistry = new Registry();
      testConfig.debugManagerRegistry.add("global", () => {
        return {
          type: "item",
          description: "Global 1",
          callback: () => {
            assert.step("callback global_1");
          },
          sequence: 0,
        };
      });
      const item1 = {
        type: "item",
        description: "Item 1",
        callback: () => {
          assert.step("callback item_1");
        },
        sequence: 10,
      };
      const item2 = {
        type: "item",
        description: "Item 2",
        callback: () => {
          assert.step("callback item_2");
        },
        sequence: 20,
      };
      class Parent extends Component {
        constructor(...args) {
          super(...args);
          useSubEnv({ inDialog: true });
          useDebugManager(() => [item1, item2]);
        }
      }
      Parent.components = { ActionDialog };
      Parent.template = tags.xml`<ActionDialog/>`;
      testConfig.debug = "1";
      const env = await makeTestEnv(testConfig);
      const actionDialog = await mount(Parent, { env, target });
      assert.containsOnce(target, "div.o_dialog_container .o_dialog");
      assert.containsOnce(target, ".o_dialog .o_debug_manager .fa-bug");
      await click(target, ".o_dialog .o_debug_manager button");
      const debugManagerEl = target.querySelector(".o_dialog_container .o_debug_manager");
      assert.containsN(debugManagerEl, "ul.o_dropdown_menu li.o_dropdown_item", 2);
      // Check that global debugManager elements are not displayed (global_1)
      const items =
        [...debugManagerEl.querySelectorAll("ul.o_dropdown_menu li.o_dropdown_item span")] || [];
      assert.deepEqual(
        items.map((el) => el.textContent),
        ["Item 1", "Item 2"]
      );
      for (const item of items) {
        click(item);
      }
      assert.verifySteps(["callback item_1", "callback item_2"]);
      actionDialog.destroy();
      (_a = target.querySelector(".o_dialog_container")) === null || _a === void 0
        ? void 0
        : _a.remove();
    }
  );
});
