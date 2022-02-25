/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { makeTestEnv } from "../helpers/mock_env";
import { companyService } from "@web/webclient/company_service";
import { click, getFixture, makeDeferred, mount, patchWithCleanup } from "../helpers/utils";
import { uiService } from "@web/core/ui/ui_service";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");

let target;

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
    const scMenu = await mount(SwitchCompanyMenu, target, { env });
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
        target = getFixture();
    });

    QUnit.test("basic rendering", async (assert) => {
        assert.expect(9);

        await createSwitchCompanyMenu();

        assert.containsOnce(target, "div.o_switch_company_menu");
        assert.strictEqual(target.querySelector("div.o_switch_company_menu").textContent, "Hermit");

        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, ".toggle_company", 3);
        assert.containsN(target, ".log_into", 3);
        assert.containsOnce(target, ".fa-check-square");
        assert.containsN(target, ".fa-square-o", 2);
        assert.strictEqual(
            target.querySelector(".fa-check-square").closest(".dropdown-item").textContent,
            "Hermit"
        );
        assert.strictEqual(
            target.querySelector(".fa-square-o").closest(".dropdown-item").textContent,
            "Herman's"
        );
        assert.strictEqual(
            target.querySelector(".dropdown-menu").textContent,
            "HermitHerman'sHeroes TM"
        );
    });

    QUnit.test("companies can be toggled: toggle a second company", async (assert) => {
        assert.expect(10);

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
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 2);

        /**
         *   [x] **Hermit**
         *   [x] Herman's      -> toggle
         *   [ ] Heroes TM
         */
        await click(target.querySelectorAll(".toggle_company")[1]);
        assert.containsOnce(target, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 1);
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
        const scMenu = await createSwitchCompanyMenu({ onPushState }, 50);

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Hermit**  -> toggle all
         *   [x] Herman's      -> toggle all
         *   [x] Heroes TM      -> toggle all
         */
        await click(target.querySelectorAll(".toggle_company")[0]);
        await click(target.querySelectorAll(".toggle_company")[1]);
        await click(target.querySelectorAll(".toggle_company")[2]);
        assert.containsOnce(target, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 1);

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
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Hermit**  -> toggle off
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        await click(target.querySelectorAll(".toggle_company")[0]);
        assert.deepEqual(scMenu.env.services.router.current.hash, { cids: 3 });
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        assert.containsOnce(target, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(target, "[data-company-id] .fa-check-square", 0);
        assert.containsN(target, "[data-company-id] .fa-square-o", 3);
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
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 2);

        /**
         *   [x] **Hermit**
         *   [ ] Herman's      -> log into
         *   [ ] Heroes TM
         */
        await click(target.querySelectorAll(".log_into")[1]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
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
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 1);

        /**
         *   [x] Hermit
         *   [ ] Herman's      -> log into
         *   [x] **Heroes TM**
         */
        await click(target.querySelectorAll(".log_into")[1]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
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
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 1);

        /**
         *   [ ] Hermit
         *   [x] **Herman's**
         *   [x] Heroes TM      -> log into
         */
        await click(target.querySelectorAll(".log_into")[2]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps(["cids=1%2C2"]);
    });

    QUnit.test("companies can be logged in even if some toggled within delay", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState }, 50);

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         */
        assert.deepEqual(scMenu.env.services.company.allowedCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 3);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Hermit**  -> toggled
         *   [ ] Herman's      -> logged in
         *   [ ] Heroes TM      -> toggled
         */
        await click(target.querySelectorAll(".toggle_company")[2]);
        await click(target.querySelectorAll(".toggle_company")[0]);
        await click(target.querySelectorAll(".log_into")[1]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps(["cids=2"]);
    });
});
