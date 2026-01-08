/** @odoo-module */
import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import { Model } from "@odoo/o-spreadsheet";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCell, getEvaluatedCell } from "@spreadsheet/../tests/utils/getters";
import { getMenuServerData } from "../menu_data_utils";

function beforeEach() {
    registry
        .category("services")
        .add("menu", menuService)
        .add("action", actionService)
        .add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
}

QUnit.module("spreadsheet > menu link cells", { beforeEach }, () => {
    QUnit.test("ir.menu linked based on xml id", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { custom: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/test_menu)");
        const cell = getCell(model, "A1");
        const evaluatedCell = getEvaluatedCell(model, "A1");
        assert.equal(evaluatedCell.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_xml_id/test_menu)",
            "The content should be the complete markdown link"
        );
        assert.equal(evaluatedCell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            evaluatedCell.link.url,
            "odoo://ir_menu_xml_id/test_menu",
            "The link url should reference the correct menu"
        );
    });

    QUnit.test("ir.menu linked based on record id", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { custom: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_id/12)");
        const cell = getCell(model, "A1");
        const evaluatedCell = getEvaluatedCell(model, "A1");
        assert.equal(evaluatedCell.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_id/12)",
            "The content should be the complete markdown link"
        );
        assert.equal(evaluatedCell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            evaluatedCell.link.url,
            "odoo://ir_menu_id/12",
            "The link url should reference the correct menu"
        );
    });

    QUnit.test("ir.menu linked based on xml id which does not exists", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { custom: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/does_not_exists)");
        assert.equal(
            getCell(model, "A1").content,
            "[label](odoo://ir_menu_xml_id/does_not_exists)"
        );
        assert.equal(getEvaluatedCell(model, "A1").value, "#LINK");
        assert.equal(
            getEvaluatedCell(model, "A1").error.message,
            "Menu does_not_exists not found. You may not have the required access rights."
        );
    });

    QUnit.test("ir.menu linked based on record id which does not exists", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { custom: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_id/9999)");
        assert.equal(getCell(model, "A1").content, "[label](odoo://ir_menu_id/9999)");
        assert.equal(getEvaluatedCell(model, "A1").value, "#LINK");
        assert.equal(
            getEvaluatedCell(model, "A1").error.message,
            "Menu 9999 not found. You may not have the required access rights."
        );
    });

    QUnit.test("Odoo link cells can be imported/exported", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { custom: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_id/12)");
        let cell = getCell(model, "A1");
        let evaluatedCell = getEvaluatedCell(model, "A1");
        assert.equal(evaluatedCell.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_id/12)",
            "The content should be the complete markdown link"
        );
        assert.equal(evaluatedCell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            evaluatedCell.link.url,
            "odoo://ir_menu_id/12",
            "The link url should reference the correct menu"
        );
        const model2 = new Model(model.exportData(), { custom: { env } });
        cell = getCell(model2, "A1");
        evaluatedCell = getEvaluatedCell(model, "A1");
        assert.equal(evaluatedCell.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_id/12)",
            "The content should be the complete markdown link"
        );
        assert.equal(evaluatedCell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            evaluatedCell.link.url,
            "odoo://ir_menu_id/12",
            "The link url should reference the correct menu"
        );
    });
});
