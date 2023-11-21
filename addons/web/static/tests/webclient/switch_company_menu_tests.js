/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { companyService } from "@web/webclient/company_service";
import { click, getFixture, makeDeferred, patchWithCleanup } from "../helpers/utils";
import { uiService } from "@web/core/ui/ui_service";
import { session } from "@web/session";

const { mount } = owl;
const serviceRegistry = registry.category("services");

const ORIGINAL_TOGGLE_DELAY = SwitchCompanyMenu.toggleDelay;
async function createSwitchCompanyMenu(routerParams = {}, toggleDelay = 0) {
    patchWithCleanup(SwitchCompanyMenu, { toggleDelay });
    if (routerParams.onPushState) {
        const pushState = browser.history.pushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState(state, title, url) {
                    pushState(...arguments);
                    if (routerParams.onPushState) {
                        routerParams.onPushState(url);
                    }
                },
            }),
        });
    }
    const env = await makeTestEnv();
    const target = getFixture();
    const scMenu = await mount(SwitchCompanyMenu, { env, target });
    registerCleanup(() => scMenu.destroy());
    return scMenu;
}

QUnit.module("SwitchCompanyMenu", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(session.user_companies, {
            allowed_companies: {
                3: { id: 3, name: "Hermit", sequence: 1 },
                2: { id: 2, name: "Herman's", sequence: 2 },
                1: { id: 1, name: "Heroes TM", sequence: 3 },
            },
            current_company: 3,
        });
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("company", companyService);
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.test("basic rendering", async (assert) => {
        assert.expect(10);

        const scMenu = await createSwitchCompanyMenu();

        assert.strictEqual(scMenu.el.tagName.toUpperCase(), "DIV");
        assert.hasClass(scMenu.el, "o_switch_company_menu");
        assert.strictEqual(scMenu.el.textContent, "Hermit");

        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu, ".toggle_company", 3);
        assert.containsN(scMenu, ".log_into", 3);
        assert.containsOnce(scMenu.el, ".fa-check-square");
        assert.containsN(scMenu.el, ".fa-square-o", 2);
        assert.strictEqual(
            scMenu.el.querySelector(".fa-check-square").closest(".dropdown-item").textContent,
            "Hermit"
        );
        assert.strictEqual(
            scMenu.el.querySelector(".fa-square-o").closest(".dropdown-item").textContent,
            "Herman's"
        );
        assert.strictEqual(
            scMenu.el.querySelector(".dropdown-menu").textContent,
            "HermitHerman'sHeroes TM"
        );
    });

    QUnit.test("companies can be toggled: toggle a second company", async (assert) => {
        const prom = makeDeferred();
        function onPushState(url) {
            assert.step(url.split("#")[1]);
            prom.resolve();
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState });

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 2);
        assert.deepEqual(
            [...scMenu.el.querySelectorAll("[data-company-id] .toggle_company")].map(
                (el) => el.ariaChecked
            ),
            ["true", "false", "false"]
        );
        assert.deepEqual(
            [...scMenu.el.querySelectorAll("[data-company-id] .log_into")].map(
                (el) => el.ariaPressed
            ),
            ["true", "false", "false"]
        );

        /**
         *   [x] **Hermit**
         *   [x] Herman's      -> toggle
         *   [ ] Heroes TM
         */
        await click(scMenu.el.querySelectorAll(".toggle_company")[1]);
        assert.containsOnce(scMenu.el, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 1);
        assert.deepEqual(
            [...scMenu.el.querySelectorAll("[data-company-id] .toggle_company")].map(
                (el) => el.ariaChecked
            ),
            ["true", "true", "false"]
        );
        assert.deepEqual(
            [...scMenu.el.querySelectorAll("[data-company-id] .log_into")].map(
                (el) => el.ariaPressed
            ),
            ["true", "false", "false"]
        );
        await prom;
        assert.verifySteps(["cids=3%2C2"]);
    });

    QUnit.test("can toggle multiple companies at once", async (assert) => {
        assert.expect(11);

        const prom = makeDeferred();
        function onPushState(url) {
            assert.step(url.split("#")[1]);
            prom.resolve();
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState }, ORIGINAL_TOGGLE_DELAY);

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Hermit**  -> toggle all
         *   [x] Herman's      -> toggle all
         *   [x] Heroes TM      -> toggle all
         */
        await click(scMenu.el.querySelectorAll(".toggle_company")[0]);
        await click(scMenu.el.querySelectorAll(".toggle_company")[1]);
        await click(scMenu.el.querySelectorAll(".toggle_company")[2]);
        assert.containsOnce(scMenu.el, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 1);

        assert.verifySteps([]);
        await prom; // await toggle promise
        assert.verifySteps(["cids=2%2C1"]);
    });

    QUnit.test("single company selected: toggling it off will keep it", async (assert) => {
        assert.expect(12);

        patchWithCleanup(browser, {
            setTimeout(fn) {
                return fn(); // s.t. we can directly assert changes in the hash
            },
        });
        const scMenu = await createSwitchCompanyMenu();

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.router.current.hash, { cids: 3 });
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Hermit**  -> toggle off
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        await click(scMenu.el.querySelectorAll(".toggle_company")[0]);
        assert.deepEqual(scMenu.env.services.router.current.hash, { cids: 3 });
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        assert.containsOnce(scMenu.el, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 0);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 3);
    });

    QUnit.test("single company mode: companies can be logged in", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState });

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 2);

        /**
         *   [x] **Hermit**
         *   [ ] Herman's      -> log into
         *   [ ] Heroes TM
         */
        await click(scMenu.el.querySelectorAll(".log_into")[1]);
        assert.containsNone(scMenu.el, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps(["cids=2"]);
    });

    QUnit.test("multi company mode: log into a non selected company", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        Object.assign(browser.location, { hash: "cids=3%2C1" });
        const scMenu = await createSwitchCompanyMenu({ onPushState });

        /**
         *   [x] Hermit
         *   [ ] Herman's
         *   [x] **Heroes TM**
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3, 1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 1);

        /**
         *   [x] Hermit
         *   [ ] Herman's      -> log into
         *   [x] **Heroes TM**
         */
        await click(scMenu.el.querySelectorAll(".log_into")[1]);
        assert.containsNone(scMenu.el, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps(["cids=2%2C3%2C1"]);
    });

    QUnit.test("multi company mode: log into an already selected company", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        Object.assign(browser.location, { hash: "cids=2%2C1" });
        const scMenu = await createSwitchCompanyMenu({ onPushState });

        /**
         *   [ ] Hermit
         *   [x] **Herman's**
         *   [x] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [2, 1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 2);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 1);

        /**
         *   [ ] Hermit
         *   [x] **Herman's**
         *   [x] Heroes TM      -> log into
         */
        await click(scMenu.el.querySelectorAll(".log_into")[2]);
        assert.containsNone(scMenu.el, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps(["cids=1%2C2"]);
    });

    QUnit.test("companies can be logged in even if some toggled within delay", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState }, ORIGINAL_TOGGLE_DELAY);

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(scMenu.el.querySelector(".dropdown-toggle"));
        assert.containsN(scMenu.el, "[data-company-id]", 3);
        assert.containsN(scMenu.el, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenu.el, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Hermit**  -> toggled
         *   [ ] Herman's      -> logged in
         *   [ ] Heroes TM      -> toggled
         */
        await click(scMenu.el.querySelectorAll(".toggle_company")[2]);
        await click(scMenu.el.querySelectorAll(".toggle_company")[0]);
        await click(scMenu.el.querySelectorAll(".log_into")[1]);
        assert.containsNone(scMenu.el, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps(["cids=2"]);
    });
});
