import { pasteText, splitBlock } from "@html_editor/../tests/_helpers/user_actions";

import {
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import {
    getEditorFromComposerEl,
    insertTextInComposer,
} from "@mail/../tests/mail_test_helpers_composer";
import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

async function openComposer() {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-html");
}

test("new line inserts a line break instead of a new paragraph", async () => {
    await openComposer();
    await insertTextInComposer(".o-mail-Composer", "Hello");
    // What Enter does when it doesn't send the message (e.g. on mobile).
    splitBlock(getEditorFromComposerEl(".o-mail-Composer"));
    await insertTextInComposer(".o-mail-Composer", "World");
    expect(".o-mail-Composer-html > .o-paragraph").toHaveCount(1);
    expect(".o-mail-Composer-html .o-paragraph").toHaveInnerHTML("Hello<br>World");
});

test("pasted multi-line text keeps line breaks in a single paragraph", async () => {
    await openComposer();
    pasteText(getEditorFromComposerEl(".o-mail-Composer"), "Hello\nWorld");
    await contains(".o-mail-Composer-html .o-paragraph:contains('World')");
    expect(".o-mail-Composer-html > .o-paragraph").toHaveCount(1);
    expect(".o-mail-Composer-html .o-paragraph").toHaveInnerHTML("Hello<br>World");
});
