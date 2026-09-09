// @ts-check

import { after, beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    edit,
    keyDown,
    press,
    queryAllAttributes,
    queryAllTexts,
    queryRect,
} from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    mountWithCleanup,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { cookie } from "@web/core/browser/cookie";
import { router } from "@web/core/browser/router";
import { user } from "@web/core/user";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";

async function createSwitchCompanyMenu() {
    await mountWithCleanup(SwitchCompanyMenu);
}

function patchUserActiveCompanies(cids) {
    patchWithCleanup(
        user.activeCompanies,
        cids.map((cid) => serverState.companies.find((company) => company.id === cid)),
    );
}

describe.current.tags("desktop");

const clickConfirm = () =>
    contains(".o_switch_company_menu_buttons button:first").click();

const openCompanyMenu = () => contains(".dropdown-toggle").click();

/** @param {number} index */
const toggleCompany = (index) =>
    contains(`[data-company-id] [role=menuitemcheckbox]:eq(${index})`).click();

beforeEach(() => {
    cookie.set("cids", "3");
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Herman's", sequence: 2, parent_id: false, child_ids: [] },
        { id: 1, name: "Heroes TM", sequence: 3, parent_id: false, child_ids: [4, 5] },
        { id: 4, name: "Hercules", sequence: 4, parent_id: 1, child_ids: [] },
        { id: 5, name: "Hulk", sequence: 5, parent_id: 1, child_ids: [] },
    ];
});

test("basic rendering", async () => {
    await createSwitchCompanyMenu();

    expect("div.o_switch_company_menu").toHaveCount(1);
    expect("div.o_switch_company_menu").toHaveText("Hermit");

    await openCompanyMenu();

    expect("[data-company-id] [role=menuitemcheckbox]").toHaveCount(5);
    expect(".log_into").toHaveCount(5);
    expect(".fa-square-check").toHaveCount(1);
    expect(".fa-regular.fa-square").toHaveCount(4);
    expect(".dropdown-item:has(.fa-square-check)").toHaveText("Hermit");
    expect(".dropdown-item:has(.fa-regular.fa-square):eq(0)").toHaveText("Herman's");
    expect(".dropdown-menu").toHaveText("Hermit\nHerman's\nHeroes TM\nHercules\nHulk");
});

test("companies can be toggled: toggle a second company", async () => {
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);
    expect(
        queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked"),
    ).toEqual(["true", "false", "false", "false", "false"]);
    expect(queryAllAttributes("[data-company-id] .log_into", "aria-pressed")).toEqual([
        "true",
        "false",
        "false",
        "false",
        "false",
    ]);

    await toggleCompany(1);
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-square-check").toHaveCount(2);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(3);
    expect(
        queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked"),
    ).toEqual(["true", "true", "false", "false", "false"]);
    expect(queryAllAttributes("[data-company-id] .log_into", "aria-pressed")).toEqual([
        "true",
        "false",
        "false",
        "false",
        "false",
    ]);
    await clickConfirm();
    expect(cookie.get("cids")).toEqual("3-2");
});

test("can toggle multiple companies at once", async () => {
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);

    await toggleCompany(0);
    await toggleCompany(1);
    await toggleCompany(2);
    expect(".dropdown-menu").toHaveCount(1, { message: "dropdown is still opened" });
    expect("[data-company-id] .fa-square-check").toHaveCount(4);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(1);

    expect.verifySteps([]);
    await clickConfirm();
    expect(cookie.get("cids")).toEqual("2-1-4-5");
});

test("single company selected: toggling it off will keep it", async () => {
    await createSwitchCompanyMenu();

    await runAllTimers();
    expect(cookie.get("cids")).toBe("3");
    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);

    await toggleCompany(0);
    await clickConfirm();
    await animationFrame();
    expect(cookie.get("cids")).toEqual("3");
    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);

    await openCompanyMenu();
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);
});

