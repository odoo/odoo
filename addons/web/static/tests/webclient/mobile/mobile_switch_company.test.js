import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { Deferred, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { session } from "@web/session";
import { MobileSwitchCompanyMenu } from "@web/webclient/burger_menu/mobile_switch_company_menu/mobile_switch_company_menu";

const ORIGINAL_TOGGLE_DELAY = MobileSwitchCompanyMenu.toggleDelay;

async function createSwitchCompanyMenu(routerParams = {}, toggleDelay = 0) {
    patchWithCleanup(MobileSwitchCompanyMenu, { toggleDelay });
    if (routerParams.onPushState) {
        const pushState = browser.history.pushState;
        patchWithCleanup(browser.history, {
            pushState(state, title, url) {
                pushState.apply(browser.history, ...arguments);
                if (routerParams.onPushState) {
                    routerParams.onPushState(url);
                }
            },
        });
    }
    await mountWithCleanup(MobileSwitchCompanyMenu);
}

describe.current.tags("mobile");

beforeEach(() => {
    patchWithCleanup(session.user_companies, {
        allowed_companies: {
            1: { id: 1, name: "Hermit", parent_id: false, child_ids: [] },
            2: { id: 2, name: "Herman's", parent_id: false, child_ids: [] },
            3: { id: 3, name: "Heroes TM", parent_id: false, child_ids: [] },
        },
        current_company: 1,
    });
});

test("basic rendering", async () => {
    await createSwitchCompanyMenu();

    expect(".o_burger_menu_companies").toHaveProperty("tagName", "DIV");
    expect(".o_burger_menu_companies").toHaveClass("o_burger_menu_companies");
    expect(".toggle_company").toHaveCount(3);
    expect(".log_into").toHaveCount(3);
    expect(".fa-check-square").toHaveCount(1);
    expect(".fa-square-o").toHaveCount(2);

    expect(".menu_companies_item:eq(0)").toHaveText("Hermit(current)");
    expect(".menu_companies_item:eq(1)").toHaveText("Herman's");
    expect(".menu_companies_item:eq(2)").toHaveText("Heroes TM");

    expect(".menu_companies_item i:eq(0)").toHaveClass("fa-check-square");
    expect(".menu_companies_item i:eq(1)").toHaveClass("fa-square-o");
    expect(".menu_companies_item i:eq(2)").toHaveClass("fa-square-o");

    expect(".o_burger_menu_companies").toHaveText(
        "Companies\nHermit(current)\nHerman's\nHeroes TM"
    );
});

test("companies can be toggled: toggle a second company", async () => {
    const prom = new Deferred();
    function onPushState(url) {
        expect.step(url.split("?")[1]);
        prom.resolve();
    }
    await createSwitchCompanyMenu({ onPushState });

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [x] **Company 1**
     *   [x] Company 2      -> toggle
     *   [ ] Company 3
     */
    await contains(".toggle_company:eq(1)").click();
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);
    await prom;
    expect(["cids=1-2"]).toVerifySteps();
});

test("can toggle multiple companies at once", async () => {
    const prom = new Deferred();
    function onPushState(url) {
        expect.step(url.split("?")[1]);
        prom.resolve();
    }
    await createSwitchCompanyMenu({ onPushState }, ORIGINAL_TOGGLE_DELAY);

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**  -> toggle all
     *   [x] Company 2      -> toggle all
     *   [x] Company 3      -> toggle all
     */
    await contains(".toggle_company:eq(0)").click();
    await contains(".toggle_company:eq(1)").click();
    await contains(".toggle_company:eq(2)").click();
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    expect([]).toVerifySteps();
    await prom; // await toggle promise
    expect(["cids=2-3"]).toVerifySteps();
});

test("single company selected: toggling it off will keep it", async () => {
    await createSwitchCompanyMenu();

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    await runAllTimers();
    expect(router.current).toEqual({ cids: 1 });
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**  -> toggle off
     *   [ ] Company 2
     *   [ ] Company 3
     */
    await contains(".toggle_company:eq(0)").click();
    await runAllTimers();

    expect(router.current).toEqual({
        cids: 1,
    });
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
    expect("[data-company-id] .fa-check-squarqe").toHaveCount(0);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);
});

test("single company mode: companies can be logged in", async () => {
    function onPushState(url) {
        expect.step(url.split("?")[1]);
    }
    await createSwitchCompanyMenu({ onPushState });

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [x] **Company 1**
     *   [ ] Company 2      -> log into
     *   [ ] Company 3
     */
    await contains(".log_into:eq(1)").click();
    expect(["cids=2"]).toVerifySteps();
});

test("multi company mode: log into a non selected company", async () => {
    function onPushState(url) {
        expect.step(url.split("?")[1]);
    }
    browser.location.search = "cids=3-1";
    await createSwitchCompanyMenu({ onPushState });

    /**
     *   [x] Company 1
     *   [ ] Company 2
     *   [x] **Company 3**
     */
    expect(getService("company").activeCompanyIds).toEqual([3, 1]);
    expect(getService("company").currentCompany.id).toBe(3);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    /**
     *   [x] Company 1
     *   [ ] Company 2      -> log into
     *   [x] **Company 3**
     */
    await contains(".log_into:eq(1)").click();
    expect(["cids=2"]).toVerifySteps();
});

test("multi company mode: log into an already selected company", async () => {
    function onPushState(url) {
        expect.step(url.split("?")[1]);
    }
    browser.location.search = "cids=2-3";
    await createSwitchCompanyMenu({ onPushState });

    /**
     *   [ ] Company 1
     *   [x] **Company 2**
     *   [x] Company 3
     */
    expect(getService("company").activeCompanyIds).toEqual([2, 3]);
    expect(getService("company").currentCompany.id).toBe(2);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    /**
     *   [ ] Company 1
     *   [x] **Company 2**
     *   [x] Company 3      -> log into
     */
    await contains(".log_into:eq(2)").click();
    expect(["cids=3"]).toVerifySteps();
});

test("companies can be logged in even if some toggled within delay", async () => {
    function onPushState(url) {
        expect.step(url.split("?")[1]);
    }
    await createSwitchCompanyMenu({ onPushState }, ORIGINAL_TOGGLE_DELAY);

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**  -> toggled
     *   [ ] Company 2      -> logged in
     *   [ ] Company 3      -> toggled
     */
    await contains(".toggle_company:eq(2)").click();
    await contains(".toggle_company:eq(0)").click();
    await contains(".log_into:eq(1)").click();
    expect(["cids=2"]).toVerifySteps();
});
