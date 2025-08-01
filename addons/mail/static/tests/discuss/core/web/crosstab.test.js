import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { asyncStep, mockService, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Channel subscription is renewed when channel is manually added", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General", channel_member_ids: [] });
    await start();
    mockService("bus_service", {
        forceUpdateChannels() {
            asyncStep("update-channels");
        },
    });
    await openDiscuss();
    await click("input[placeholder='Search conversations']");
    await insertText("input[placeholder='Search a conversation']", "General");
    await click("a", { text: "General" });
    await contains(".o-mail-DiscussSidebar-item", { text: "General" });
    await waitForSteps(["update-channels"]);
});
