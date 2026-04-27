import {
    defineDocumentSpreadsheetModels,
    getBasicData,
    getBasicServerData,
    getMySpreadsheetPermissionPanelData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Model } from "@odoo/o-spreadsheet";
import { contains, getService, MockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

let target;

beforeEach(() => {
    target = getFixture();
});

test("spreadsheet with generic untitled name is styled", async function () {
    await createSpreadsheet();
    const input = target.querySelector(".o_sp_name input");
    expect(input).toHaveClass("o-sp-untitled", {
        message: "It should be styled as untitled",
    });
    await contains(input).edit("My");
    expect(input).not.toHaveClass("o-sp-untitled", {
        message: "It should not be styled as untitled",
    });
    await contains(input).edit("Untitled spreadsheet");
    expect(input).toHaveClass("o-sp-untitled", {
        message: "It should be styled as untitled",
    });
    await contains(input).edit("");
    expect(input).toHaveClass("o-sp-untitled", {
        message: "It should be styled as untitled",
    });
});

test("spreadsheet name can never be empty (white spaces)", async function () {
    await createSpreadsheet();
    const input = target.querySelector(".o_sp_name input");
    expect(input).toHaveValue("Untitled spreadsheet", {
        message: "The input should have the placeholder value initially",
    });

    await contains(input).edit("     ");
    expect(input).toHaveValue("Untitled spreadsheet", {
        message: "The input should retain the placeholder value when set to empty spaces",
    });

    await contains(input).edit("My spreadsheet");
    expect(input).toHaveValue("My spreadsheet", {
        message: "The input should update to the new value when set to a valid name",
    });

    await contains(input).edit("     ");
    expect(input).toHaveValue("My spreadsheet", {
        message: "The input should retain the new value even when set to empty spaces",
    });
});

test("untitled spreadsheet", async function () {
    await createSpreadsheet({ spreadsheetId: 3 });
    const input = target.querySelector(".o_sp_name input");
    expect(input).toHaveClass("o-sp-untitled", {
        message: "It should be styled as untitled",
    });
    expect(input).toHaveValue("", { message: "It should be empty" });
    expect(input.placeholder).toBe("Untitled spreadsheet", {
        message: "It should display a placeholder",
    });
    await animationFrame();
});

test("input width changes when content changes", async function () {
    await createSpreadsheet();
    const input = target.querySelector(".o_sp_name input");
    const originalWidth = input.offsetWidth;
    await contains(input).edit("My", { confirm: false });
    let width = input.offsetWidth;
    await contains(input).edit("My title", { confirm: false });
    expect(width).toBeLessThan(input.offsetWidth, {
        message: "It should have grown to fit content",
    });
    width = input.offsetWidth;
    await contains(input).edit("");
    expect(originalWidth).toBe(input.offsetWidth, {
        message: "It should have the size of the previous content",
    });
});

test("changing the input saves the name", async function () {
    const serverData = getBasicServerData();
    await createSpreadsheet({ spreadsheetId: 2, serverData });
    await contains(".o_sp_name input").edit("My spreadsheet");
    expect(MockServer.env["documents.document"][1].name).toBe("My spreadsheet", {
        message: "It should have updated the name",
    });
});

test("trailing white spaces are trimmed", async function () {
    await createSpreadsheet();
    const input = target.querySelector(".o_sp_name input");
    const width = input.offsetWidth;
    await contains(input).edit("My spreadsheet  ");
    expect(input).toHaveValue("My spreadsheet", {
        message: "It should not have trailing white spaces",
    });
    expect(width).toBeGreaterThan(input.offsetWidth, {
        message: "It should have resized",
    });
});

test("focus sets the placeholder as value and select it", async function () {
    await createSpreadsheet({ spreadsheetId: 3 });
    const input = target.querySelector(".o_sp_name input");
    expect(input).toHaveValue("", { message: "It should be empty" });
    await contains(input).focus();
    expect(input).toHaveValue("Untitled spreadsheet", {
        message: "Placeholder should have become the input value",
    });
    expect(input.selectionStart).toBe(0, { message: "It should have selected the value" });
    expect(input.selectionEnd).toBe(input.value.length, {
        message: "It should have selected the value",
    });
});

test("Freeze&Share spreadsheet from control panel", async function () {
    const spreadsheetId = 789;
    const frozenSpreadsheetId = 1337;
    const model = new Model();
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        { id: 1, type: "folder" },
        {
            name: "My spreadsheet",
            id: spreadsheetId,
            spreadsheet_data: JSON.stringify(model.exportData()),
            folder_id: 1,
            active: true,
        },
    ];
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenMyspreadsheet");
        },
    });
    await createSpreadsheet({
        serverData,
        spreadsheetId,
        mockRPC: async function (route, args) {
            if (args.method === "action_freeze_and_copy") {
                const excel = JSON.parse(JSON.stringify(model.exportXLSX().files));

                expect(args.args[0]).toEqual(spreadsheetId);
                expect(args.args[1]).toEqual(JSON.stringify(model.exportData()));
                expect(args.args[2]).toEqual(excel);

                expect.step("spreadsheet_shared");
                return { id: frozenSpreadsheetId };
            }
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(frozenSpreadsheetId);
                expect.step("permission_panel_data");
                return getMySpreadsheetPermissionPanelData();
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    expect(target.querySelector(".spreadsheet_share_dropdown")).toBe(null);
    await contains("button:contains(Freeze and share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["spreadsheet_shared", "permission_panel_data", "Document url copied"]);
});

test("Share spreadsheet from control panel", async function () {
    const spreadsheetId = 789;
    const model = new Model();
    const serverData = getBasicServerData();
    serverData.models["documents.document"].records = [
        { id: 1, type: "folder" },
        {
            name: "My spreadsheet",
            id: spreadsheetId,
            spreadsheet_data: JSON.stringify(model.exportData()),
            folder_id: 1,
            active: true,
        },
    ];
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenMyspreadsheet");
        },
    });
    await createSpreadsheet({
        serverData,
        spreadsheetId,
        mockRPC: async function (route, args) {
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(spreadsheetId);
                expect.step("permission_panel_data");
                return getMySpreadsheetPermissionPanelData();
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    expect(target.querySelector(".spreadsheet_share_dropdown")).toBe(null);
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Document url copied"]);
});

test("toggle favorite", async function () {
    await createSpreadsheet({
        spreadsheetId: 2,
        mockRPC: async function (route, args) {
            if (args.method === "toggle_favorited" && args.model === "documents.document") {
                expect.step("favorite_toggled");
                expect(args.args[0]).toEqual([2], {
                    message: "It should write the correct document",
                });
                return true;
            }
        },
    });
    expect(".o-sp-favorite.fa-star").toHaveCount(0);
    await contains(".o-sp-favorite").click();
    expect(".o-sp-favorite.fa-star").toHaveCount(1);
    expect.verifySteps(["favorite_toggled"]);
});

test("already favorited", async function () {
    await createSpreadsheet({ spreadsheetId: 3 });
    expect(".o-sp-favorite.fa-star").toHaveCount(1, {
        message: "It should already be favorited",
    });
});

test("Spreadsheet action is named in breadcrumb", async function () {
    await createSpreadsheetFromPivotView();
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });
    await animationFrame();
    const items = target.querySelectorAll(".breadcrumb-item");
    const [breadcrumb1, breadcrumb2] = Array.from(items).map((item) => item.innerText);
    expect(breadcrumb1).toBe("pivot view");
    expect(breadcrumb2).toBe("Untitled spreadsheet");
    expect(".o_breadcrumb .active").toHaveText("Partner");
});

