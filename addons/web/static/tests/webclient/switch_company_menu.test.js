import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { edit, keyDown, press, queryAllAttributes, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";

import { cookie } from "@web/core/browser/cookie";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";

describe.current.tags("desktop");

const clickConfirm = () => contains(".o_switch_company_menu_buttons button:first").click();

const openCompanyMenu = () => contains(".dropdown-toggle").click();

const stepOnCookieChange = () =>
    patchWithCleanup(cookie, {
        set(key, value) {
            if (key === "cids") {
                expect.step(value);
            }
            return super.set(key, value);
        },
    });

/**
 * @param {number} index
 */
const toggleCompany = (index) =>
    contains(`[data-company-id] [role=menuitemcheckbox]:eq(${index})`).click();

beforeEach(() => {
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Herman's", sequence: 2, parent_id: false, child_ids: [] },
        { id: 1, name: "Heroes TM", sequence: 3, parent_id: false, child_ids: [4, 5] },
        { id: 4, name: "Hercules", sequence: 4, parent_id: 1, child_ids: [] },
        { id: 5, name: "Hulk", sequence: 5, parent_id: 1, child_ids: [] },
    ];
});

test("basic rendering", async () => {
    await mountWithCleanup(SwitchCompanyMenu);

    expect("div.o_switch_company_menu").toHaveCount(1);
    expect("div.o_switch_company_menu").toHaveText("Hermit");

    await openCompanyMenu();

    expect("[data-company-id] [role=menuitemcheckbox]").toHaveCount(5);
    expect(".log_into").toHaveCount(5);
    expect(".fa-check-square").toHaveCount(1);
    expect(".fa-square-o").toHaveCount(4);
    expect(".dropdown-item:has(.fa-check-square)").toHaveText("Hermit");
    expect(".dropdown-item:has(.fa-square-o):eq(0)").toHaveText("Herman's");
    expect(".dropdown-menu").toHaveText("Hermit\nHerman's\nHeroes TM\nHercules\nHulk");
});

test("companies can be toggled: toggle a second company", async () => {
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);

    expect.verifySteps(["3"]);

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);
    expect(queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked")).toEqual(
        ["true", "false", "false", "false", "false"]
    );
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
    await toggleCompany(1);
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);
    expect(queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked")).toEqual(
        ["true", "true", "false", "false", "false"]
    );
    expect(queryAllAttributes("[data-company-id] .log_into", "aria-pressed")).toEqual([
        "true",
        "false",
        "false",
        "false",
        "false",
    ]);
    await clickConfirm();
    expect.verifySteps(["3-2"]);
});

test("can toggle multiple companies at once", async () => {
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);

    expect.verifySteps(["3"]);

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(4);

    /**
     *   [ ] Hermit          -> toggle all
     *   [x] **Herman's**    -> toggle all
     *   [x] Heroes TM       -> toggle all
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await toggleCompany(0);
    await toggleCompany(1);
    await toggleCompany(2);
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-check-square").toHaveCount(4);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    expect.verifySteps([]);
    await clickConfirm();
    expect.verifySteps(["2-1-4-5"]);
});

test("single company selected: toggling it off will keep it", async () => {
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);

    expect.verifySteps(["3"]);

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
    await openCompanyMenu();
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
    await toggleCompany(0);
    await clickConfirm();
    await animationFrame();
    expect.verifySteps(["3"]);
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);

    await openCompanyMenu();
    expect("[data-company-id] .fa-check-square").toHaveCount(0);
    expect("[data-company-id] .fa-square-o").toHaveCount(5);
});

test("single company mode: companies can be logged in", async () => {
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);

    expect.verifySteps(["3"]);

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await openCompanyMenu();
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
    expect.verifySteps(["2"]);
});

test("multi company mode: log into a non selected company", async () => {
    cookie.set("cids", "3-1");
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["3-1"]);

    /**
     *   [x] Hermit
     *   [ ] Herman's
     *   [x] **Heroes TM**
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3, 1]);
    expect(getService("company").currentCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);

    /**
     *   [x] Hermit
     *   [x] **Herman's**    -> log into
     *   [x] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect.verifySteps(["2-3-1"]);
});

test("multi company mode: log into an already selected company", async () => {
    cookie.set("cids", "2-1");
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["2-1"]);

    /**
     *   [ ] Hermit
     *   [x] **Herman's**
     *   [x] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([2, 1]);
    expect(getService("company").currentCompany.id).toBe(2);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(2);
    expect("[data-company-id] .fa-square-o").toHaveCount(3);

    /**
     *   [ ] Hermit
     *   [x] Herman's
     *   [x] **Heroes TM**    -> log into
     *   [x]    Hercules
     *   [x]    Hulk
     */
    await contains(".log_into:eq(2)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect.verifySteps(["1-2-4-5"]);
});

