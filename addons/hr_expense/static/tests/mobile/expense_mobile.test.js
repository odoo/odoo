import { describe, expect, test } from "@odoo/hoot";
import { openListView, registerArchs, start } from "@mail/../tests/mail_test_helpers";
import { defineHrExpenseModels } from "@hr_expense/../tests/hr_expense_test_helpers";
import { tick } from "@odoo/hoot-mock";

describe.current.tags("mobile");
defineHrExpenseModels();

const newArchs = {
    "res.partner,false,search": `<search/>`,
    "res.partner,false,list": `
                <tree js_class="hr_expense_dashboard_tree">
                    <field name="display_name"/>
                </tree>
            `,
};

test("expense dashboard can horizontally scroll", async () => {
    registerArchs(newArchs);
    await start();
    await openListView("res.partner");
    const statusBar = document.querySelector(".o_expense_container");
    statusBar.scrollLeft = 20;
    await tick();
    expect(statusBar.scrollLeft).toBe(20);
});
