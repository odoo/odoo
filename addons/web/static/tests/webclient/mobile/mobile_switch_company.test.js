import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    mountWithCleanup,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";

import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";
import { MobileSwitchCompanyMenu } from "@web/webclient/burger_menu/mobile_switch_company_menu/mobile_switch_company_menu";

const ORIGINAL_TOGGLE_DELAY = MobileSwitchCompanyMenu.toggleDelay;

async function createSwitchCompanyMenu(options = { toggleDelay: 0 }) {
    patchWithCleanup(MobileSwitchCompanyMenu, { toggleDelay: options.toggleDelay });
    await mountWithCleanup(MobileSwitchCompanyMenu);
}

function patchUserActiveCompanies(cids) {
    patchWithCleanup(
        user.activeCompanies,
        cids.map((cid) => serverState.companies.find((company) => company.id === cid))
    );
}

describe.current.tags("mobile");

const clickConfirm = () => contains(".o_switch_company_menu_buttons button:first").click();

/**
 * @param {number} index
 */
const toggleCompany = async (index) =>
    contains(`[data-company-id] [role=menuitemcheckbox]:eq(${index})`).click();

beforeEach(() => {
    serverState.companies = [
        { id: 1, name: "Hermit", parent_id: false, child_ids: [] },
        { id: 2, name: "Herman's", parent_id: false, child_ids: [] },
        { id: 3, name: "Heroes TM", parent_id: false, child_ids: [] },
    ];
});

test("basic rendering", async () => {
    await mountWithCleanup(MobileSwitchCompanyMenu);

    expect(".o_burger_menu_companies").toHaveProperty("tagName", "DIV");
    expect(".o_burger_menu_companies").toHaveClass("o_burger_menu_companies");
    expect("[data-company-id]").toHaveCount(3);
    expect(".log_into").toHaveCount(3);
    expect(".fa-check-square").toHaveCount(1);
    expect(".fa-square-o").toHaveCount(2);

    expect(".o_switch_company_item:eq(0)").toHaveText("Hermit");
    expect(".o_switch_company_item:eq(0)").toHaveClass("alert-secondary");
    expect(".o_switch_company_item:eq(1)").toHaveText("Herman's");
    expect(".o_switch_company_item:eq(2)").toHaveText("Heroes TM");

    expect(".o_switch_company_item i:eq(0)").toHaveClass("fa-check-square");
    expect(".o_switch_company_item i:eq(1)").toHaveClass("fa-square-o");
    expect(".o_switch_company_item i:eq(2)").toHaveClass("fa-square-o");

    expect(".o_burger_menu_companies").toHaveText("Companies\nHermit\nHerman's\nHeroes TM");
});

test("companies can be toggled: toggle a second company", async () => {
    await createSwitchCompanyMenu();

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [x] **Company 1**
     *   [x] Company 2      -> toggle
     *   [ ] Company 3
     */
    await toggleCompany(1);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);
    await clickConfirm();
    expect(cookie.get("cids")).toEqual("1-2");
});

test("can toggle multiple companies at once", async () => {
    await createSwitchCompanyMenu({ toggleDelay: ORIGINAL_TOGGLE_DELAY });
    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**  -> toggle all
     *   [x] Company 2      -> toggle all
     *   [x] Company 3      -> toggle all
     */
    await toggleCompany(0);
    await toggleCompany(1);
    await toggleCompany(2);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    expect.verifySteps([]);
    await clickConfirm();
    expect(cookie.get("cids")).toEqual("2-3");
});

test("single company selected: toggling it off will keep it", async () => {
    await createSwitchCompanyMenu();

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    await runAllTimers();
    expect(cookie.get("cids")).toBe("1");
    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**  -> toggle off
     *   [ ] Company 2
     *   [ ] Company 3
     */
    await toggleCompany(0);
    await clickConfirm();
    expect(cookie.get("cids")).toEqual("1");
    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);
});

test("single company mode: companies can be logged in", async () => {
    await createSwitchCompanyMenu();

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**
     *   [x] Company 2      -> log into
     *   [ ] Company 3
     */
    await contains(".log_into:eq(1)").click();
    expect(cookie.get("cids")).toEqual("2");
});

