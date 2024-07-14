/** @odoo-module */

import {
  invokeInsertListInSpreadsheetDialog,
  spawnListViewForSpreadsheet,
  toggleCogMenuSpreadsheet,
} from "../utils/list_helpers";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { toggleActionMenu } from "@web/../tests/search/helpers";
import { getSpreadsheetActionModel } from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";

let target;
QUnit.module(
    "documents_spreadsheet > insert_list_spreadsheet_menu",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("Can save a list in a new spreadsheet", async (assert) => {
            assert.expect(4);

            await spawnListViewForSpreadsheet({
                mockRPC: async function (route, args) {
                    if (
                        args.method === "action_open_new_spreadsheet" &&
                        args.model === "documents.document"
                    ) {
                        assert.step("action_open_new_spreadsheet");
                    }
                },
            });
            await nextTick();
            await toggleActionMenu(target);
            await toggleCogMenuSpreadsheet(target);
            await click(target.querySelector(".o_insert_list_spreadsheet_menu"));
            await click(target, ".modal button.btn-primary");
            await nextTick();
            assert.verifySteps(["action_open_new_spreadsheet"]);
        });

        QUnit.test("Can save a list in existing spreadsheet", async (assert) => {
            assert.expect(5);

            await spawnListViewForSpreadsheet({
                mockRPC: async function (route, args) {
                    if (args.model === "documents.document") {
                        /** These two methods are used for the PivotSelectorDialog */
                        if (args.method !== "search_count" && args.method !== "get_views") {
                            assert.step(args.method);
                            switch (args.method) {
                                case "get_spreadsheets_to_display":
                                    return [{ id: 1, name: "My Spreadsheet" }];
                            }
                        }
                    }
                },
            });

            await toggleActionMenu(target);
            await toggleCogMenuSpreadsheet(target);
            await click(target.querySelector(".o_insert_list_spreadsheet_menu"));
            await triggerEvent(target, ".o-sp-dialog-item div[data-id='1']", "focus");
            await click(target, ".modal button.btn-primary");
            await nextTick();

            assert.verifySteps(
                ["get_spreadsheets_to_display", "join_spreadsheet_session"],
                "get spreadsheet, then join"
            );
        });

        QUnit.test("List name can be changed from the dialog", async (assert) => {
            const { env } = await spawnListViewForSpreadsheet();

            let spreadsheetAction;
            patchWithCleanup(SpreadsheetAction.prototype, {
                setup() {
                    super.setup();
                    spreadsheetAction = this;
                },
            });
            await invokeInsertListInSpreadsheetDialog(env);
            /** @type {HTMLInputElement} */
            const name = target.querySelector(".o_spreadsheet_name");
            name.value = "New name";
            await triggerEvent(name, null, "input");
            await click(target, ".modal button.btn-primary");
            const model = getSpreadsheetActionModel(spreadsheetAction);
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(model.getters.getListName("1"), "New name");
            assert.strictEqual(model.getters.getListDisplayName("1"), "(#1) New name");
        });

        QUnit.test("Unsorted List name doesn't contains sorting info", async function (assert) {
            const { env } = await spawnListViewForSpreadsheet();

            await invokeInsertListInSpreadsheetDialog(env);
            assert.strictEqual(target.querySelector(".o_spreadsheet_name").value, "Partners");
        });

        QUnit.test("Sorted List name contains sorting info", async function (assert) {
            const { env } = await spawnListViewForSpreadsheet({
                orderBy: [{ name: "bar", asc: true }],
            });

            await invokeInsertListInSpreadsheetDialog(env);
            assert.strictEqual(
                target.querySelector(".o_spreadsheet_name").value,
                "Partners by Bar"
            );
        });

        QUnit.test("List name is not changed if the name is empty", async (assert) => {
            const { env } = await spawnListViewForSpreadsheet();

            let spreadsheetAction;
            patchWithCleanup(SpreadsheetAction.prototype, {
                setup() {
                    super.setup();
                    spreadsheetAction = this;
                },
            });
            await invokeInsertListInSpreadsheetDialog(env);
            target.querySelector(".o_spreadsheet_name").value = "";
            await click(target, ".modal button.btn-primary");
            const model = getSpreadsheetActionModel(spreadsheetAction);
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(model.getters.getListName("1"), "Partners");
        });

        QUnit.test(
            "Grouped list: we take the number of elements not the number of groups",
            async function (assert) {
                const serverData = getBasicServerData();
                const { env } = await spawnListViewForSpreadsheet({
                    serverData,
                    groupBy: ["product_id"],
                    red_model: "partner",
                });

                await invokeInsertListInSpreadsheetDialog(env);
                assert.equal(
                    target.querySelector("input#threshold").value,
                    String(serverData.models.partner.records.length)
                );
            }
        );
    }
);