test("companies can be logged in even if some toggled within delay", async () => {
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["3"]);

    /**
     *   [x] **Hermit**
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await openCompanyMenu();
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
    await contains("[data-company-id] [role=menuitemcheckbox]:eq(2)").click();
    await contains("[data-company-id] [role=menuitemcheckbox]:eq(0)").click();
    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect.verifySteps(["2"]);
});

test("always show the name of the company on the top right of the app", async () => {
    // initialize a single company
    serverState.companies = [
        { id: 1, name: "Single company", sequence: 1, parent_id: false, child_ids: [] },
    ];

    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["1"]);

    // in case of a single company, drop down button should be displayed but disabled
    expect(".dropdown-toggle").toBeDisplayed();
    expect(".dropdown-toggle").not.toBeEnabled();
    expect(".dropdown-toggle").toHaveText("Single company");
});

test("single company mode: from company loginto branch", async () => {
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["3"]);

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
     *   [ ] Herman's
     *   [x] **Heroes TM** -> log into
     *   [x]    Hercules
     *   [x]    Hulk
     */
    await contains(".log_into:eq(2)").click();
    expect.verifySteps(["1-4-5"]);
});

test("single company mode: from branch loginto company", async () => {
    cookie.set("cids", "1-4-5");
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["1-4-5"]);

    /**
     *   [ ] Hermit
     *   [ ] Herman's
     *   [x] **Heroes TM**
     *   [x]    Hercules
     *   [x]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([1, 4, 5]);
    expect(getService("company").currentCompany.id).toBe(1);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(3);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [x] Hermit    -> log into
     *   [ ] Herman's
     *   [ ] Heroes TM
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    await contains(".log_into:eq(0)").click();
    expect.verifySteps(["3"]);
});

test("single company mode: from leaf (only one company in branch selected) loginto company", async () => {
    cookie.set("cids", "1");
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["1"]);

    /**
     *   [ ] Hermit
     *   [ ] Herman's
     *   [x] **Heroes TM**
     *   [ ]    Hercules
     *   [ ]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([1]);
    expect(getService("company").currentCompany.id).toBe(1);
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
    expect.verifySteps(["2"]);
});

test("multi company mode: switching company doesn't deselect already selected ones", async () => {
    cookie.set("cids", "1-2-4-5");
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["1-2-4-5"]);

    /**
     *   [ ] Hermit
     *   [x] Herman's
     *   [x] **Heroes TM**
     *   [x]    Hercules
     *   [x]    Hulk
     */
    expect(getService("company").activeCompanyIds).toEqual([1, 2, 4, 5]);
    expect(getService("company").currentCompany.id).toBe(1);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-check-square").toHaveCount(4);
    expect("[data-company-id] .fa-square-o").toHaveCount(1);

    /**
     *   [ ] Hermit
     *   [x] **Herman's** -> log into
     *   [x] Heroes TM
     *   [x]    Hercules
     *   [x]    Hulk
     */
    await contains(".log_into:eq(1)").click();
    expect.verifySteps(["2-1-4-5"]);
});

test("show confirm and reset buttons only when selection has changed", async () => {
    await mountWithCleanup(SwitchCompanyMenu);
    await openCompanyMenu();

    expect(".o_switch_company_menu_buttons").toHaveCount(0);

    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons button").toHaveCount(2);

    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons").toHaveCount(0);
});

test("no search input when less that 10 companies", async () => {
    await mountWithCleanup(SwitchCompanyMenu);

    await openCompanyMenu();
    expect(".o-dropdown--menu .visually-hidden input").toHaveCount(1);
});

test("show search input when more that 10 companies & search filters items but ignore case and spaces", async () => {
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

    await mountWithCleanup(SwitchCompanyMenu);

    await openCompanyMenu();
    expect(".o-dropdown--menu input").toHaveCount(1);
    expect(".o-dropdown--menu input").toBeFocused();
    expect(".o-dropdown--menu .o_switch_company_item").toHaveCount(10);

    await edit("omcom");
    await animationFrame();
    expect(".o-dropdown--menu .o_switch_company_item").toHaveCount(3);

    expect(queryAllTexts(".o-dropdown--menu .o_switch_company_item")).toEqual([
        "Random Company a",
        "Random Company aa",
        "Random Company ab",
    ]);
});

test("when less than 10 companies, typing key makes the search input visible", async () => {
    await mountWithCleanup(SwitchCompanyMenu);
    await openCompanyMenu();

    expect(".o-dropdown--menu input").toHaveCount(1);
    expect(".o-dropdown--menu input").toBeFocused();
    expect(".o-dropdown--menu .visually-hidden input").toHaveCount(1);

    await edit("a");
    await animationFrame();

    expect(".o-dropdown--menu input").toHaveValue("a");
    expect(".o-dropdown--menu :not(.visually-hidden) input").toHaveCount(1);
});