test("single company mode: companies can be logged in", async () => {
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);

    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(cookie.get("cids")).toEqual("2");
});

test("multi company mode: log into a non selected company", async () => {
    patchUserActiveCompanies([3, 1]);
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3, 1]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(2);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(3);

    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(cookie.get("cids")).toEqual("2-1-3");
});

test("multi company mode: log into an already selected company", async () => {
    patchUserActiveCompanies([2, 1]);
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([2, 1]);
    expect(user.activeCompany.id).toBe(2);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(2);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(3);

    await contains(".log_into:eq(2)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(cookie.get("cids")).toEqual("1-2-4-5");
});

test("logging into a company discards pending toggles", async () => {
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);

    await contains("[data-company-id] [role=menuitemcheckbox]:eq(2)").click();
    await contains("[data-company-id] [role=menuitemcheckbox]:eq(0)").click();
    await contains(".log_into:eq(1)").click();
    expect(".dropdown-menu").toHaveCount(0, { message: "dropdown is directly closed" });
    expect(cookie.get("cids")).toEqual("2");
});

test("always show the name of the company on the top right of the app", async () => {
    const companyName = "Single company";
    serverState.companies = [
        { id: 1, name: companyName, sequence: 1, parent_id: false, child_ids: [] },
    ];

    await createSwitchCompanyMenu();

    expect(".dropdown-toggle").toBeVisible();
    expect(".dropdown-toggle").not.toBeEnabled();
    expect(".dropdown-toggle").toHaveText(companyName);
});

test("single company mode: from company loginto branch", async () => {
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);

    await contains(".log_into:eq(2)").click();
    expect(cookie.get("cids")).toEqual("1-4-5");
});

test("single company mode: from branch loginto company", async () => {
    patchUserActiveCompanies([1, 4, 5]);
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([1, 4, 5]);
    expect(user.activeCompany.id).toBe(1);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(3);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(2);

    await contains(".log_into:eq(0)").click();
    expect(cookie.get("cids")).toEqual("3");
});

test("single company mode: from leaf (only one company in branch selected) loginto company", async () => {
    patchUserActiveCompanies([1]);
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    expect(user.activeCompany.id).toBe(1);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(4);

    await contains(".log_into:eq(1)").click();
    expect(cookie.get("cids")).toEqual("2");
});

test("multi company mode: switching company doesn't deselect already selected ones", async () => {
    patchUserActiveCompanies([1, 2, 4, 5]);
    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([1, 2, 4, 5]);
    expect(user.activeCompany.id).toBe(1);
    await contains(".dropdown-toggle").click();
    expect("[data-company-id]").toHaveCount(5);
    expect("[data-company-id] .fa-square-check").toHaveCount(4);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(1);

    await contains(".log_into:eq(1)").click();
    expect(cookie.get("cids")).toEqual("2-1-4-5");
});

test("show confirm and reset buttons only when selection has changed", async () => {
    await createSwitchCompanyMenu();
    await openCompanyMenu();

    expect(".o_switch_company_menu_buttons").toHaveCount(0);

    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons button").toHaveCount(2);

    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons").toHaveCount(0);
});

test("the search row is on screen in any multi-company environment", async () => {
    await createSwitchCompanyMenu();

    await openCompanyMenu();
    expect(".o-dropdown--menu [role=searchbox]").toHaveCount(1);
    expect(
        ".o-dropdown--menu div:has(> [role=search]) [role=menuitemcheckbox]",
    ).toHaveCount(1);
    expect(".o-dropdown--menu .visually-hidden").toHaveCount(0);
    // `visually-hidden` collapses the row to 1x1: assert it really takes room
    expect(
        queryRect(".o-dropdown--menu div:has(> [role=search])").height,
    ).toBeGreaterThan(1);
});

