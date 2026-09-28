import { defineCrmLivechatModels } from "@crm_livechat/../tests/crm_livechat_test_helpers";
import {
    click,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { describe, expect, test } from "@odoo/hoot";
import { onRpc, serverState } from "@web/../tests/web_test_helpers";

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
        expect.step(args[0]);
        return true;
    });
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "/lead great lead");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await expect.waitForSteps([[channelId]]);
});
