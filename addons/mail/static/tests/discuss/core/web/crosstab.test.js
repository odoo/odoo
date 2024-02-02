/** @odoo-module */

import { test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    insertText,
    start,
    startServer,
    step,
} from "../../../mail_test_helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

test.skip("Channel subscription is renewed when channel is manually added", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([
        { name: "my channel" },
        { name: "General", channel_member_ids: [] },
    ]);
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            step("update-channels");
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "my channel" });
    await assertSteps(["update-channels"]);
    await click("[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "General");
    await click(":nth-child(1 of .o-discuss-ChannelSelector-suggestion)");
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await assertSteps(["update-channels"]);
});