test("the search input filters items, ignoring case and spaces", async () => {
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Herman's", sequence: 2, parent_id: false, child_ids: [] },
        { id: 1, name: "Heroes TM", sequence: 3, parent_id: false, child_ids: [4, 5] },
        { id: 4, name: "Hercules", sequence: 4, parent_id: 1, child_ids: [] },
        { id: 5, name: "Hulk", sequence: 5, parent_id: 1, child_ids: [] },
        {
            id: 6,
            name: "Random Company a",
            sequence: 6,
            parent_id: false,
            child_ids: [7, 8],
        },
        { id: 7, name: "Random Company aa", sequence: 7, parent_id: 6, child_ids: [] },
        { id: 8, name: "Random Company ab", sequence: 8, parent_id: 6, child_ids: [] },
        { id: 9, name: "Random d", sequence: 9, parent_id: false, child_ids: [] },
        { id: 10, name: "Random e", sequence: 10, parent_id: false, child_ids: [] },
    ];

    await createSwitchCompanyMenu();

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

test.tags("focus required");
test("navigation with search input", async () => {
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Herman's", sequence: 2, parent_id: false, child_ids: [] },
        { id: 1, name: "Heroes TM", sequence: 3, parent_id: false, child_ids: [4, 5] },
        { id: 4, name: "Hercules", sequence: 4, parent_id: 1, child_ids: [] },
        { id: 5, name: "Hulk", sequence: 5, parent_id: 1, child_ids: [] },
        {
            id: 6,
            name: "Random Company a",
            sequence: 6,
            parent_id: false,
            child_ids: [7, 8],
        },
        { id: 7, name: "Random Company aa", sequence: 7, parent_id: 6, child_ids: [] },
        { id: 8, name: "Random Company ab", sequence: 8, parent_id: 6, child_ids: [] },
        { id: 9, name: "Random d", sequence: 9, parent_id: false, child_ids: [] },
        { id: 10, name: "Random e", sequence: 10, parent_id: false, child_ids: [] },
    ];

    await createSwitchCompanyMenu();
    await openCompanyMenu();

    expect(".o-dropdown--menu input").toBeFocused();
    expect(".o_switch_company_item.focus").toHaveCount(0);

    const navigationSteps = [
        { hotkey: "arrowdown", focused: 1, selectedCompanies: [3] },
        { hotkey: "arrowup", focused: 0 },
        { hotkey: "arrowup", focused: 10 },
        { hotkey: "Space", focused: 10, selectedCompanies: [3, 10] },
        { hotkey: ["shift", "tab"], focused: 9, selectedCompanies: [3, 10] },
        { hotkey: "tab", focused: 10, selectedCompanies: [3, 10] },
        { hotkey: "arrowdown", focused: 11 },
        { hotkey: "arrowdown", focused: 12 },
        { hotkey: "enter", focused: 10, selectedCompanies: [3] },
        { hotkey: "arrowdown", focused: 0 },
        { input: "a", focused: 0 },
        { hotkey: "arrowdown", focused: 1 },
        { hotkey: "Space", focused: 1, selectedCompanies: [2] },
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

        await animationFrame();
        await runAllTimers();

        expect(`.o_popover .o-navigable:eq(${focused})`).toHaveClass("focus");
        expect(`.o_popover .o-navigable:eq(${focused})`).toBeFocused();

        if (selectedCompanies) {
            expect(
                queryAllAttributes(
                    ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
                    "data-company-id",
                ).map(Number),
            ).toEqual(selectedCompanies);
        }
    }

    await keyDown(["control", "enter"]);
    await animationFrame();

    expect(cookie.get("cids")).toEqual("3-2");
    expect(".o_switch_company_item").toHaveCount(0);
    expect.verifySteps(navigationSteps);
});

