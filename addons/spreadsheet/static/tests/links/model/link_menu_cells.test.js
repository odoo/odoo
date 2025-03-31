import { describe, expect, test } from "@odoo/hoot";
import { Model } from "@odoo/o-spreadsheet";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";

import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getCell, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { getMenuServerData } from "../menu_data_utils";

describe.current.tags("headless");
defineSpreadsheetModels();

test("ir.menu linked based on xml id", async function () {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/test_menu)");
    const cell = getCell(model, "A1");
    const evaluatedCell = getEvaluatedCell(model, "A1");
    expect(evaluatedCell.value).toBe("label", { message: "The value should be the menu name" });
    expect(cell.content).toBe("[label](odoo://ir_menu_xml_id/test_menu)", {
        message: "The content should be the complete markdown link",
    });
    expect(evaluatedCell.link.label).toBe("label", {
        message: "The link label should be the menu name",
    });
    expect(evaluatedCell.link.url).toBe("odoo://ir_menu_xml_id/test_menu", {
        message: "The link url should reference the correct menu",
    });
});

test("ir.menu linked based on record id", async function () {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", "[label](odoo://ir_menu_id/12)");
    const cell = getCell(model, "A1");
    const evaluatedCell = getEvaluatedCell(model, "A1");
    expect(evaluatedCell.value).toBe("label", { message: "The value should be the menu name" });
    expect(cell.content).toBe("[label](odoo://ir_menu_id/12)", {
        message: "The content should be the complete markdown link",
    });
    expect(evaluatedCell.link.label).toBe("label", {
        message: "The link label should be the menu name",
    });
    expect(evaluatedCell.link.url).toBe("odoo://ir_menu_id/12", {
        message: "The link url should reference the correct menu",
    });
});

test("ir.menu linked based on xml id which does not exists", async function () {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/does_not_exists)");
    expect(getCell(model, "A1").content).toBe("[label](odoo://ir_menu_xml_id/does_not_exists)");
    expect(getEvaluatedCell(model, "A1").value).toBe("#LINK");
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "Menu does_not_exists not found. You may not have the required access rights."
    );
});

test("ir.menu linked based on record id which does not exists", async function () {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", "[label](odoo://ir_menu_id/9999)");
    expect(getCell(model, "A1").content).toBe("[label](odoo://ir_menu_id/9999)");
    expect(getEvaluatedCell(model, "A1").value).toBe("#LINK");
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "Menu 9999 not found. You may not have the required access rights."
    );
});

test("Odoo link cells can be imported/exported", async function () {
    const env = await makeSpreadsheetMockEnv({ serverData: getMenuServerData() });
    const model = new Model({}, { custom: { env } });
    setCellContent(model, "A1", "[label](odoo://ir_menu_id/12)");
    let cell = getCell(model, "A1");
    let evaluatedCell = getEvaluatedCell(model, "A1");
    expect(evaluatedCell.value).toBe("label", { message: "The value should be the menu name" });
    expect(cell.content).toBe("[label](odoo://ir_menu_id/12)", {
        message: "The content should be the complete markdown link",
    });
    expect(evaluatedCell.link.label).toBe("label", {
        message: "The link label should be the menu name",
    });
    expect(evaluatedCell.link.url).toBe("odoo://ir_menu_id/12", {
        message: "The link url should reference the correct menu",
    });
    const model2 = new Model(model.exportData(), { custom: { env } });
    cell = getCell(model2, "A1");
    evaluatedCell = getEvaluatedCell(model, "A1");
    expect(evaluatedCell.value).toBe("label", { message: "The value should be the menu name" });
    expect(cell.content).toBe("[label](odoo://ir_menu_id/12)", {
        message: "The content should be the complete markdown link",
    });
    expect(evaluatedCell.link.label).toBe("label", {
        message: "The link label should be the menu name",
    });
    expect(evaluatedCell.link.url).toBe("odoo://ir_menu_id/12", {
        message: "The link url should reference the correct menu",
    });
});
