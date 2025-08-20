import {
    click,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { asyncStep, onRpc, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Can execute lead command", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    onRpc("discuss.channel", "execute_command_lead", ({ args }) => {
        asyncStep(args[0]);
        return true;
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/lead great lead");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await waitForSteps([[channelId]]);
});
