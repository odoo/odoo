/** @odoo-module **/

import { Registry } from "../../src/core/registry";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { SwitchCompanyMenu } from "../../src/webclient/switch_company_menu/switch_company_menu";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeUIService, makeFakeUserService } from "../helpers/mock_services";
import { click, getFixture } from "../helpers/utils";

const { mount } = owl;

QUnit.module("SwitchCompanyMenu", (hooks) => {
  let testConfig;

  hooks.beforeEach(() => {
    const serviceRegistry = new Registry();

    const session_info = {
      user_companies: {
        allowed_companies: {
          1: { id: 1, name: "Hermit" },
          2: { id: 2, name: "Herman's" },
          3: { id: 3, name: "Heroes TM" },
        },
        current_company: 1,
      },
    };
    serviceRegistry.add("ui", makeFakeUIService());
    serviceRegistry.add("user", makeFakeUserService({ session_info }));
    serviceRegistry.add("hotkey", hotkeyService);
    testConfig = { serviceRegistry };
  });

  QUnit.test("basic rendering", async (assert) => {
    assert.expect(10);

    const env = await makeTestEnv(testConfig);
    const target = getFixture();
    const scMenu = await mount(SwitchCompanyMenu, { env, target });
    registerCleanup(() => scMenu.destroy());

    assert.strictEqual(scMenu.el.tagName.toUpperCase(), "LI");
    assert.hasClass(scMenu.el, "o_switch_company_menu");
    assert.strictEqual(scMenu.el.textContent, "Hermit");

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    assert.containsN(scMenu, ".toggle_company", 3);
    assert.containsN(scMenu, ".log_into", 3);
    assert.containsOnce(scMenu.el, ".fa-check-square");
    assert.containsN(scMenu.el, ".fa-square-o", 2);
    assert.strictEqual(
      scMenu.el.querySelector(".fa-check-square").closest(".o_dropdown_item").textContent,
      "Hermit"
    );
    assert.strictEqual(
      scMenu.el.querySelector(".fa-square-o").closest(".o_dropdown_item").textContent,
      "Herman's"
    );
    assert.strictEqual(
      scMenu.el.querySelector(".o_dropdown_menu").textContent,
      "HermitHerman'sHeroes TM"
    );
  });

  QUnit.test("companies can be toggled and logged in", async (assert) => {
    assert.expect(20);

    const env = await makeTestEnv(testConfig);
    const target = getFixture();
    const scMenu = await mount(SwitchCompanyMenu, { env, target });
    registerCleanup(() => scMenu.destroy());

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [1]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 1);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".toggle_company")[1]);
    /**
     *   [x] **Company 1**
     *   [x] Company 2      -> toggle
     *   [ ] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [1, 2]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 1);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".toggle_company")[0]);
    /**
     *   [ ] Company 1       -> toggle
     *   [x] **Company 2**
     *   [ ] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [2]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 2);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".toggle_company")[1]);
    /**
     *   [ ] Company 1
     *   [x] **Company 2**  -> tried to toggle
     *   [ ] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [2]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 2);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".toggle_company")[2]);
    /**
     *   [ ] Company 1
     *   [x] **Company 2**
     *   [x] Company 3      -> toggle
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [2, 3]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 2);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".toggle_company")[0]);
    /**
     *   [x] Company 1      -> toggle
     *   [x] **Company 2**
     *   [x] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [2, 3, 1]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 2);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".log_into")[0]);
    /**
     *   [x] **Company 1**      -> click label
     *   [x] Company 2
     *   [x] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [1, 2, 3]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 1);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".log_into")[0]);
    /**
     *   [x] **Company 1**      -> tried to click label
     *   [x] Company 2
     *   [x] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [1, 2, 3]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 1);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".toggle_company")[0]);
    /**
     *   [ ] Company 1      -> toggle
     *   [x] **Company 2**
     *   [x] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [2, 3]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 2);

    await click(scMenu.el.querySelector(".o_dropdown_toggler"));
    await click(scMenu.el.querySelectorAll(".log_into")[0]);
    /**
     *   [x] **Company 1**      -> click label
     *   [x] Company 2
     *   [x] Company 3
     */
    assert.deepEqual(scMenu.env.services.user.context.allowed_company_ids, [1, 2, 3]);
    assert.strictEqual(scMenu.env.services.user.current_company.id, 1);
  });
});
