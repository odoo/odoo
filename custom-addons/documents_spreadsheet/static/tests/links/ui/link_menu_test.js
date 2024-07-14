/** @odoo-module */

import { registries, components } from "@odoo/o-spreadsheet";

import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";
import { registry } from "@web/core/registry";
import { createSpreadsheet } from "../../spreadsheet_test_utils";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { getCell } from "@spreadsheet/../tests/utils/getters";
import { setCellContent, setSelection } from "@spreadsheet/../tests/utils/commands";
import { getMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";

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
    await nextTick();
    await click(target, ".o-special-link");
    await click(target, ".o-menu-item[data-name='odooMenu']");
    return { webClient, env, model };
}

function beforeEach() {
    target = getFixture();
    registry.category("services").add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
    patchWithCleanup(Grid.prototype, {
        setup() {
            super.setup();
            this.hoveredCell = { col: 0, row: 0 };
        },
    });
}

QUnit.module("spreadsheet > menu link ui", { beforeEach }, () => {
    QUnit.test("insert a new ir menu link", async function (assert) {
        const { model } = await openMenuSelector();
        await click(target, ".o-ir-menu-selector input");
        assert.ok(target.querySelector("button.o-confirm").disabled);
        await click(document.querySelectorAll(".ui-menu-item")[0]);
        await click(document, "button.o-confirm");
        assert.equal(labelInput().value, "menu with xmlid", "The label should be the menu name");
        assert.equal(
            urlInput().value,
            "menu with xmlid",
            "The url displayed should be the menu name"
        );
        assert.ok(urlInput().disabled, "The url input should be disabled");
        await click(target, "button.o-save");
        const cell = getCell(model, "A1");
        assert.equal(
            cell.content,
            "[menu with xmlid](odoo://ir_menu_xml_id/test_menu)",
            "The content should be the complete markdown link"
        );
        assert.equal(
            target.querySelector(".o-link-tool a").text,
            "menu with xmlid",
            "The link tooltip should display the menu name"
        );
    });

    QUnit.test("update selected ir menu", async function (assert) {
        await openMenuSelector();
        await click(target, ".o-ir-menu-selector input");
        assert.ok(target.querySelector("button.o-confirm").disabled);
        const item1 = document.querySelectorAll(".ui-menu-item")[1];
        triggerEvent(item1, null, "mouseenter");
        await click(item1);
        assert.equal(
            target.querySelector(".o-ir-menu-selector input").value,
            "App_1/menu without xmlid",
            "The menu displayed should be the menu name"
        );
        await click(target, ".o-ir-menu-selector input");
        const item2 = document.querySelectorAll(".ui-menu-item")[0];
        triggerEvent(item2, null, "mouseenter");
        await click(item2);
        assert.equal(
            target.querySelector(".o-ir-menu-selector input").value,
            "App_1/menu with xmlid",
            "The menu displayed should be the menu name"
        );
    });

    QUnit.test("fetch available menus", async function (assert) {
        const { env } = await openMenuSelector({
            mockRPC: function (route, args) {
                if (args.method === "name_search" && args.model === "ir.ui.menu") {
                    assert.step("fetch_menus");
                    assert.deepEqual(
                        args.kwargs.args,
                        [
                            "|",
                            ["id", "in", [1]],
                            "&",
                            ["action", "!=", false],
                            ["id", "in", [1, 11, 12]],
                        ],
                        "user defined groupby should have precedence on action groupby"
                    );
                }
            },
        });
        assert.deepEqual(
            env.services.menu.getAll().map((menu) => menu.id),
            [1, 11, 12, "root"]
        );
        await click(target, ".o-ir-menu-selector input");
        assert.verifySteps(["fetch_menus"]);
    });

    QUnit.test(
        "insert a new ir menu link when the menu does not have an xml id",
        async function (assert) {
            const { model } = await openMenuSelector();
            await click(target, ".o-ir-menu-selector input");
            assert.ok(target.querySelector("button.o-confirm").disabled);
            const item = document.querySelectorAll(".ui-menu-item")[1];
            triggerEvent(item, null, "mouseenter");
            await click(item);
            await click(target, "button.o-confirm");
            assert.equal(
                labelInput().value,
                "menu without xmlid",
                "The label should be the menu name"
            );
            assert.equal(
                urlInput().value,
                "menu without xmlid",
                "The url displayed should be the menu name"
            );
            assert.ok(urlInput().disabled, "The url input should be disabled");
            await click(target, "button.o-save");
            const cell = getCell(model, "A1");
            assert.equal(
                cell.content,
                "[menu without xmlid](odoo://ir_menu_id/12)",
                "The content should be the complete markdown link"
            );
            assert.equal(
                target.querySelector(".o-link-tool a").text,
                "menu without xmlid",
                "The link tooltip should display the menu name"
            );
        }
    );

    QUnit.test("cancel ir.menu selection", async function (assert) {
        await openMenuSelector();
        await click(target, ".o-ir-menu-selector input");
        await click(document.querySelectorAll(".ui-menu-item")[0]);
        assert.containsOnce(target, ".o-ir-menu-selector");
        await click(target, ".modal-footer button.o-cancel");
        assert.containsNone(target, ".o-ir-menu-selector");
        assert.equal(labelInput().value, "", "The label should be empty");
        assert.equal(urlInput().value, "", "The url displayed should be the menu name");
    });

    QUnit.test("menu many2one field input is focused", async function (assert) {
        await openMenuSelector(this.serverData);
        assert.equal(
            document.activeElement,
            target.querySelector(".o-ir-menu-selector input"),
            "the input should be focused"
        );
    });

    QUnit.test("ir.menu link keep breadcrumb", async function (assert) {
        const { model } = await createSpreadsheet({
            serverData: getMenuServerData(),
        });
        setCellContent(model, "A1", "[menu with xmlid](odoo://ir_menu_xml_id/test_menu)");
        setSelection(model, "A1");
        await nextTick();
        const link = document.querySelector("a.o-link");
        await click(link);
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Untitled spreadsheetaction1"
        );
    });
});
