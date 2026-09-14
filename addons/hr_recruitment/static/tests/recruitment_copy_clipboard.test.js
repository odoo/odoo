import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

class HrRecruitmentSource extends models.Model {
    _name = "hr.recruitment.source";

    email = fields.Char({ string: "Email" });
    url = fields.Char({ string: "Tracker URL" });

    _records = [{ id: 1, email: false, url: "https://example.com/jobs/1" }];

    _views = {
        list: `<list><field name="url" widget="RecruitmentCopyClipboardChar" options="{'displayed_value': 'URL'}"/><field name="email" widget="RecruitmentCopyClipboardChar" options="{'content_generation_function_name': 'create_and_get_alias', 'displayed_value': 'Email'}"/></list>`,
    };
}

defineModels([HrRecruitmentSource]);

beforeEach(() => {
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(`writeText: ${text}`);
        },
    });
});

/** @returns {HTMLElement[]} the two copy buttons, plain first, generating second */
function copyButtons() {
    const buttons = queryAll(".o_clipboard_button");
    expect(buttons).toHaveLength(2, {
        message: "both branches of the widget must render a copy button",
    });
    return buttons;
}

test("both branches of the widget render a copy button", async () => {
    await mountView({ type: "list", resModel: "hr.recruitment.source" });

    expect(".o_data_row").toHaveCount(1);
    expect(".o_clipboard_button").toHaveCount(2);
    // the t-else branch shows the field's value, the t-if branch its label
    expect(".o_data_row").toHaveText(/URL/);
    expect(".o_data_row").toHaveText(/Email/);
});

test("the plain branch copies the field's own value", async () => {
    await mountView({ type: "list", resModel: "hr.recruitment.source" });

    await click(copyButtons()[0]);
    await animationFrame();

    expect.verifySteps(["writeText: https://example.com/jobs/1"]);
});

test("the generating branch copies what the server returns, not the empty field", async () => {
    onRpc("hr.recruitment.source", "create_and_get_alias", ({ args }) => {
        expect.step(`create_and_get_alias(${JSON.stringify(args)})`);
        return "jobs+linkedin@example.com";
    });
    await mountView({ type: "list", resModel: "hr.recruitment.source" });

    await click(copyButtons()[1]);
    await animationFrame();

    expect.verifySteps([
        "create_and_get_alias([1])",
        "writeText: jobs+linkedin@example.com",
    ]);
});

test("the generating branch asks the server on every click", async () => {
    let alias = "first@example.com";
    onRpc("hr.recruitment.source", "create_and_get_alias", () => alias);
    await mountView({ type: "list", resModel: "hr.recruitment.source" });

    await click(copyButtons()[1]);
    await animationFrame();
    alias = "second@example.com";
    await click(copyButtons()[1]);
    await animationFrame();

    // Pins the behaviour, and deliberately does NOT claim to distinguish the
    // shape this widget had before 8c630dedebf9. Driven against that shape in a
    // worktree, all four of these tests pass: the old subclass assigned
    // `this.props.content = await generator()` on every click, so the generator
    // was re-invoked every time too. That refactor removed duplication and a
    // props mutation, not a behavioural defect -- the two are indistinguishable
    // from outside, and a test comment claiming otherwise would be a lie a
    // reader has no way to check.
    expect.verifySteps([
        "writeText: first@example.com",
        "writeText: second@example.com",
    ]);
});
