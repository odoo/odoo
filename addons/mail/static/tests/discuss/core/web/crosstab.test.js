import {
    click,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Channel subscription is renewed when channel is manually added", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General", channel_member_ids: [] });
    await start();
    mockService("bus_service", {
        forceUpdateChannels() {
            expect.step("update-channels");
        },
    });
    await openDiscuss(channelId);
    await click("[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Mitchell Admin" });
    await click("[title='Invite']:enabled");
    await expect.waitForSteps(["update-channels"]);
});
