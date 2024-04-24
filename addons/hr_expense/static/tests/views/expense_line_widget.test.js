import { describe, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    start,
    startServer,
    step,
    onRpcBefore,
    registerArchs,
    openFormView,
    patchUiSize,
    SIZES,
} from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";
import { getOrigin } from "@web/core/utils/urls";
import { defineHrExpenseModels } from "@hr_expense/../tests/hr_expense_test_helpers";

describe.current.tags("desktop");
defineHrExpenseModels();

const newArchs = {
    "hr.expense.sheet,false,form": `<form>
                    <sheet name="Expenses">
                        <notebook>
                            <page name="expenses" string="Expense">
                                <field name="expense_line_ids" widget="expense_lines_widget">
                                    <tree>
                                        <field name="name"/>
                                        <field name="message_main_attachment_id"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                    <div class="o_attachment_preview"/>
                    <chatter/>
                </form>`
};

test("ExpenseLineWidget test attachments change on expense line click", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const sheetId = pyEnv["hr.expense.sheet"].create({ name: "Expense Sheet test" });
    const expense_lines = pyEnv["hr.expense"].create([
        { name: "Lunch", sheet_id: sheetId },
        { name: "Taxi", sheet_id: sheetId },
        { name: "Misc", sheet_id: sheetId },
    ]);
    const attachmentIds = pyEnv["ir.attachment"].create([
        { res_id: expense_lines[0], res_model: "hr.expense", mimetype: "application/pdf" },
        { res_id: expense_lines[0], res_model: "hr.expense", mimetype: "application/pdf" },
        { res_id: expense_lines[1], res_model: "hr.expense", mimetype: "application/pdf" },
        { res_id: expense_lines[1], res_model: "hr.expense", mimetype: "application/pdf" },
    ]);
    pyEnv["hr.expense.sheet"].write([sheetId], { expense_line_ids: expense_lines });
    pyEnv["hr.expense"].write([expense_lines[0]], {
        message_main_attachment_id: attachmentIds[1],
    });
    pyEnv["hr.expense"].write([expense_lines[1]], {
        message_main_attachment_id: attachmentIds[2],
    });
    onRpcBefore("/mail/action", (args) => {
        if (args.init_messaging) {
            step(`/mail/action - ${JSON.stringify(args)}`);
        }
    });
    registerArchs(newArchs);
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    await openFormView("hr.expense.sheet", sheetId);
    await contains(".o_data_row", { count: 3 });
    // Default attachment is the last one.
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            `${getOrigin()}/web/content/4`
        )}#pagemode=none']`
    );
    await click(":nth-child(1 of .o_data_row) :nth-child(1 of .o_data_cell)");
    // Attachment is switched to the main attachment in expense line one.
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            `${getOrigin()}/web/content/2`
        )}#pagemode=none']`
    );
    await assertSteps([], "no extra rpc should be done");
    // No change since line three has no attachments.
    await click(":nth-child(3 of .o_data_row) :nth-child(1 of .o_data_cell)");
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            `${getOrigin()}/web/content/2`
        )}#pagemode=none']`
    );
    await assertSteps([], "no extra rpc should be done");
    await click(":nth-child(2 of .o_data_row) :nth-child(1 of .o_data_cell)");
    // Attachment is switched to the main attachment in expense line two.
    await contains(
        `.o_attachment_preview iframe[data-src='/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            `${getOrigin()}/web/content/3`
        )}#pagemode=none']`
    );
});
