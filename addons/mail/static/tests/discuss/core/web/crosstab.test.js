import { describe, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
} from "../../../mail_test_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Channel subscription is renewed when channel is manually added", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General", channel_member_ids: [] });
    const env = await start();
    patchWithCleanup(env.services.bus_service, {
        forceUpdateChannels() {
            step("update-channels");
        },
    });
    await openDiscuss();
    await click("[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "General");
    await click(":nth-child(1 of .o-discuss-ChannelSelector-suggestion)");
    await contains(".o-mail-DiscussSidebarChannel", { text: "General" });
    await assertSteps(["update-channels"]);
});
