/** @odoo-module */

import { nextTick, getFixture, editInput } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";

import { actionService } from "@web/webclient/actions/action_service";
import { createSpreadsheet, createSpreadsheetTemplate } from "../spreadsheet_test_utils";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import { createSpreadsheetFromPivotView } from "../utils/pivot_helpers";
import { setCellContent } from "@spreadsheet/../tests/utils/commands";

const { topbarMenuRegistry } = spreadsheet.registries;

QUnit.module("documents_spreadsheet > template menu", {}, () => {
    QUnit.test("new template menu", async function (assert) {
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("actionMain", actionService);
        const fakeActionService = {
            dependencies: ["actionMain"],
            start(env, { actionMain }) {
                return {
                    ...actionMain,
                    doAction: (actionRequest, options = {}) => {
                        if (
                            actionRequest.tag === "action_open_template" &&
                            actionRequest.params.spreadsheet_id === 111
                        ) {
                            assert.step("redirect");
                        }
                        return actionMain.doAction(actionRequest, options);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });
        const models = getBasicData();
        const { env } = await createSpreadsheetTemplate({
            serverData: { models },
            mockRPC: function (route, args) {
                if (args.model == "spreadsheet.template" && args.method === "create") {
                    assert.step("new_template");
                    models["spreadsheet.template"].records.push({
                        id: 111,
                        name: "test template",
                        spreadsheet_data: "{}",
                    });
                    return 111;
                }
            },
        });
        await doMenuAction(topbarMenuRegistry, ["file", "new_sheet"], env);
        await nextTick();
        assert.verifySteps(["new_template", "redirect"]);
    });

    QUnit.test("copy template menu", async function (assert) {
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("actionMain", actionService);
        const fakeActionService = {
            dependencies: ["actionMain"],
            start(env, { actionMain }) {
                return {
                    ...actionMain,
                    doAction: (actionRequest, options = {}) => {
                        if (
                            actionRequest.tag === "action_open_template" &&
                            actionRequest.params.spreadsheet_id === 111
                        ) {
                            assert.step("redirect");
                        }
                        return actionMain.doAction(actionRequest, options);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });
        const models = getBasicData();
        const { env } = await createSpreadsheetTemplate({
            serverData: { models },
            mockRPC: function (route, args) {
                if (args.model == "spreadsheet.template" && args.method === "copy") {
                    assert.step("template_copied");
                    const { spreadsheet_data, thumbnail } = args.kwargs.default;
                    assert.ok(spreadsheet_data);
                    assert.ok(thumbnail);
                    models["spreadsheet.template"].records.push({
                        id: 111,
                        name: "template",
                        spreadsheet_data,
                        thumbnail,
                    });
                    return 111;
                }
            },
        });
        await doMenuAction(topbarMenuRegistry, ["file", "make_copy"], env);
        await nextTick();
        assert.verifySteps(["template_copied", "redirect"]);
    });

    QUnit.test("Save as template menu", async function (assert) {
        assert.expect(7);
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("actionMain", actionService);
        const fakeActionService = {
            dependencies: ["actionMain"],
            start(env, { actionMain }) {
                return Object.assign({}, actionMain, {
                    doAction: (actionRequest, options = {}) => {
                        if (
                            actionRequest ===
                            "documents_spreadsheet.save_spreadsheet_template_action"
                        ) {
                            assert.step("create_template_wizard");

                            const context = options.additionalContext;
                            const data = JSON.parse(context.default_spreadsheet_data);
                            const name = context.default_template_name;
                            const cells = data.sheets[0].cells;
                            assert.equal(
                                name,
                                "Untitled spreadsheet - Template",
                                "It should be named after the spreadsheet"
                            );
                            assert.ok(context.default_thumbnail);
                            assert.equal(
                                cells.A3.content,
                                `=ODOO.PIVOT.HEADER(1,"product_id",ODOO.PIVOT.POSITION(1,"product_id",1))`
                            );
                            assert.equal(
                                cells.B3.content,
                                `=ODOO.PIVOT(1,"probability","product_id",ODOO.PIVOT.POSITION(1,"product_id",1),"bar","false")`
                            );
                            assert.equal(cells.A11.content, "😃");
                            return Promise.resolve(true);
                        }
                        return actionMain.doAction(actionRequest, options);
                    },
                });
            },
        };
        serviceRegistry.add("action", fakeActionService);
        const { env, model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /*xml*/ `
                        <pivot>
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        setCellContent(model, "A11", "😃");
        await doMenuAction(topbarMenuRegistry, ["file", "save_as_template"], env);
        await nextTick();
        assert.verifySteps(["create_template_wizard"]);
    });

    QUnit.test("Name template with spreadsheet name", async function (assert) {
        assert.expect(3);
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("actionMain", actionService);
        const fakeActionService = {
            dependencies: ["actionMain"],
            start(env, { actionMain }) {
                return Object.assign({}, actionMain, {
                    doAction: (actionRequest, options = {}) => {
                        if (
                            actionRequest ===
                            "documents_spreadsheet.save_spreadsheet_template_action"
                        ) {
                            assert.step("create_template_wizard");
                            const name = options.additionalContext.default_template_name;
                            assert.equal(
                                name,
                                "My spreadsheet - Template",
                                "It should be named after the spreadsheet"
                            );
                            return Promise.resolve(true);
                        }
                        return actionMain.doAction(actionRequest, options);
                    },
                });
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });
        const { env } = await createSpreadsheet({
            mockRPC: function (route, args) {
                if (args.method === "create" && args.model === "spreadsheet.template") {
                    assert.step("create_template");
                    assert.equal(
                        args.args[0].name,
                        "My spreadsheet",
                        "It should be named after the spreadsheet"
                    );
                }
            },
        });
        const target = getFixture();
        const input = target.querySelector(".o_spreadsheet_name input");
        await editInput(input, null, "My spreadsheet");
        await doMenuAction(topbarMenuRegistry, ["file", "save_as_template"], env);
        await nextTick();
        assert.verifySteps(["create_template_wizard"]);
    });
});
