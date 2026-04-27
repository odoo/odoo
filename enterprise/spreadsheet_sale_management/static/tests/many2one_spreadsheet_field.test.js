import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";

import {
    clickFieldDropdownItem,
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineSpreadsheetSaleModels } from "./helpers/data";
import { mailModels } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");

class SaleOrderTemplate extends models.Model {
    _name = "sale.order.template";

    spreadsheet_template_id = fields.Many2one({ relation: "sale.order.spreadsheet" });

    _records = [];
}

defineSpreadsheetSaleModels();
defineModels({ ...mailModels, SaleOrderTemplate });

test("create record and open action", async () => {
    const action = {
        type: "ir.actions.client",
        tag: "action_sale_order_spreadsheet",
        params: {
            spreadsheet_id: 1,
        },
    };
    onRpc("action_open_new_spreadsheet", ({ args, kwargs }) => {
        expect(kwargs.context.default_name).toBe("yy");
        expect.step("action_open_new_spreadsheet");
        return action; // return any action
    });
    onRpc("web_save", ({ args, kwargs }) => {
        expect(args[1].spreadsheet_template_id).toBe(1);
        expect.step("web_save template");
    });

    mockService("action", {
        doAction(params) {
            expect(params).toEqual(action);
            expect.step("do-action");
        },
    });

    await mountView({
        type: "form",
        resModel: "sale.order.template",
        arch: /*xml*/ `
            <form>
                <field name="spreadsheet_template_id" widget="many2one_spreadsheet"/>
            </form>
        `,
    });

    await contains(".o_field_widget[name=spreadsheet_template_id] input").edit("yy", {
        confirm: false,
    });
    await runAllTimers();
    await clickFieldDropdownItem("spreadsheet_template_id", "Create and edit...");

    expect.verifySteps(["action_open_new_spreadsheet", "web_save template", "do-action"]);
});
