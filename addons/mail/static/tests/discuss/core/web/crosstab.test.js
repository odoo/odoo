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
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Channel subscription is renewed when channel is manually added", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General", channel_member_ids: [] });
    await start();
    patchWithCleanup(getService("bus_service"), {
        forceUpdateChannels() {
            step("update-channels");
        },
    });
    await openDiscuss();
    await click("input[placeholder='Find or start a conversation']");
    await insertText("input[placeholder='Search a conversation']", "General");
    await click("a", { text: "General" });
    await contains(".o-mail-DiscussSidebar-item", { text: "General" });
    await assertSteps(["update-channels"]);
});