test("multi company mode: log into a non selected company", async () => {
    patchUserActiveCompanies([3, 1]);
    await createSwitchCompanyMenu();

    /**
     *   [x] Company 1
     *   [ ] Company 2
     *   [x] **Company 3**
     */
    expect(user.activeCompanies.map((c) => c.id)).toEqual([3, 1]);
    expect(user.activeCompany.id).toBe(3);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    /**
     *   [x] Company 1
     *   [ ] Company 2      -> log into
     *   [x] **Company 3**
     */
    await contains(".log_into:eq(1)").click();
    expect(cookie.get("cids")).toEqual("2-1-3"); // 1-3 in that order, they are sorted
});

test("multi company mode: log into an already selected company", async () => {
    patchUserActiveCompanies([2, 3]);
    await createSwitchCompanyMenu();

    /**
     *   [ ] Company 1
     *   [x] **Company 2**
     *   [x] Company 3
     */
    expect(user.activeCompanies.map((c) => c.id)).toEqual([2, 3]);
    expect(user.activeCompany.id).toBe(2);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    /**
     *   [ ] Company 1
     *   [x] **Company 2**
     *   [x] Company 3      -> log into
     */
    await contains(".log_into:eq(2)").click();
    expect(cookie.get("cids")).toEqual("3-2");
});

test("companies can be logged in even if some toggled within delay", async () => {
    await createSwitchCompanyMenu({ toggleDelay: ORIGINAL_TOGGLE_DELAY });

    /**
     *   [x] **Company 1**
     *   [ ] Company 2
     *   [ ] Company 3
     */
    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [ ] **Company 1**  -> toggled
     *   [ ] Company 2      -> logged in
     *   [ ] Company 3      -> toggled
     */
    await contains("[data-company-id] [role=menuitemcheckbox]:eq(2)").click();
    await contains("[data-company-id] [role=menuitemcheckbox]:eq(0)").click();
    await contains(".log_into:eq(1)").click();
    expect(cookie.get("cids")).toEqual("2");
});

test("show confirm and reset buttons only when selection has changed", async () => {
    await mountWithCleanup(MobileSwitchCompanyMenu);
    expect(".o_switch_company_menu_buttons").toHaveCount(0);
    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons button").toHaveCount(2);
    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons").toHaveCount(0);
});

test("No collapse and no search input when less that 10 companies", async () => {
    await mountWithCleanup(MobileSwitchCompanyMenu);
    expect(".o_burger_menu_companies .fa-caret-right").toHaveCount(0);
    expect(".o_burger_menu_companies .visually-hidden input").toHaveCount(1);
});

test("Show search input when more that 10 companies & search filters items but ignore case and spaces", async () => {
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Herman's", sequence: 2, parent_id: false, child_ids: [] },
        { id: 1, name: "Heroes TM", sequence: 3, parent_id: false, child_ids: [4, 5] },
        { id: 4, name: "Hercules", sequence: 4, parent_id: 1, child_ids: [] },
        { id: 5, name: "Hulk", sequence: 5, parent_id: 1, child_ids: [] },
        { id: 6, name: "Random Company a", sequence: 6, parent_id: false, child_ids: [7, 8] },
        { id: 7, name: "Random Company aa", sequence: 7, parent_id: 6, child_ids: [] },
        { id: 8, name: "Random Company ab", sequence: 8, parent_id: 6, child_ids: [] },
        { id: 9, name: "Random d", sequence: 9, parent_id: false, child_ids: [] },
        { id: 10, name: "Random e", sequence: 10, parent_id: false, child_ids: [] },
    ];
    await createSwitchCompanyMenu();
    await contains(".o_burger_menu_companies > div").click();
    expect(".o_burger_menu_companies input").toHaveCount(1);
    expect(".o_burger_menu_companies input").not.toBeFocused();

    expect(".o_switch_company_item").toHaveCount(10);
    contains(".o_burger_menu_companies input").edit("omcom");
    await animationFrame();

    expect(".o_switch_company_item").toHaveCount(3);
    expect(queryAllTexts(".o_switch_company_item.o-navigable")).toEqual([
        "Random Company a",
        "Random Company aa",
        "Random Company ab",
    ]);
});