test("select and de-select all", async () => {
    await createSwitchCompanyMenu();
    await openCompanyMenu();

    expect("[role=menuitemcheckbox][title='Deselect all'] i").toHaveClass(
        "fa-square-minus",
    );

    await contains("[role=menuitemcheckbox][title='Deselect all']").click();
    expect("[role=menuitemcheckbox][title='Select all'] i").toHaveClass("fa-square");
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(0);

    await contains("[role=menuitemcheckbox][title='Select all']").click();
    expect("[role=menuitemcheckbox][title='Deselect all'] i").toHaveClass(
        "fa-square-check",
    );
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(5);

    await contains("[role=menuitemcheckbox][title='Deselect all']").click();
    expect("[role=menuitemcheckbox][title='Select all'] i").toHaveClass("fa-square");
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(0);
});

test("de-select only changes visible companies", async () => {
    await createSwitchCompanyMenu();
    await openCompanyMenu();

    await edit(" ");
    await toggleCompany(4);
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(2);

    await contains("input").edit("herm");
    await animationFrame();
    expect(".o_switch_company_item").toHaveCount(2);

    await contains("[role=menuitemcheckbox][title='Deselect all']").click();
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(0);

    await contains("input").clear();
    await animationFrame();
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(1);

    await contains("input").edit("herm");
    await animationFrame();
    await contains("[role=menuitemcheckbox][title='Select all']").click();
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(2);

    await contains("input").clear();
    await animationFrame();
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(3);
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=false])",
    ).toHaveCount(2);
});

test("select all takes exactly the branches the filter shows", async () => {
    await createSwitchCompanyMenu();
    await openCompanyMenu();

    await edit(" ");
    await animationFrame();
    await contains("input").edit("Heroes");
    await animationFrame();
    expect(queryAllTexts(".company_label")).toEqual(["Heroes TM", "Hercules", "Hulk"]);

    await contains("[role=menuitemcheckbox][title='Select all']").click();

    await contains("input").clear();
    await animationFrame();
    expect(
        queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked"),
    ).toEqual(["true", "false", "true", "true", "true"]);
});

test("closing the dropdown without confirming discards the pending selection", async () => {
    await createSwitchCompanyMenu();

    patchWithCleanup(router, {
        pushState: () => expect.step("pushState"),
    });

    await openCompanyMenu();
    await toggleCompany(1);
    expect(".o_switch_company_menu_buttons button").toHaveCount(2);

    await contains(".dropdown-toggle").click();
    expect(".dropdown-menu").toHaveCount(0);

    await keyDown(["control", "enter"]);
    await animationFrame();
    await runAllTimers();

    expect.verifySteps([]);
    expect(cookie.get("cids")).toBe("3");
    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
});

test("reopening the dropdown after closing shows the active companies", async () => {
    await createSwitchCompanyMenu();

    await openCompanyMenu();
    await toggleCompany(1);
    expect("[data-company-id] .fa-square-check").toHaveCount(2);

    await contains(".dropdown-toggle").click();
    expect(".dropdown-menu").toHaveCount(0);
    await openCompanyMenu();

    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect(
        queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked"),
    ).toEqual(["true", "false", "false", "false", "false"]);
    expect(".o_switch_company_menu_buttons").toHaveCount(0);
});

test("select all does not select disallowed ancestor companies", async () => {
    cookie.set("cids", "1-3");
    serverState.companies = [
        { id: 1, name: "Parent", sequence: 1, parent_id: false, child_ids: [2] },
        { id: 2, name: "Child A", sequence: 2, parent_id: 1, child_ids: [3] },
        { id: 3, name: "Child B", sequence: 3, parent_id: 2, child_ids: [] },
    ];

    patchWithCleanup(user.allowedCompanies, [
        serverState.companies[0],
        serverState.companies[2],
    ]);

    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([1, 3]);
    await openCompanyMenu();

    await edit(" ");
    await animationFrame();

    await contains("[role=menuitemcheckbox][title='Deselect all']").click();
    expect(
        ".o_switch_company_item:has([role=menuitemcheckbox][aria-checked=true])",
    ).toHaveCount(0);

    await contains("[role=menuitemcheckbox][title='Select all']").click();
    expect(
        queryAllAttributes("[data-company-id] [role=menuitemcheckbox]", "aria-checked"),
    ).toEqual(["true", "false", "true"]);
    expect(".o_switch_company_menu_buttons").toHaveCount(0);
});

