import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import {
    containsTextInComposer,
    insertTextInComposer,
} from "@mail/../tests/mail_test_helpers_composer";

import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

async function openComposer() {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-html:focus");
}

// Emojis are inserted through the editor: native undo cannot revert them.
test("undo an emoji inserted from the picker", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤠')");
    await containsTextInComposer(".o-mail-Composer", "Blabla🤠");
    // the emoji picker holds the focus while open: the shortcut needs it back
    await contains(".o-mail-Composer-html:focus");
    await press(["control", "z"]);
    await containsTextInComposer(".o-mail-Composer", "Blabla");
});

test("redo an emoji insertion undone with control+z", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤠')");
    await contains(".o-mail-Composer-html:focus");
    await press(["control", "z"]);
    await containsTextInComposer(".o-mail-Composer", "Blabla");
    await press(["control", "shift", "z"]);
    await containsTextInComposer(".o-mail-Composer", "Blabla🤠");
    await press(["control", "z"]);
    await containsTextInComposer(".o-mail-Composer", "Blabla");
    await press(["control", "y"]);
    await containsTextInComposer(".o-mail-Composer", "Blabla🤠");
});
