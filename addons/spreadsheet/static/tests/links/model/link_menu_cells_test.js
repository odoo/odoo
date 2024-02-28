/** @odoo-module */
import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";
import { ormService } from "@web/core/orm_service";
import { viewService } from "@web/views/view_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCell } from "@spreadsheet/../tests/utils/getters";
import { getMenuServerData } from "../menu_data_utils";

const { Model } = spreadsheet;

function beforeEach() {
    registry
        .category("services")
        .add("menu", menuService)
        .add("action", actionService)
        .add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
    registry.category("services").add("view", viewService, { force: true }); // #action-serv-leg-compat-js-class
    registry.category("services").add("orm", ormService, { force: true }); // #action-serv-leg-compat-js-class
}

QUnit.module("spreadsheet > menu link cells", { beforeEach }, () => {
    QUnit.test("ir.menu linked based on xml id", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { evalContext: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/test_menu)");
        const cell = getCell(model, "A1");
        assert.equal(cell.evaluated.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_xml_id/test_menu)",
            "The content should be the complete markdown link"
        );
        assert.equal(cell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            cell.link.url,
            "odoo://ir_menu_xml_id/test_menu",
            "The link url should reference the correct menu"
        );
    });

    QUnit.test("ir.menu linked based on record id", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { evalContext: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_id/2)");
        const cell = getCell(model, "A1");
        assert.equal(cell.evaluated.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_id/2)",
            "The content should be the complete markdown link"
        );
        assert.equal(cell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            cell.link.url,
            "odoo://ir_menu_id/2",
            "The link url should reference the correct menu"
        );
    });

    QUnit.test("ir.menu linked based on xml id which does not exists", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { evalContext: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_xml_id/does_not_exists)");
        const cell = getCell(model, "A1");
        assert.equal(cell.content, "[label](odoo://ir_menu_xml_id/does_not_exists)");
        assert.equal(cell.evaluated.value, "#BAD_EXPR");
    });

    QUnit.test("ir.menu linked based on record id which does not exists", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { evalContext: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_id/9999)");
        const cell = getCell(model, "A1");
        assert.equal(cell.content, "[label](odoo://ir_menu_id/9999)");
        assert.equal(cell.evaluated.value, "#BAD_EXPR");
    });

    QUnit.test("Odoo link cells can be imported/exported", async function (assert) {
        const env = await makeTestEnv({ serverData: getMenuServerData() });
        const model = new Model({}, { evalContext: { env } });
        setCellContent(model, "A1", "[label](odoo://ir_menu_id/2)");
        let cell = getCell(model, "A1");
        assert.equal(cell.evaluated.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_id/2)",
            "The content should be the complete markdown link"
        );
        assert.equal(cell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            cell.link.url,
            "odoo://ir_menu_id/2",
            "The link url should reference the correct menu"
        );
        const model2 = new Model(model.exportData(), { evalContext: { env } });
        cell = getCell(model2, "A1");
        assert.equal(cell.evaluated.value, "label", "The value should be the menu name");
        assert.equal(
            cell.content,
            "[label](odoo://ir_menu_id/2)",
            "The content should be the complete markdown link"
        );
        assert.equal(cell.link.label, "label", "The link label should be the menu name");
        assert.equal(
            cell.link.url,
            "odoo://ir_menu_id/2",
            "The link url should reference the correct menu"
        );
    });
});