test("disallowed companies in between allowed companies are not enabled", async () => {
    cookie.set("cids", "3");
    serverState.companies = [
        { id: 1, name: "Parent", sequence: 1, parent_id: false, child_ids: [2] },
        { id: 2, name: "Child A", sequence: 2, parent_id: 1, child_ids: [3] },
        { id: 3, name: "Child B", sequence: 3, parent_id: 2, child_ids: [] },
    ];

    patchWithCleanup(user.allowedCompanies, [
        serverState.companies[0],
        serverState.companies[2],
    ]);

    await createSwitchCompanyMenu();

    expect(user.activeCompanies.map((c) => c.id)).toEqual([3]);
    expect(user.activeCompany.id).toBe(3);
    await openCompanyMenu();
    expect("[data-company-id]").toHaveCount(3);
    expect("[data-company-id] .fa-square-check").toHaveCount(1);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(2);

    await contains(".log_into:eq(0)").click();
    expect(cookie.get("cids")).toEqual("1-3");

    await openCompanyMenu();
    await toggleCompany(0);
    expect("[data-company-id] .fa-square-check").toHaveCount(0);
    expect("[data-company-id] .fa-regular.fa-square").toHaveCount(3);
});

test("switching company probes record access under the new companies before mutating the cookie", async () => {
    const controller = { props: { resId: 1, resModel: "res.partner" } };
    const actionService = { currentController: controller };

    const calls = [];
    patchWithCleanup(user, {
        checkAccessRight(model, operation, ids, options) {
            calls.push({
                model,
                operation,
                ids,
                allowedCompanyIds: options?.context?.allowed_company_ids,
                cidsAtCallTime: cookie.get("cids"),
            });
            return Promise.resolve(true);
        },
    });

    const selector = new SwitchCompanyMenu.CompanySelector(actionService, {
        close: () => {},
    });
    selector.selectedCompaniesIds = [2];

    expect(cookie.get("cids")).toBe("3");
    await selector.apply();

    expect(calls).toHaveLength(1);
    expect(calls[0].model).toBe("res.partner");
    expect(calls[0].operation).toBe("read");
    expect(calls[0].ids).toBe(1);
    expect(calls[0].allowedCompanyIds).toEqual([2]);
    expect(calls[0].cidsAtCallTime).toBe("3");
    expect(cookie.get("cids")).toBe("2");
});

test("switching company drops the current record when it is inaccessible under the new companies", async () => {
    const controller = { props: { resId: 1, resModel: "res.partner" } };
    const actionService = { currentController: controller };

    patchWithCleanup(user, {
        checkAccessRight: () => Promise.resolve(false),
    });

    const pushes = [];
    patchWithCleanup(router, {
        pushState(state, options) {
            pushes.push({ state, options });
            return super.pushState(state, options);
        },
    });

    const selector = new SwitchCompanyMenu.CompanySelector(actionService, {
        close: () => {},
    });
    selector.selectedCompaniesIds = [2];
    await selector.apply();

    expect(pushes).toHaveLength(1);
    expect(pushes[0].options.replace).toBe(true);
    expect(pushes[0].options.reload).toBe(true);
    expect(pushes[0].state.actionStack).toBeInstanceOf(Array);
    expect(cookie.get("cids")).toBe("2");
});

