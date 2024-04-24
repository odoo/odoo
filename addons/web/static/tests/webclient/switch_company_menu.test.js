import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllAttributes } from "@odoo/hoot-dom";
import { Deferred, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { session } from "@web/session";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { cookie } from "@web/core/browser/cookie";

const ORIGINAL_TOGGLE_DELAY = SwitchCompanyMenu.toggleDelay;

async function createSwitchCompanyMenu(options = { toggleDelay: 0 }) {
    patchWithCleanup(SwitchCompanyMenu, { toggleDelay: options.toggleDelay });
    if (options.onSetCookie) {
        const set = cookie.set;
        patchWithCleanup(cookie, {
            set(key, value) {
                set.apply(cookie, [key, value]);
                if (options.onSetCookie) {
                    options.onSetCookie(key, value);
                }
            },
        });
    }
    await mountWithCleanup(SwitchCompanyMenu);
}

describe.current.tags("desktop");

beforeEach(() => {
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
});

test("basic rendering", async () => {
    await createSwitchCompanyMenu();

    expect("div.o_switch_company_menu").toHaveCount(1);
    expect("div.o_switch_company_menu").toHaveText("Hermit");

    await contains(".dropdown-toggle").click();
    expect(".toggle_company").toHaveCount(5);
    expect(".log_into").toHaveCount(5);
    expect(".fa-check-square").toHaveCount(1);
    expect(".fa-square-o").toHaveCount(4);
    expect(".dropdown-item:has(.fa-check-square)").toHaveText("Hermit");
    expect(".dropdown-item:has(.fa-square-o):eq(0)").toHaveText("Herman's");
    expect(".dropdown-menu").toHaveText("Hermit\nHerman's\nHeroes TM\nHercules\nHulk");
});

test("companies can be toggled: toggle a second company", async () => {
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
        }
    }
    await createSwitchCompanyMenu({ onSetCookie });
    expect(["3"]).toVerifySteps();

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);
    expect(queryAllAttributes("[data-company-id] .toggle_company", "aria-checked")).toEqual([
        "true",
        "false",
        "false",
        "false",
        "false",
    ]);
    expect(queryAllAttributes("[data-company-id] .log_into", "aria-pressed")).toEqual([
        "true",
        "false",
        "false",
        "false",
        "false",
    ]);

    /**
     *   [x] **Hermit**
     *   [x] Herman's      -> toggle
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".toggle_company:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);
    expect(queryAllAttributes("[data-company-id] .toggle_company", "aria-checked")).toEqual([
        "true",
        "true",
        "false",
        "false",
        "false",
    ]);
    expect(queryAllAttributes("[data-company-id] .log_into", "aria-pressed")).toEqual([
        "true",
        "false",
        "false",
        "false",
        "false",
    ]);
    expect(["3-2"]).toVerifySteps();
});

test("can toggle multiple companies at once", async () => {
    const prom = new Deferred();
    let step = 0;
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
            if (step === 1) {
                prom.resolve();
            }
            step++;
        }
    }
    await createSwitchCompanyMenu({ onSetCookie, toggleDelay: ORIGINAL_TOGGLE_DELAY });
    expect(["3"]).toVerifySteps();

    /**
     *   [ ] Hermit          -> toggle all
     *   [x] **Herman's**    -> toggle all
     *   [x] Heroes TM       -> toggle all
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);

    /**
     *   [x] **Hermit**
     *   [x] Herman's      -> toggle
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".toggle_company:eq(0)").click();
    await contains(".toggle_company:eq(1)").click();
    await contains(".toggle_company:eq(2)").click();
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-check-square").toHaveCount(4);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    expect([]).toVerifySteps();
    await prom;
    expect(["2-1-4-5"]).toVerifySteps();
});

test("single company selected: toggling it off will keep it", async () => {
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
        }
    }
    await createSwitchCompanyMenu({ onSetCookie });
    expect(["3"]).toVerifySteps();

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await runAllTimers();
    expect(cookie.get("cids")).toBe("3");
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);

    /**
     *   [x] **Hermit**  -> toggle off
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".toggle_company:eq(0)").click();
    await runAllTimers();

    expect(["3"]).toVerifySteps();
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-check-square").toHaveCount(0);
    expect("[data-company-id] .fa-square-o").toHaveCount(5);
});

test("single company mode: companies can be logged in", async () => {
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
        }
    }
    await createSwitchCompanyMenu({ onSetCookie, toggleDelay: ORIGINAL_TOGGLE_DELAY });
    expect(["3"]).toVerifySteps();

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);

    /**
     *   [ ] Hermit
     *   [x] **Herman's**     -> log into
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(["2"]).toVerifySteps();
});

test("multi company mode: log into a non selected company", async () => {
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
        }
    }
    cookie.set("cids", "3-1");
    await createSwitchCompanyMenu({ onSetCookie });
    expect(["3-1"]).toVerifySteps();

    /**
     *   [x] Hermit
     *   [ ] Herman's
     *   [x] **Heroes TM**
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3, 1]);
    expect(getService("company").currentCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);

    /**
     *   [ ] Hermit
     *   [x] **Herman's**    -> log into
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(["2"]).toVerifySteps();
});

test("multi company mode: log into an already selected company", async () => {
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
        }
    }
    cookie.set("cids", "2-1");
    await createSwitchCompanyMenu({ onSetCookie });
    expect(["2-1"]).toVerifySteps();

    /**
     *   [ ] Hermit
     *   [x] **Herman's**
     *   [x] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([2, 1]);
    expect(getService("company").currentCompany.id).toBe(2);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);

    /**
     *   [ ] Hermit
     *   [ ] Herman's
     *   [x] **Heroes TM**    -> log into
     *   [x]    Hercules
     *   [x]    Hulk
     */
    await contains(".log_into:eq(2)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(["1-4-5"]).toVerifySteps();
});

test("companies can be logged in even if some toggled within delay", async () => {
    function onSetCookie(key, values) {
        if (key === "cids") {
            expect.step(values);
        }
    }
    await createSwitchCompanyMenu({ onSetCookie, toggleDelay: ORIGINAL_TOGGLE_DELAY });
    expect(["3"]).toVerifySteps();

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);

    /**
     *   [ ] Hermit         -> toggled
     *   [x] **Herman's**   -> logged in
     *   [ ] Heroes TM      -> toggled
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".toggle_company:eq(2)").click();
    await contains(".toggle_company:eq(0)").click();
    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(["2"]).toVerifySteps();
});
