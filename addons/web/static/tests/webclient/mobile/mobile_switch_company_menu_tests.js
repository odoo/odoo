/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    click,
    getFixture,
    makeDeferred,
    mount,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { MobileSwitchCompanyMenu } from "@web/webclient/burger_menu/mobile_switch_company_menu/mobile_switch_company_menu";
import { companyService } from "@web/webclient/company_service";
import { uiService } from "@web/core/ui/ui_service";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");
let target;

const ORIGINAL_TOGGLE_DELAY = MobileSwitchCompanyMenu.toggleDelay;
async function createSwitchCompanyMenu(routerParams = {}, toggleDelay = 0) {
    patchWithCleanup(MobileSwitchCompanyMenu, { toggleDelay });
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
    const scMenu = await mount(MobileSwitchCompanyMenu, target, { env });
    return scMenu;
}

QUnit.module("MobileSwitchCompanyMenu", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        patchWithCleanup(session.user_companies, {
            allowed_companies: {
                1: { id: 1, name: "Hermit", parent_id: false, child_ids: [] },
                2: { id: 2, name: "Herman's", parent_id: false, child_ids: [] },
                3: { id: 3, name: "Heroes TM", parent_id: false, child_ids: [] },
            },
            current_company: 1,
        });
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("company", companyService);
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.test("basic rendering", async (assert) => {
        assert.expect(13);

        await createSwitchCompanyMenu();
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        assert.strictEqual(scMenuEl.tagName.toUpperCase(), "DIV");
        assert.hasClass(scMenuEl, "o_burger_menu_companies");
        assert.containsN(scMenuEl, ".toggle_company", 3);
        assert.containsN(scMenuEl, ".log_into", 3);
        assert.containsOnce(scMenuEl, ".fa-check-square");
        assert.containsN(scMenuEl, ".fa-square-o", 2);

        assert.strictEqual(
            scMenuEl.querySelectorAll(".menu_companies_item")[0].textContent,
            "Hermit(current)"
        );
        assert.strictEqual(
            scMenuEl.querySelectorAll(".menu_companies_item")[1].textContent,
            "Herman's"
        );
        assert.strictEqual(
            scMenuEl.querySelectorAll(".menu_companies_item")[2].textContent,
            "Heroes TM"
        );

        assert.hasClass(scMenuEl.querySelectorAll(".menu_companies_item i")[0], "fa-check-square");
        assert.hasClass(scMenuEl.querySelectorAll(".menu_companies_item i")[1], "fa-square-o");
        assert.hasClass(scMenuEl.querySelectorAll(".menu_companies_item i")[2], "fa-square-o");

        assert.strictEqual(scMenuEl.textContent, "CompaniesHermit(current)Herman'sHeroes TM");
    });

    QUnit.test("companies can be toggled: toggle a second company", async (assert) => {
        assert.expect(9);

        const prom = makeDeferred();
        function onPushState(url) {
            assert.step(url.split("#")[1]);
            prom.resolve();
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState });
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [x] **Company 1**
         *   [ ] Company 2
         *   [ ] Company 3
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 2);

        /**
         *   [x] **Company 1**
         *   [x] Company 2      -> toggle
         *   [ ] Company 3
         */
        await click(scMenuEl.querySelectorAll(".toggle_company")[1]);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 1);
        await prom;
        assert.verifySteps(["cids=1-2&_company_switching=1"]);
    });

    QUnit.test("can toggle multiple companies at once", async (assert) => {
        assert.expect(10);

        const prom = makeDeferred();
        function onPushState(url) {
            assert.step(url.split("#")[1]);
            prom.resolve();
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState }, ORIGINAL_TOGGLE_DELAY);
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [x] **Company 1**
         *   [ ] Company 2
         *   [ ] Company 3
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Company 1**  -> toggle all
         *   [x] Company 2      -> toggle all
         *   [x] Company 3      -> toggle all
         */
        await click(scMenuEl.querySelectorAll(".toggle_company")[0]);
        await click(scMenuEl.querySelectorAll(".toggle_company")[1]);
        await click(scMenuEl.querySelectorAll(".toggle_company")[2]);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 1);

        assert.verifySteps([]);
        await prom; // await toggle promise
        assert.verifySteps(["cids=2-3&_company_switching=1"]);
    });

    QUnit.test("single company selected: toggling it off will keep it", async (assert) => {
        assert.expect(11);

        patchWithCleanup(browser, {
            setTimeout(fn) {
                return fn(); // s.t. we can directly assert changes in the hash
            },
        });
        const scMenu = await createSwitchCompanyMenu();
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [x] **Company 1**
         *   [ ] Company 2
         *   [ ] Company 3
         */
        assert.deepEqual(scMenu.env.services.router.current.hash, { cids: 1 });
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Company 1**  -> toggle off
         *   [ ] Company 2
         *   [ ] Company 3
         */
        await click(scMenuEl.querySelectorAll(".toggle_company")[0]);
        assert.deepEqual(scMenu.env.services.router.current.hash, {
            cids: 1,
            _company_switching: 1,
        });
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-squarqe", 0);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 3);
    });

    QUnit.test("single company mode: companies can be logged in", async (assert) => {
        assert.expect(7);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState });
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [x] **Company 1**
         *   [ ] Company 2
         *   [ ] Company 3
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 2);

        /**
         *   [x] **Company 1**
         *   [ ] Company 2      -> log into
         *   [ ] Company 3
         */
        await click(scMenuEl.querySelectorAll(".log_into")[1]);
        assert.verifySteps(["cids=2&_company_switching=1"]);
    });

    QUnit.test("multi company mode: log into a non selected company", async (assert) => {
        assert.expect(7);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        Object.assign(browser.location, { hash: "cids=3-1" });
        const scMenu = await createSwitchCompanyMenu({ onPushState });
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [x] Company 1
         *   [ ] Company 2
         *   [x] **Company 3**
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3, 1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 1);

        /**
         *   [x] Company 1
         *   [ ] Company 2      -> log into
         *   [x] **Company 3**
         */
        await click(scMenuEl.querySelectorAll(".log_into")[1]);
        assert.verifySteps(["cids=2&_company_switching=1"]);
    });

    QUnit.test("multi company mode: log into an already selected company", async (assert) => {
        assert.expect(7);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        Object.assign(browser.location, { hash: "cids=2-3" });
        const scMenu = await createSwitchCompanyMenu({ onPushState });
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [ ] Company 1
         *   [x] **Company 2**
         *   [x] Company 3
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [2, 3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 2);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 2);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 1);

        /**
         *   [ ] Company 1
         *   [x] **Company 2**
         *   [x] Company 3      -> log into
         */
        await click(scMenuEl.querySelectorAll(".log_into")[2]);
        assert.verifySteps(["cids=3&_company_switching=1"]);
    });

    QUnit.test("companies can be logged in even if some toggled within delay", async (assert) => {
        assert.expect(7);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        const scMenu = await createSwitchCompanyMenu({ onPushState }, ORIGINAL_TOGGLE_DELAY);
        const scMenuEl = target.querySelector(".o_burger_menu_companies");

        /**
         *   [x] **Company 1**
         *   [ ] Company 2
         *   [ ] Company 3
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        assert.containsN(scMenuEl, "[data-company-id]", 3);
        assert.containsN(scMenuEl, "[data-company-id] .fa-check-square", 1);
        assert.containsN(scMenuEl, "[data-company-id] .fa-square-o", 2);

        /**
         *   [ ] **Company 1**  -> toggled
         *   [ ] Company 2      -> logged in
         *   [ ] Company 3      -> toggled
         */
        await click(scMenuEl.querySelectorAll(".toggle_company")[2]);
        await click(scMenuEl.querySelectorAll(".toggle_company")[0]);
        await click(scMenuEl.querySelectorAll(".log_into")[1]);
        assert.verifySteps(["cids=2&_company_switching=1"]);
    });
});
