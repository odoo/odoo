import {
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { contains, mockService } from "@web/../tests/web_test_helpers";

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
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await contains("[title='Add People']:count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('Mitchell Admin')):count(1)"
    ).click();
    await contains("button:text('Invite'):enabled:count(1)").click();
    await expect.waitForSteps(["update-channels"]);
});
