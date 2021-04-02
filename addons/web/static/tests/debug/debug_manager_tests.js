/** @odoo-module **/

import { ActionDialog } from "../../src/actions/action_dialog";
import { Registry } from "../../src/core/registry";
import { DebugManager } from "../../src/debug/debug_manager";
import { debugService } from "../../src/debug/debug_service";
import { ormService } from "../../src/services/orm_service";
import { useDebugManager } from "../../src/debug/debug_manager";
import { click, getFixture } from "../helpers/utils";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { uiService } from "../../src/services/ui_service";
import { makeTestEnv } from "../helpers/mock_env";

const { Component, hooks, mount, tags } = owl;
const { useSubEnv } = hooks;

let target;
let testConfig;
QUnit.module("DebugManager", (hooks) => {
  hooks.beforeEach(async () => {
    target = getFixture();
    const serviceRegistry = new Registry();
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("ui", uiService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("debug", debugService);
    const mockRPC = async (route, args) => {
      if (args.method === "check_access_rights") {
        return Promise.resolve(true);
      }
    };
    testConfig = { serviceRegistry, mockRPC };
  });
  QUnit.test("can be rendered", async (assert) => {
    testConfig.debugRegistry = new Registry();
    testConfig.debugRegistry.add("item_1", () => {
      return {
        type: "item",
        description: "Item 1",
        callback: () => {
          assert.step("callback item_1");
        },
        sequence: 10,
      };
    });
    testConfig.debugRegistry.add("item_2", () => {
      return {
        type: "item",
        description: "Item 2",
        callback: () => {
          assert.step("callback item_2");
        },
        sequence: 5,
      };
    });
    testConfig.debugRegistry.add("item_3", () => {
      return {
        type: "item",
        description: "Item 3",
        callback: () => {
          assert.step("callback item_3");
        },
      };
    });
    testConfig.debugRegistry.add("separator", () => {
      return {
        type: "separator",
        sequence: 20,
      };
    });
    testConfig.debugRegistry.add("separator_2", () => {
      return {
        type: "separator",
        sequence: 7,
        hide: true,
      };
    });
    testConfig.debugRegistry.add("item_4", () => {
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
    await click(debugManager.el.querySelector("button.o_dropdown_toggler"));
    debugManagerEl = debugManager.el;
    assert.containsN(debugManagerEl, "ul.o_dropdown_menu li.o_dropdown_item", 3);
    assert.containsOnce(debugManagerEl, "div.dropdown-divider");
    const children = [...(debugManagerEl.querySelector("ul.o_dropdown_menu").children || [])];
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
    const dialogContainer = document.createElement("div");
    dialogContainer.classList.add("o_dialog_container");
    target.append(dialogContainer);
    const env = await makeTestEnv(testConfig);
    const actionDialog = await mount(ActionDialog, { env, target });
    assert.containsOnce(target, "div.o_dialog_container .o_dialog");
    assert.containsNone(target, ".o_dialog .o_debug_manager .fa-bug");
    actionDialog.destroy();
    target.querySelector(".o_dialog_container").remove();
  });

  QUnit.test(
    "Display the DebugManager correctly in a ActionDialog if debug mode is enabled",
    async (assert) => {
      const dialogContainer = document.createElement("div");
      dialogContainer.classList.add("o_dialog_container");
      target.append(dialogContainer);
      testConfig.debugRegistry = new Registry();
      testConfig.debugRegistry.add("global", () => {
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
        setup() {
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
      target.querySelector(".o_dialog_container").remove();
    }
  );
});
