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
    const scMenu = await mount(SwitchCompanyMenu, target, { env });
    return scMenu;
}

function toCIDS(...ids) {
    return `cids=${ids.join("-")}&_company_switching=1`;
}

QUnit.module("SwitchCompanyMenu", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(session.user_companies, {
            allowed_companies: {
                3: { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
                2: { id: 2, name: "Herman's", sequence: 2, parent_id: false, child_ids: [] },
                1: { id: 1, name: "Heroes TM", sequence: 3, parent_id: false, child_ids: [4, 5] },
                4: { id: 4, name: "Hercules", sequence: 4, parent_id: 1, child_ids: [] },
                5: { id: 5, name: "Hulk", sequence: 5, parent_id: 1, child_ids: [] },
            },
            disallowed_ancestor_companies: {},
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
        assert.containsN(target, ".toggle_company", 5);
        assert.containsN(target, ".log_into", 5);
        assert.containsOnce(target, ".fa-check-square");
        assert.containsN(target, ".fa-square-o", 4);
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
            "HermitHerman'sHeroes TMHerculesHulk"
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
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 4);
        assert.deepEqual(
            [...target.querySelectorAll("[data-company-id] .toggle_company")].map((el) =>
                el.getAttribute("aria-checked")
            ),
            ["true", "false", "false", "false", "false"]
        );
        assert.deepEqual(
            [...target.querySelectorAll("[data-company-id] .log_into")].map((el) =>
                el.getAttribute("aria-pressed")
            ),
            ["true", "false", "false", "false", "false"]
        );

        /**
         *   [x] **Hermit**
         *   [x] Herman's      -> toggle
         *   [ ] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".toggle_company")[1]);
        assert.containsOnce(target, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 3);
        assert.deepEqual(
            [...target.querySelectorAll("[data-company-id] .toggle_company")].map((el) =>
                el.getAttribute("aria-checked")
            ),
            ["true", "true", "false", "false", "false"]
        );
        assert.deepEqual(
            [...target.querySelectorAll("[data-company-id] .log_into")].map((el) =>
                el.getAttribute("aria-pressed")
            ),
            ["true", "false", "false", "false", "false"]
        );
        await prom;
        assert.verifySteps(["cids=3-2&_company_switching=1"]);
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
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 4);

        /**
         *   [ ] Hermit          -> toggle all
         *   [x] **Herman's**    -> toggle all
         *   [x] Heroes TM       -> toggle all
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".toggle_company")[0]);
        await click(target.querySelectorAll(".toggle_company")[1]);
        await click(target.querySelectorAll(".toggle_company")[2]);
        assert.containsOnce(target, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(target, "[data-company-id] .fa-check-square", 4);
        assert.containsN(target, "[data-company-id] .fa-square-o", 1);

        assert.verifySteps([]);
        await prom; // await toggle promise
        assert.verifySteps(["cids=2-1-4-5&_company_switching=1"]);
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
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.router.current.hash, { cids: 3 });
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 4);

        /**
         *   [x] **Hermit**  -> toggle off
         *   [ ] Herman's
         *   [ ] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".toggle_company")[0]);
        assert.deepEqual(scMenu.env.services.router.current.hash, {
            cids: 3,
            _company_switching: 1,
        });
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        assert.containsOnce(target, ".dropdown-menu", "dropdown is still opened");
        assert.containsN(target, "[data-company-id] .fa-check-square", 0);
        assert.containsN(target, "[data-company-id] .fa-square-o", 5);
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
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 4);

        /**
         *   [ ] Hermit
         *   [x] **Herman's**     -> log into
         *   [ ] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".log_into")[1]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps([toCIDS(2)]);
    });

    QUnit.test("single company mode: from company loginto branch", async (assert) => {
        assert.expect(8);
        const scMenu = await createSwitchCompanyMenu({
            onPushState: (url) => assert.step(url.split("#")[1]),
        });

        /**
         *   [x] **Hermit**
         *   [ ] Herman's
         *   [ ] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 4);

        /**
         *   [ ] Hermit
         *   [ ] Herman's
         *   [x] **Heroes TM** -> log into
         *   [x]    Hercules
         *   [x]    Hulk
         */
        await click(target.querySelectorAll(".log_into")[2]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps([toCIDS(1, 4, 5)]);
    });

    QUnit.test("single company mode: from branch loginto company", async (assert) => {
        assert.expect(8);
        Object.assign(browser.location, { hash: toCIDS(1, 4, 5) });
        const scMenu = await createSwitchCompanyMenu({
            onPushState: (url) => assert.step(url.split("#")[1]),
        });

        /**
         *   [ ] Hermit
         *   [ ] Herman's
         *   [x] **Heroes TM**
         *   [x]    Hercules
         *   [x]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1, 4, 5]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 3);
        assert.containsN(target, "[data-company-id] .fa-square-o", 2);

        /**
         *   [x] Hermit    -> log into
         *   [ ] Herman's
         *   [ ] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".log_into")[0]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps([toCIDS(3)]);
    });

    QUnit.test(
        "single company mode: from leaf (only one company in branch selected) loginto company",
        async (assert) => {
            assert.expect(8);
            Object.assign(browser.location, { hash: toCIDS(1) });

            function onPushState(url) {
                assert.step(url.split("#")[1]);
            }
            const scMenu = await createSwitchCompanyMenu({ onPushState });

            /**
             *   [ ] Hermit
             *   [ ] Herman's
             *   [x] **Heroes TM**
             *   [ ]    Hercules
             *   [ ]    Hulk
             */
            assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1]);
            assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
            await click(target.querySelector(".dropdown-toggle"));
            assert.containsN(target, "[data-company-id]", 5);
            assert.containsN(target, "[data-company-id] .fa-check-square", 1);
            assert.containsN(target, "[data-company-id] .fa-square-o", 4);

            /**
             *   [ ] Hermit
             *   [x] **Herman's**     -> log into
             *   [ ] Heroes TM
             *   [ ]    Hercules
             *   [ ]    Hulk
             */
            await click(target.querySelectorAll(".log_into")[1]);
            assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
            assert.verifySteps([toCIDS(2)]);
        }
    );

    QUnit.test("multi company mode: log into a non selected company", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        Object.assign(browser.location, { hash: toCIDS(3, 1) });
        const scMenu = await createSwitchCompanyMenu({ onPushState });

        /**
         *   [x] Hermit
         *   [ ] Herman's
         *   [x] **Heroes TM**
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3, 1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 3);

        /**
         *   [x] Hermit
         *   [x] **Herman's**    -> log into
         *   [x] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".log_into")[1]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps([toCIDS(2, 3, 1)]);
    });

    QUnit.test("multi company mode: log into an already selected company", async (assert) => {
        assert.expect(8);

        function onPushState(url) {
            assert.step(url.split("#")[1]);
        }
        Object.assign(browser.location, { hash: "cids=2-1" });
        const scMenu = await createSwitchCompanyMenu({ onPushState });

        /**
         *   [ ] Hermit
         *   [x] **Herman's**
         *   [x] Heroes TM
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [2, 1]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 2);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 2);
        assert.containsN(target, "[data-company-id] .fa-square-o", 3);

        /**
         *   [ ] Hermit
         *   [x] Herman's
         *   [x] **Heroes TM**    -> log into
         *   [x]    Hercules
         *   [x]    Hulk
         */
        await click(target.querySelectorAll(".log_into")[2]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
        assert.verifySteps([toCIDS(1, 2, 4, 5)]);
    });

    QUnit.test(
        "multi company mode: switching company doesn't deselect already selected ones",
        async (assert) => {
            assert.expect(8);
            Object.assign(browser.location, { hash: toCIDS(1, 2, 4, 5) });
            const scMenu = await createSwitchCompanyMenu({
                onPushState: (url) => assert.step(url.split("#")[1]),
            });

            /**
             *   [ ] Hermit
             *   [x] Herman's
             *   [x] **Heroes TM**
             *   [x]    Hercules
             *   [x]    Hulk
             */
            assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [1, 2, 4, 5]);
            assert.strictEqual(scMenu.env.services.company.currentCompany.id, 1);
            await click(target.querySelector(".dropdown-toggle"));
            assert.containsN(target, "[data-company-id]", 5);
            assert.containsN(target, "[data-company-id] .fa-check-square", 4);
            assert.containsN(target, "[data-company-id] .fa-square-o", 1);

            /**
             *   [ ] Hermit
             *   [x] **Herman's** -> log into
             *   [x] Heroes TM
             *   [x]    Hercules
             *   [x]    Hulk
             */
            await click(target.querySelectorAll(".log_into")[1]);
            assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");
            assert.verifySteps([toCIDS(2, 1, 4, 5)]);
        }
    );

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
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        assert.deepEqual(scMenu.env.services.company.activeCompanyIds, [3]);
        assert.strictEqual(scMenu.env.services.company.currentCompany.id, 3);
        await click(target.querySelector(".dropdown-toggle"));
        assert.containsN(target, "[data-company-id]", 5);
        assert.containsN(target, "[data-company-id] .fa-check-square", 1);
        assert.containsN(target, "[data-company-id] .fa-square-o", 4);

        /**
         *   [ ] Hermit         -> 2) toggled
         *   [x] **Herman's**   -> 3) logged in
         *   [ ] Heroes TM      -> 1) toggled
         *   [ ]    Hercules
         *   [ ]    Hulk
         */
        await click(target.querySelectorAll(".toggle_company")[2]);
        await click(target.querySelectorAll(".toggle_company")[0]);
        await click(target.querySelectorAll(".log_into")[1]);
        assert.containsNone(target, ".dropdown-menu", "dropdown is directly closed");

        // When "Herman's" is logged into, only one company is currently selected
        // so we treat it as single company mode
        assert.verifySteps([toCIDS(2)]);
    });
});
