import {
    clickSave,
    contains,
    makeMockServer,
    mockService,
    mountView,
} from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";

describe.current.tags("desktop");
defineHrModels();

test("editing the 'lang' field and saving it triggers a 'reload_context'", async function () {
    const { env } = await makeMockServer();
    const userId = env["fake.user"].create({
        name: "Aline",
        lang: "fr",
    });
    mockService("action", {
        doAction(action) {
            expect.step(action);
        },
    });
    await mountView({
        type: "form",
        resModel: "fake.user",
        arch: `
            <form js_class="hr_user_preferences_form">
                <field name="name"/>
                <field name="lang"/>
            </form>`,
        resId: userId,
    });
    await contains("[name='name'] input").edit("John");
    await clickSave();
    expect.verifySteps([]);
    await contains("[name='lang'] input").edit("En");
    await clickSave();
    expect.verifySteps(["reload_context"]);
});