test("switching company keeps an accessible record and does not touch the action stack", async () => {
    const controller = { props: { resId: 1, resModel: "res.partner" } };
    const actionService = { currentController: controller };

    patchWithCleanup(user, {
        checkAccessRight: () => Promise.resolve(true),
    });

    const pushes = [];
    patchWithCleanup(router, {
        pushState(state, options) {
            pushes.push({ state, options });
            return super.pushState(state, options);
        },
    });

    const selector = new SwitchCompanyMenu.CompanySelector(actionService, {
        close: () => {},
    });
    selector.selectedCompaniesIds = [2];
    await selector.apply();

    expect(pushes).toHaveLength(1);
    expect(pushes[0].options.reload).toBe(true);
    expect(pushes[0].options.replace).toBe(undefined);
    expect(pushes[0].state.actionStack).toBe(undefined);
    expect(cookie.get("cids")).toBe("2");
});

test("switching company with no record open performs no access probe", async () => {
    const actionService = { currentController: null };

    let probed = false;
    patchWithCleanup(user, {
        checkAccessRight() {
            probed = true;
            return Promise.resolve(true);
        },
    });

    const selector = new SwitchCompanyMenu.CompanySelector(actionService, {
        close: () => {},
    });
    selector.selectedCompaniesIds = [2];
    await selector.apply();

    expect(probed).toBe(false);
    expect(cookie.get("cids")).toBe("2");
});

test("a matching branch is shown under its parent, never on its own", async () => {
    await createSwitchCompanyMenu();
    await openCompanyMenu();

    await edit(" ");
    await animationFrame();
    await contains("input").edit("Hercules");
    await animationFrame();

    expect(queryAllTexts(".company_label")).toEqual(["Heroes TM", "Hercules", "Hulk"]);
});

test("a search matching nothing shows nothing", async () => {
    await createSwitchCompanyMenu();
    await openCompanyMenu();

    await edit(" ");
    await animationFrame();
    await contains("input").edit("Vandelay");
    await animationFrame();

    expect(queryAllTexts(".company_label")).toEqual([]);
});

describe("disallowed ancestors", () => {
    beforeEach(() => {
        cookie.set("cids", "10");
        after(() => cookie.set("cids", "3"));
        serverState.companies = [
            { id: 10, name: "Alpha", sequence: 2, parent_id: 99, child_ids: [12] },
            { id: 11, name: "Beta", sequence: 3, parent_id: 99, child_ids: [] },
            { id: 12, name: "Gamma", sequence: 4, parent_id: 10, child_ids: [] },
        ];
        serverState.disallowedAncestorCompanies = [
            {
                id: 99,
                name: "Root",
                sequence: 1,
                parent_id: false,
                child_ids: [10, 11],
            },
        ];
    });

    test("the disallowed ancestor is rendered but not selectable", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();

        expect(queryAllTexts(".company_label")).toEqual([
            "Root",
            "Alpha",
            "Gamma",
            "Beta",
        ]);
        expect(
            queryAllAttributes(".o_switch_company_item", "class").map((c) =>
                c.includes("disabled"),
            ),
        ).toEqual([true, false, false, false]);
    });

    test("clicking the disallowed ancestor's checkbox is a no-op", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();
        expect(cookie.get("cids")).toBe("10");

        await toggleCompany(0);

        expect(".o_switch_company_menu_buttons").toHaveCount(0);
        expect(
            queryAllAttributes(
                ".o_switch_company_item [role=menuitemcheckbox]",
                "aria-checked",
            ),
        ).toEqual(["false", "true", "false", "false"]);
        expect(cookie.get("cids")).toBe("10");
    });

    test("selecting an allowed parent cascades to its children only", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();

        await toggleCompany(1);
        await toggleCompany(1);
        await clickConfirm();

        expect(cookie.get("cids")).toBe("10-12");
    });

    test("select-all skips the disallowed ancestor", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();

        await edit(" ");
        await animationFrame();

        await contains("[role=menuitemcheckbox][title='Deselect all']").click();
        await contains("[role=menuitemcheckbox][title='Select all']").click();
        await clickConfirm();

        const cids = cookie.get("cids").split("-").map(Number);
        expect(cids).not.toInclude(99);
        expect(cids.toSorted((a, b) => a - b)).toEqual([10, 11, 12]);
    });

    test("select-all reads as fully checked once every selectable company is on", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();

        await edit(" ");
        await animationFrame();

        await contains("[role=menuitemcheckbox][title='Deselect all']").click();
        await contains("[role=menuitemcheckbox][title='Select all']").click();

        expect(
            "[role=menuitemcheckbox][title='Deselect all'] .fa-square-check",
        ).toHaveCount(1);
        expect(
            "[role=menuitemcheckbox][title='Deselect all'] .fa-square-minus",
        ).toHaveCount(0);
    });
});