test("Spreadsheet action is named in breadcrumb with the updated name", async function () {
    await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="bar" type="col"/>
                                <field name="foo" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
            },
        },
    });
    await contains(".o_sp_name input").edit("My awesome spreadsheet");
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });
    await animationFrame();
    const items = target.querySelectorAll(".breadcrumb-item");
    const [breadcrumb1, breadcrumb2] = Array.from(items).map((item) => item.innerText);
    expect(breadcrumb1).toBe("pivot view");
    expect(breadcrumb2).toBe("My awesome spreadsheet");
    expect(".o_breadcrumb .active span").toHaveText("Partner");
});

test("Spreadsheet action is named in breadcrumb with the correct name after go back ", async function () {
    await createSpreadsheetFromPivotView();
    await contains(".o_sp_name input").edit("My awesome spreadsheet");
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "pivot"]],
    });
    await animationFrame();
    const items = target.querySelectorAll(".breadcrumb-item");
    const [breadcrumb1, breadcrumb2] = Array.from(items).map((item) => item.innerText);
    expect(breadcrumb1).toBe("pivot view");
    expect(breadcrumb2).toBe("My awesome spreadsheet");
    expect(".o_breadcrumb .active span").toHaveText("Partner");
    await contains(".breadcrumb-item:last").click();
    expect(".o_sp_name input").toHaveValue("My awesome spreadsheet");
});
