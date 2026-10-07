import { expect, test } from "@odoo/hoot";
import { mountView, onRpc, defineModels, models, fields } from "@web/../tests/web_test_helpers";

class MyModel extends models.Model {
    _name = "my.model";
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["done", "Done"],
        ],
    });
    // The dependency added in the PR
    display_name = fields.Char();

    _records = [{ id: 1, state: "draft", display_name: "Test Record" }];
}
defineModels([MyModel]);

test("statusbar field automatically fetches display_name", async () => {
    onRpc("web_read", (args) => {
        expect.step("web_read");

        const spec = args.kwargs.specification || {};
        expect("display_name" in spec).toBe(true, {
            message: "The statusbar field must declare display_name as a dependency",
        });
    });

    await mountView({
        type: "form",
        resModel: "my.model",
        resId: 1,
        arch: `
            <form>
                <header>
                    <!-- display_name is intentionally missing from the arch -->
                    <field name="state" widget="statusbar" />
                </header>
            </form>`,
    });

    expect.verifySteps(["web_read"]);
});