describe("two disallowed ancestors, as the server really serves them", () => {
    beforeEach(() => {
        cookie.set("cids", "8");
        after(() => cookie.set("cids", "3"));
        serverState.companies = [
            { id: 8, name: "A", sequence: 1, parent_id: false, child_ids: [] },
            { id: 10, name: "B Branch", sequence: 3, parent_id: 9, child_ids: [] },
            { id: 11, name: "C", sequence: 4, parent_id: false, child_ids: [12] },
            {
                id: 13,
                name: "C Branch Branch",
                sequence: 6,
                parent_id: 12,
                child_ids: [],
            },
        ];
        serverState.disallowedAncestorCompanies = [
            { id: 9, name: "B", sequence: 2, parent_id: false, child_ids: [10] },
            { id: 12, name: "C Branch", sequence: 5, parent_id: 11, child_ids: [13] },
        ];
    });

    test("the two ancestors render disabled and never become selected", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();

        expect(queryAllTexts(".company_label")).toEqual([
            "A",
            "B",
            "B Branch",
            "C",
            "C Branch",
            "C Branch Branch",
        ]);
        expect(
            queryAllAttributes(".o_switch_company_item", "class").map((c) =>
                c.includes("disabled"),
            ),
        ).toEqual([false, true, false, false, true, false]);

        await edit(" ");
        await animationFrame();
        await contains("[role=menuitemcheckbox][title='Deselect all']").click();
        await contains("[role=menuitemcheckbox][title='Select all']").click();

        expect(
            queryAllAttributes(
                ".o_switch_company_item [role=menuitemcheckbox]",
                "aria-checked",
            ),
        ).toEqual(["true", "false", "true", "true", "false", "true"]);
    });

    test("select-all reads fully checked with two ancestors present", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();

        await edit(" ");
        await animationFrame();
        await contains("[role=menuitemcheckbox][title='Deselect all']").click();
        await contains("[role=menuitemcheckbox][title='Select all']").click();

        expect(
            "[role=menuitemcheckbox][title='Deselect all'] .fa-square-check",
        ).toHaveCount(1);
    });
});

describe("company index (first set)", () => {
    beforeEach(() => {
        cookie.set("cids", "3");
        after(() => cookie.set("cids", "3"));
        serverState.companies = [
            { id: 3, name: "Hermit", sequence: 1, parent_id: false, child_ids: [] },
            { id: 4, name: "Kramerica", sequence: 2, parent_id: false, child_ids: [] },
        ];
    });

    test("renders its own companies and populates the index", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();
        expect(queryAllTexts(".company_label")).toEqual(["Hermit", "Kramerica"]);
    });
});

describe("company index (disjoint second set)", () => {
    beforeEach(() => {
        cookie.set("cids", "7");
        after(() => cookie.set("cids", "3"));
        serverState.companies = [
            { id: 7, name: "Vandelay", sequence: 1, parent_id: false, child_ids: [8] },
            { id: 8, name: "Industries", sequence: 2, parent_id: 7, child_ids: [] },
        ];
    });

    test("resolves ids the previous set never had", async () => {
        await createSwitchCompanyMenu();
        await openCompanyMenu();
        expect(queryAllTexts(".company_label")).toEqual(["Vandelay", "Industries"]);
    });
});
