/** @odoo-module */

import { doAction } from "@web/../tests/webclient/helpers";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    makeDeferred,
    editInput,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { x2ManyCommands } from "@web/core/orm_service";
import { browser } from "@web/core/browser/browser";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createSpreadsheetFromPivotView } from "../utils/pivot_helpers";
import { Model } from "@odoo/o-spreadsheet";

let target;

QUnit.module(
    "documents_spreadsheet > Spreadsheet Control Panel",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("spreadsheet with generic untitled name is styled", async function (assert) {
            assert.expect(4);
            await createSpreadsheet();
            const input = target.querySelector(".o_spreadsheet_name input");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
            await editInput(input, null, "My");
            assert.doesNotHaveClass(
                input,
                "o-spreadsheet-untitled",
                "It should not be styled as untitled"
            );
            await editInput(input, null, "Untitled spreadsheet");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
            await editInput(input, null, "");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
        });

        QUnit.test("spreadsheet name can never be empty (white spaces)", async function (assert) {
            await createSpreadsheet();
            const input = target.querySelector(".o_spreadsheet_name input");
            assert.equal(
                input.value,
                "Untitled spreadsheet",
                "The input should have the placeholder value initially"
            );

            await editInput(input, null, "     ");
            await triggerEvent(input, null, "change");
            assert.equal(
                input.value,
                "Untitled spreadsheet",
                "The input should retain the placeholder value when set to empty spaces"
            );

            await editInput(input, null, "My spreadsheet");
            await triggerEvent(input, null, "change");
            assert.equal(
                input.value,
                "My spreadsheet",
                "The input should update to the new value when set to a valid name"
            );

            await editInput(input, null, "     ");
            await triggerEvent(input, null, "change");
            assert.equal(
                input.value,
                "My spreadsheet",
                "The input should retain the new value even when set to empty spaces"
            );
        });

        QUnit.test("untitled spreadsheet", async function (assert) {
            assert.expect(3);
            await createSpreadsheet({ spreadsheetId: 2 });
            const input = target.querySelector(".o_spreadsheet_name input");
            assert.hasClass(input, "o-spreadsheet-untitled", "It should be styled as untitled");
            assert.equal(input.value, "", "It should be empty");
            assert.equal(
                input.placeholder,
                "Untitled spreadsheet",
                "It should display a placeholder"
            );
            await nextTick();
        });

        QUnit.test("input width changes when content changes", async function (assert) {
            assert.expect(2);
            await createSpreadsheet();
            const input = target.querySelector(".o_spreadsheet_name input");
            await editInput(input, null, "My");
            let width = input.offsetWidth;
            await editInput(input, null, "My title");
            assert.ok(width < input.offsetWidth, "It should have grown to fit content");
            width = input.offsetWidth;
            await editInput(input, null, "");
            assert.ok(
                width === input.offsetWidth,
                "It should have the size of the previous content"
            );
        });

        QUnit.test("changing the input saves the name", async function (assert) {
            assert.expect(1);
            const serverData = getBasicServerData();
            await createSpreadsheet({ spreadsheetId: 2, serverData });
            await editInput(target, ".o_spreadsheet_name input", "My spreadsheet");
            assert.equal(
                serverData.models["documents.document"].records[1].name,
                "My spreadsheet",
                "It should have updated the name"
            );
        });

        QUnit.test("trailing white spaces are trimmed", async function (assert) {
            assert.expect(2);
            await createSpreadsheet();
            const input = target.querySelector(".o_spreadsheet_name input");
            const width = input.offsetWidth;
            await editInput(input, null, "My spreadsheet  ");
            assert.equal(input.value, "My spreadsheet", "It should not have trailing white spaces");
            assert.ok(width > input.offsetWidth, "It should have resized");
        });

        QUnit.test("focus sets the placeholder as value and select it", async function (assert) {
            assert.expect(4);
            await createSpreadsheet({ spreadsheetId: 2 });
            const input = target.querySelector(".o_spreadsheet_name input");
            assert.equal(input.value, "", "It should be empty");
            await triggerEvent(input, null, "focus");
            assert.equal(
                input.value,
                "Untitled spreadsheet",
                "Placeholder should have become the input value"
            );
            assert.equal(input.selectionStart, 0, "It should have selected the value");
            assert.equal(
                input.selectionEnd,
                input.value.length,
                "It should have selected the value"
            );
        });

        QUnit.test("share spreadsheet from control panel", async function (assert) {
            const spreadsheetId = 789;
            const model = new Model();
            const serverData = getBasicServerData();
            serverData.models["documents.document"].records = [
                {
                    name: "My spreadsheet",
                    id: spreadsheetId,
                    spreadsheet_data: JSON.stringify(model.exportData()),
                    folder_id: 465,
                },
            ];
            patchWithCleanup(browser, {
                navigator: {
                    clipboard: {
                        writeText: (url) => {
                            assert.step("share url copied");
                            assert.strictEqual(url, "localhost:8069/share/url/132465");
                        },
                    },
                },
            });
            const def = makeDeferred();
            await createSpreadsheet({
                serverData,
                spreadsheetId,
                mockRPC: async function (route, args) {
                    if (args.method === "action_get_share_url") {
                        await def;
                        assert.step("spreadsheet_shared");
                        const [shareVals] = args.args;
                        assert.strictEqual(args.model, "documents.share");
                        const excel = JSON.parse(JSON.stringify(model.exportXLSX().files));
                        assert.deepEqual(shareVals, {
                            document_ids: [x2ManyCommands.set([spreadsheetId])],
                            folder_id: 465,
                            type: "ids",
                            spreadsheet_shares: [
                                {
                                    spreadsheet_data: JSON.stringify(model.exportData()),
                                    document_id: spreadsheetId,
                                    excel_files: excel,
                                },
                            ],
                        });
                        return "localhost:8069/share/url/132465";
                    }
                },
            });
            assert.strictEqual(target.querySelector(".spreadsheet_share_dropdown"), null);
            await click(target, "i.fa-share-alt");
            assert.equal(
                target.querySelector(".spreadsheet_share_dropdown")?.innerText,
                "Generating sharing link"
            );
            def.resolve();
            await nextTick();
            assert.verifySteps(["spreadsheet_shared", "share url copied"]);
            assert.strictEqual(
                target.querySelector(".o_field_CopyClipboardChar").innerText,
                "localhost:8069/share/url/132465"
            );
            await click(target, ".fa-clipboard");
            assert.verifySteps(["share url copied"]);
        });

        QUnit.test("changing contents will recreate the share", async function (assert) {
            const spreadsheetId = 789;
            const model = new Model();
            const serverData = getBasicServerData();
            let counter = 0;
            serverData.models["documents.document"].records = [
                {
                    name: "My spreadsheet",
                    id: spreadsheetId,
                    spreadsheet_data: JSON.stringify(model.exportData()),
                    folder_id: 465,
                },
            ];
            patchWithCleanup(browser, {
                navigator: {
                    clipboard: {
                        writeText: (url) => {},
                    },
                },
            });
            const { model: newModel } = await createSpreadsheet({
                serverData,
                spreadsheetId,
                mockRPC: async function (route, args) {
                    if (args.method === "action_get_share_url") {
                        return `localhost:8069/share/url/${++counter}`;
                    }
                },
            });
            await click(target, "i.fa-share-alt");
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_CopyClipboardChar").innerText,
                "localhost:8069/share/url/1"
            );

            await click(target, "i.fa-share-alt"); // close share dropdown

            await click(target, "i.fa-share-alt");
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_CopyClipboardChar").innerText,
                "localhost:8069/share/url/1"
            );

            await click(target, "i.fa-share-alt"); // close share dropdown
            newModel.dispatch("UPDATE_CELL", {
                col: 0,
                row: 1,
                sheetId: newModel.getters.getActiveSheetId(),
                content: "I am new value",
            });
            await nextTick();

            await click(target, "i.fa-share-alt");
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_CopyClipboardChar").innerText,
                "localhost:8069/share/url/2"
            );
        });

        QUnit.test("toggle favorite", async function (assert) {
            assert.expect(5);
            await createSpreadsheet({
                spreadsheetId: 1,
                mockRPC: async function (route, args) {
                    if (args.method === "toggle_favorited" && args.model === "documents.document") {
                        assert.step("favorite_toggled");
                        assert.deepEqual(args.args[0], [1], "It should write the correct document");
                        return true;
                    }
                    if (route.includes("dispatch_spreadsheet_message")) {
                        return Promise.resolve();
                    }
                },
            });
            assert.containsNone(target, ".favorite_button_enabled");
            await click(target, ".o_spreadsheet_favorite");
            assert.containsOnce(target, ".favorite_button_enabled");
            assert.verifySteps(["favorite_toggled"]);
        });

        QUnit.test("already favorited", async function (assert) {
            assert.expect(1);
            await createSpreadsheet({ spreadsheetId: 2 });
            assert.containsOnce(
                target,
                ".favorite_button_enabled",
                "It should already be favorited"
            );
        });

        QUnit.test("Spreadsheet action is named in breadcrumb", async function (assert) {
            assert.expect(3);
            const { webClient } = await createSpreadsheetFromPivotView();
            await doAction(webClient, {
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "pivot"]],
            });
            await nextTick();
            const items = target.querySelectorAll(".breadcrumb-item");
            const [breadcrumb1, breadcrumb2] = Array.from(items).map((item) => item.innerText);
            assert.equal(breadcrumb1, "pivot view");
            assert.equal(breadcrumb2, "Untitled spreadsheet");
            assert.equal(target.querySelector(".o_breadcrumb .active").innerText, "Partner");
        });

        QUnit.test(
            "Spreadsheet action is named in breadcrumb with the updated name",
            async function (assert) {
                assert.expect(3);
                const { webClient } = await createSpreadsheetFromPivotView({
                    serverData: {
                        models: getBasicData(),
                        views: {
                            "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="bar" type="col"/>
                                <field name="foo" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                            "partner,false,search": `<search/>`,
                        },
                    },
                });
                await editInput(target, ".o_spreadsheet_name input", "My awesome spreadsheet");
                await doAction(webClient, {
                    name: "Partner",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "pivot"]],
                });
                await nextTick();
                const items = target.querySelectorAll(".breadcrumb-item");
                const [breadcrumb1, breadcrumb2] = Array.from(items).map((item) => item.innerText);
                assert.equal(breadcrumb1, "pivot view");
                assert.equal(breadcrumb2, "My awesome spreadsheet");
                assert.equal(
                    target.querySelector(".o_breadcrumb .active span").innerText,
                    "Partner"
                );
            }
        );
    }
);
