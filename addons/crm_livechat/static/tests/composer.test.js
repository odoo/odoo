import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Can execute lead command", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    onRpc("discuss.channel", "execute_command_lead", (params) => {
        step("execute_command_lead");
        expect(params.args[0]).toEqual([channelId]);
        return true;
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/lead great lead");
    await click(".o-mail-Composer-send:enabled");
    await assertSteps(["execute_command_lead"]);
});
