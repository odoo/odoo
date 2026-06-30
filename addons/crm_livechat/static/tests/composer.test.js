import { defineCrmLivechatModels } from "@crm_livechat/../tests/crm_livechat_test_helpers";
import {
    click,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { asyncStep, onRpc, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineCrmLivechatModels();

test("Can execute lead command", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
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
