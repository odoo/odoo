import {
    defineDocumentSpreadsheetModels,
    getBasicData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import {
    createSpreadsheet,
    createSpreadsheetTemplate,
} from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { contains, mockService, onRpc } from "@web/../tests/web_test_helpers";

defineDocumentSpreadsheetModels();

const { topbarMenuRegistry } = spreadsheet.registries;

test("new template menu", async function () {
    mockService("action", {
        doAction({ params, tag }) {
            if (tag === "action_open_template" && params.spreadsheet_id[0] === newTemplateId) {
                expect.step("redirect");
            }
            return super.doAction(...arguments);
        },
    });
    onRpc("spreadsheet.template", "create", ({ parent }) => {
        expect.step("new_template");
        const result = parent();
        newTemplateId = result[0];
        return result;
    });
    let newTemplateId = null;
    const models = getBasicData();
    const { env } = await createSpreadsheetTemplate({
        serverData: { models },
    });
    await doMenuAction(topbarMenuRegistry, ["file", "new_sheet"], env);
    await animationFrame();
    expect.verifySteps(["new_template", "redirect"]);
});

test("copy template menu", async function () {
    mockService("action", {
        doAction({ params, tag }) {
            if (tag === "action_open_template" && params.spreadsheet_id === newTemplateId) {
                expect.step("redirect");
            }
            return super.doAction(...arguments);
        },
    });
    onRpc("spreadsheet.template", "copy", ({ kwargs, parent }) => {
        expect.step("template_copied");
        expect(kwargs.default).toInclude("spreadsheet_data");
        expect(kwargs.default).not.toInclude("thumbnail");
        const result = parent();
        newTemplateId = result[0];
        return result;
    });
    let newTemplateId = null;
    const models = getBasicData();
    const { env } = await createSpreadsheetTemplate({
        serverData: { models },
    });
    await doMenuAction(topbarMenuRegistry, ["file", "make_copy"], env);
    await animationFrame();
    expect.verifySteps(["template_copied", "redirect"]);
});

test("Save as template menu", async function () {
    mockService("action", {
        async doAction(actionRequest, options) {
            if (actionRequest === "documents_spreadsheet.save_spreadsheet_template_action") {
                expect.step("create_template_wizard");

                const context = options?.additionalContext;
                const data = JSON.parse(context.default_spreadsheet_data);
                const name = context.default_template_name;
                const cells = data.sheets[0].cells;
                expect(name).toBe("Untitled spreadsheet - Template", {
                    message: "It should be named after the spreadsheet",
                });
                expect(context).toInclude("default_thumbnail");
                expect(cells.A3.content).toBe(`=PIVOT.HEADER(1,"product_id",37)`);
                expect(cells.B3.content).toBe(
                    `=PIVOT.VALUE(1,"probability:avg","product_id",37,"bar",FALSE)`
                );
                expect(cells.A11.content).toBe("😃");
                return true;
            }
            return super.doAction(...arguments);
        },
    });
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
            },
        },
    });
    setCellContent(model, "A11", "😃");
    await doMenuAction(topbarMenuRegistry, ["file", "save_as_template"], env);
    await animationFrame();
    expect.verifySteps(["create_template_wizard"]);
});

test("Name template with spreadsheet name", async function () {
    mockService("action", {
        async doAction(actionRequest, options) {
            if (actionRequest === "documents_spreadsheet.save_spreadsheet_template_action") {
                expect.step("create_template_wizard");
                const name = options?.additionalContext.default_template_name;
                expect(name).toBe("My spreadsheet - Template", {
                    message: "It should be named after the spreadsheet",
                });
                return true;
            }
            return super.doAction(...arguments);
        },
    });
    onRpc("spreadsheet.template", "create", ({ args }) => {
        expect.step("create_template");
        expect(args[0].name).toBe("My spreadsheet", {
            message: "It should be named after the spreadsheet",
        });
    });
    const { env } = await createSpreadsheet();
    const target = getFixture();
    const input = target.querySelector(".o_sp_name input");
    await contains(input).edit("My spreadsheet");
    await doMenuAction(topbarMenuRegistry, ["file", "save_as_template"], env);
    await animationFrame();
    expect.verifySteps(["create_template_wizard"]);
});
