import {
    describe,
    expect,
    test
} from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class HrExpense extends models.Model {
    _name = "hr.expense";

    name = fields.Char();
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["submitted", "Submitted"],
            ["approved", "Approved"],
            ["done", "Posted"],
        ],
    });

    _records = [{ id: 1, name: "Hotel", state: "approved" }];
}


defineMailModels();
defineModels({ HrExpense });

describe.current.tags("desktop");

test("wizard closing with noReload does not reload the expense list", async () => {
    // Simulate the framework's real behavior when the wizard's "Post Expenses"
    // button redirects to a new action (e.g. the created journal entries):
    // action_service.js always passes { noReload: true } in that case.
    mockService("action", {
        async doAction(action, options) {
            await options.onClose?.({ noReload: true });
            return true;
        },
    });

    patchWithCleanup(user, {hasGroup: () => true});
    onRpc("hr.expense", "action_post", () => ({
        type: "ir.actions.act_window",
        res_model: "hr.expense.post.wizard",
        target: "new",
        views: [[false, "form"]],
    }));
    onRpc("hr.expense", "web_search_read", () => expect.step("web_search_read"));
    await mountView({
        resModel: "hr.expense",
        type: "list",
        arch: `
        <list js_class="hr_expense_tree">
            <field name="name"/>
            <field name="state"/>
        </list>`
    });
    expect.verifySteps(["web_search_read"]); // initial mount
    await contains(".o_data_row .o_list_record_selector input").click();
    await contains("button:contains(Post Entries)").click();

    // onClose's own reload is skipped; only the unconditional reload that
    // already happens right when the wizard dialog opens remains
    expect.verifySteps(["web_search_read"]);
});
