import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("can add emojis to a poll option", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Composer button[title='More Actions']");
    await click(".o-dropdown-item:contains('Start a Poll')");
    await contains(".modal-header", { text: "Create a poll" });
    await click(".o-mail-CreatePollOptionDialog:first .fa-smile-o");
    await click(".o-Emoji:contains('😀')");
    await contains(".o-mail-CreatePollOptionDialog input:eq(0)", { value: "😀" });
});