test.tags("focus required");
test("navigation with search input", async () => {
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

    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["3"]);
    await openCompanyMenu();

    expect(".o-dropdown--menu input").toBeFocused();
    expect(".o_switch_company_item.focus").toHaveCount(0);

    const navigationSteps = [
        { hotkey: "arrowdown", focused: 1, selectedCompanies: [3] }, // Go to first item
        { hotkey: "arrowup", focused: 0 }, // Go to search input
        { hotkey: "arrowup", focused: 10 }, // Go to last item
        { hotkey: "Space", focused: 10, selectedCompanies: [3, 10] }, // Select last item
        { hotkey: ["shift", "tab"], focused: 9, selectedCompanies: [3, 10] }, // Go to previous item
        { hotkey: "tab", focused: 10, selectedCompanies: [3, 10] }, // Go to next item
        { hotkey: "arrowdown", focused: 11 }, // Go to Confirm
        { hotkey: "arrowdown", focused: 12 }, // Go to Reset
        { hotkey: "enter", focused: 10, selectedCompanies: [3] }, // Reset, focus is on last item
        { hotkey: "arrowdown", focused: 0 }, // Go to seach input
        { input: "a", focused: 0 }, // Type "a"
        { hotkey: "arrowdown", focused: 1 }, // Go to first item
        { hotkey: "Space", focused: 1, selectedCompanies: [2] }, // Select first item
    ];

    for (const navigationStep of navigationSteps) {
        expect.step(navigationStep);
        const { hotkey, focused, selectedCompanies, input } = navigationStep;
        if (hotkey) {
            await press(hotkey);
        }
        if (input) {
            await edit(input);
        }

        // Ensure debounced mutation listener update and owl re-render
        await animationFrame();
        await runAllTimers();

        expect(`.o_popover .o-navigable:eq(${focused})`).toHaveClass("focus");
        expect(`.o_popover .o-navigable:eq(${focused})`).toBeFocused();

        if (selectedCompanies) {
            expect(
                queryAllAttributes(
                    ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
                    "data-company-id"
                ).map(Number)
            ).toEqual(selectedCompanies);
        }
    }

    await keyDown(["control", "enter"]);
    await animationFrame();

    expect.verifySteps([...navigationSteps, "3-2"]);
    expect(".o_switch_company_item").toHaveCount(0);
});

test("select and de-select all", async () => {
    await mountWithCleanup(SwitchCompanyMenu);
    await openCompanyMenu();

    // Show search
    await edit(" ");
    await animationFrame();

    // One company is selected, there should be a check box with minus inside
    expect("[role=menuitemcheckbox][title='Deselect all'] i").toHaveClass("fa-minus-square-o");

    await contains("[role=menuitemcheckbox][title='Deselect all']").click();
    // No company is selected, there should be a empty check box
    expect("[role=menuitemcheckbox][title='Select all'] i").toHaveClass("fa-square-o");
    expect(".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])").toHaveCount(0);

    await contains("[role=menuitemcheckbox][title='Select all']").click();
    // All companies are selected, there should be a checked check box
    expect("[role=menuitemcheckbox][title='Deselect all'] i").toHaveClass("fa-check-square");
    expect(".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])").toHaveCount(5);

    await contains("[role=menuitemcheckbox][title='Deselect all']").click();
    // No company is selected, there should be a empty check box
    expect("[role=menuitemcheckbox][title='Select all'] i").toHaveClass("fa-square-o");
    expect(".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])").toHaveCount(0);
});

test("disallowed companies in between allowed companies are not enabled", async () => {
    const companies = {
        1: { id: 1, name: "Parent", sequence: 1, parent_id: false, child_ids: [2] },
        2: { id: 2, name: "Child A", sequence: 2, parent_id: 1, child_ids: [3] },
        3: { id: 3, name: "Child B", sequence: 3, parent_id: 2, child_ids: [] },
    };

    patchWithCleanup(session.user_companies, {
        allowed_companies: companies,
        current_company: 3,
        disallowed_ancestor_companies: {
            2: companies[2]
        },
    });

    cookie.set("cids", "3");
    stepOnCookieChange();

    await mountWithCleanup(SwitchCompanyMenu);
    expect.verifySteps(["3"]);

    /**
     *   [ ] Parent
     *   [ ]    Child A
     *   [x]        Child B
     */
    expect(getService("company").activeCompanyIds).toEqual([3]);
    expect(getService("company").currentCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-check-square").toHaveCount(1);
    expect("[data-company-id] .fa-square-o").toHaveCount(2);

    /**
     *   [x] Parent -> toggle
     *   [ ]    Child A
     *   [x]        Child B
     */
    await contains(".log_into:eq(0)").click();
    expect.verifySteps(["1-3"]);
});
