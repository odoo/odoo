import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { DiscussChannel } from "@mail/../tests/mock_server/mock_models/discuss_channel";
import { describe, expect, test } from "@odoo/hoot";
import { keyDown, runAllTimers } from "@odoo/hoot-dom";
import { asyncStep, onRpc, waitForSteps } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("onchange_on_keydown option triggers onchange properly", async () => {
    DiscussChannel._onChanges.description = () => {};
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    onRpc("discuss.channel", "onchange", (params) => {
        expect(params.args[1].description).toBe("testing the keydown event");
        asyncStep("onchange");
    });
    await openFormView("discuss.channel", channelId, {
        arch: "<form><field name='description' onchange_on_keydown='True'/></form>",
    });
    await insertText("textarea#description_0", "testing the keydown event");
    await waitForSteps(["onchange"]);
});

test("editing a text field with the onchange_on_keydown option disappearing shouldn't trigger a crash", async () => {
    DiscussChannel._onChanges.description = () => {};
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("discuss.channel", "onchange", () => asyncStep("onchange"));
    await start();
    await openFormView("discuss.channel", channelId, {
        arch: `
            <form>
                <field name="description" onchange_on_keydown="True" invisible="name == 'yop'"/>
                <field name="name"/>
            </form>
        `,
    });
    await click("textarea#description_0");
    await keyDown("a");
    await insertText("[name=name] input", "yop", { replace: true });
    await contains("textarea#description_0", { count: 0 });
    await runAllTimers();
    await waitForSteps([]);
});
