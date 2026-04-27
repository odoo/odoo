import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { components, registries } from "@odoo/o-spreadsheet";
import { setCellContent, setSelection } from "@spreadsheet/../tests/helpers/commands";
import { getCell } from "@spreadsheet/../tests/helpers/getters";
import { getMenuServerData } from "@documents_spreadsheet/../tests/links/menu_data_utils";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineDocumentSpreadsheetModels();

const { cellMenuRegistry } = registries;
const { Grid } = components;

let target;

function labelInput() {
    return target.querySelectorAll(".o-link-editor input")[0];
}

function urlInput() {
    return target.querySelectorAll(".o-link-editor input")[1];
}

/**
 * Create a spreadsheet and open the menu selector to
 * insert a menu link in A1.
 * @param {object} params
 * @param {function} [params.mockRPC]
 */
async function openMenuSelector(params = {}) {
    const { webClient, env, model } = await createSpreadsheet({
        serverData: getMenuServerData(),
        mockRPC: params.mockRPC,
    });
    const insertLinkMenu = cellMenuRegistry.getAll().find((item) => item.id === "insert_link");
    await insertLinkMenu.execute(env);
    await animationFrame();
    await contains(".o-special-link").click();
    await contains(".o-menu-item[data-name='odooMenu']").click();
    return { webClient, env, model };
}

beforeEach(() => {
    target = getFixture();
    patchWithCleanup(Grid.prototype, {
        setup() {
            super.setup();
            this.hoveredCell.hover({ col: 0, row: 0 });
        },
    });
});

test("insert a new ir menu link", async function () {
    const { model } = await openMenuSelector();
    await contains(".o-ir-menu-selector input").click();
    expect("button.o-confirm").toHaveProperty("disabled", true);
    await contains(document.querySelectorAll(".ui-menu-item")[0]).click();
    await contains("button.o-confirm").click();
    expect(labelInput()).toHaveValue("menu with xmlid", {
        message: "The label should be the menu name",
    });
    expect(urlInput()).toHaveValue("menu with xmlid", {
        message: "The url displayed should be the menu name",
    });
    expect(urlInput()).toHaveProperty("disabled", true, {
        message: "The url input should be disabled",
    });
    await contains("button.o-save").click();
    const cell = getCell(model, "A1");
    expect(cell.content).toBe("[menu with xmlid](odoo://ir_menu_xml_id/test_menu)", {
        message: "The content should be the complete markdown link",
    });
    expect(target.querySelector(".o-link-tool a").text).toBe("menu with xmlid", {
        message: "The link tooltip should display the menu name",
    });
});

test("update selected ir menu", async function () {
    await openMenuSelector();
    await contains(".o-ir-menu-selector input").click();
    expect("button.o-confirm").toHaveProperty("disabled", true);
    const item1 = document.querySelectorAll(".ui-menu-item")[1];
    contains(item1).hover();
    await contains(item1).click();
    expect(".o-ir-menu-selector input").toHaveValue("App_1/menu without xmlid", {
        message: "The menu displayed should be the menu name",
    });
    await contains(".o-ir-menu-selector input").click();
    const item2 = document.querySelectorAll(".ui-menu-item")[0];
    contains(item2).hover();
    await contains(item2).click();
    expect(".o-ir-menu-selector input").toHaveValue("App_1/menu with xmlid", {
        message: "The menu displayed should be the menu name",
    });
});

test("fetch available menus", async function () {
    const { env } = await openMenuSelector({
        mockRPC: function (route, args) {
            if (args.method === "name_search" && args.model === "ir.ui.menu") {
                expect.step("fetch_menus");
                expect(args.kwargs.args).toEqual(
                    [
                        "|",
                        ["id", "in", [1]],
                        "&",
                        ["action", "!=", false],
                        ["id", "in", [1, 11, 12]],
                    ],
                    {
                        message: "user defined groupby should have precedence on action groupby",
                    }
                );
            }
        },
    });
    expect(env.services.menu.getAll().map((menu) => menu.id)).toEqual([1, 11, 12, "root"]);
    await contains(".o-ir-menu-selector input").click();
    expect.verifySteps(["fetch_menus"]);
});

test("insert a new ir menu link when the menu does not have an xml id", async function () {
    const { model } = await openMenuSelector();
    await contains(".o-ir-menu-selector input").click();
    expect("button.o-confirm").toHaveProperty("disabled", true);
    const item = document.querySelectorAll(".ui-menu-item")[1];
    contains(item).hover();
    await contains(item).click();
    await contains("button.o-confirm").click();
    expect(labelInput()).toHaveValue("menu without xmlid", {
        message: "The label should be the menu name",
    });
    expect(urlInput()).toHaveValue("menu without xmlid", {
        message: "The url displayed should be the menu name",
    });
    expect(urlInput()).toHaveProperty("disabled", true, {
        message: "The url input should be disabled",
    });
    await contains("button.o-save").click();
    const cell = getCell(model, "A1");
    expect(cell.content).toBe("[menu without xmlid](odoo://ir_menu_id/12)", {
        message: "The content should be the complete markdown link",
    });
    expect(target.querySelector(".o-link-tool a").text).toBe("menu without xmlid", {
        message: "The link tooltip should display the menu name",
    });
});

test("cancel ir.menu selection", async function () {
    await openMenuSelector();
    await contains(".o-ir-menu-selector input").click();
    await contains(document.querySelectorAll(".ui-menu-item")[0]).click();
    expect(".o-ir-menu-selector").toHaveCount(1);
    await contains(".modal-footer button.o-cancel").click();
    expect(".o-ir-menu-selector").toHaveCount(0);
    expect(labelInput()).toHaveValue("", { message: "The label should be empty" });
    expect(urlInput()).toHaveValue("", { message: "The url displayed should be the menu name" });
});

test("menu many2one field input is focused", async function () {
    await openMenuSelector();
    expect(".o-ir-menu-selector input:first").toBeFocused();
});

test("ir.menu link keep breadcrumb", async function () {
    const { model } = await createSpreadsheet({
        serverData: getMenuServerData(),
    });
    setCellContent(model, "A1", "[menu with xmlid](odoo://ir_menu_xml_id/test_menu)");
    setSelection(model, "A1");
    await animationFrame();
    const link = document.querySelector("a.o-link");
    await contains(link).click();
    expect(".o_breadcrumb").toHaveText("Untitled spreadsheet\naction1");
});
