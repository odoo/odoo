import { deleteBackward } from "@html_editor/../tests/_helpers/user_actions";
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
    getEditorFromComposerEl,
    insertTextInComposer,
} from "@mail/../tests/mail_test_helpers_composer";
import { beforeEach, describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { Composer } from "@mail/core/common/composer";
import { press } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    // Simulate real user interactions
    patchWithCleanup(Composer.prototype, {
        isEventTrusted() {
            return true;
        },
    });
});

test('[text composer] display command suggestions on typing "/"', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "/");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

test.tags("html composer");
test("display command suggestions on typing '/'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "/");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

test("[text composer] use a command for a specific channel type", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "/");
    await click(".o-mail-Composer-suggestion strong:text('who')");
    await containsTextInComposer(".o-mail-Composer", "/who\u00a0");
});

test.tags("html composer");
test("use a command for a specific channel type", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "/");
    await click(".o-mail-Composer-suggestion strong:text('who')");
    await containsTextInComposer(".o-mail-Composer", "/who\u00a0");
});

test("[text composer] command suggestion should only open if command is the first character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "bluhbluh");
    await containsTextInComposer(".o-mail-Composer", "bluhbluh");
    await insertTextInComposer(".o-mail-Composer", "/");
    // weak test, no guarantee that we waited long enough for the potential list to open
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
});

test.tags("html composer");
test("command suggestion should only open if command is the first character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "bluhbluh");
    await containsTextInComposer(".o-mail-Composer", "bluhbluh");
    await insertTextInComposer(".o-mail-Composer", "/");
    // weak test, no guarantee that we waited long enough for the potential list to open
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
});

test("Sort partner suggestions by recent chats", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const [partner_1, partner_2, partner_3] = pyEnv["res.partner"].create([
        { name: "User 1" },
        { name: "User 2" },
        { name: "User 3" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partner_1 },
        { partner_id: partner_2 },
        { partner_id: partner_3 },
    ]);
    pyEnv["discuss.channel"].create([
        {
            name: "General",
            channel_type: "channel",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partner_1 }),
                Command.create({ partner_id: partner_2 }),
                Command.create({ partner_id: partner_3 }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: partner_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:10",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: partner_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:20",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ partner_id: partner_3 }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel-itemName:text('User 2')");
    await insertTextInComposer(".o-mail-Composer", "This is a test");
    await press("Enter");
    await contains(".o-mail-Message-content:text('This is a test')");
    await click(".o-mail-DiscussSidebarChannel-itemName:text('General')");
    await contains(
        ".o-mail-DiscussSidebarCategory-chat + .o-mail-DiscussSidebarCategory-channels .o-mail-DiscussSidebarChannel:eq(0):has(:text('User 2'))"
    );
    await contains(".o-mail-Composer [o-we-hint-text='Message #General…']");
    await insertTextInComposer(".o-mail-Composer", "@");
    await insertTextInComposer(".o-mail-Composer", "User");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
    await contains(".o-mail-Composer-suggestion:eq(0) strong:text('User 2')");
    await contains(".o-mail-Composer-suggestion:eq(1) strong:text('User 3')");
    await contains(".o-mail-Composer-suggestion:eq(2) strong:text('User 1')");
});

test("mention suggestion are shown after deleting a character", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@John D");
    await contains(".o-mail-Composer-suggestion strong:text('John Doe')");
    await insertTextInComposer(".o-mail-Composer", "a");
    await contains(".o-mail-Composer-suggestion strong:text('John D')", { count: 0 });
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    deleteBackward(editor);
    await contains(".o-mail-Composer-suggestion strong:text('John Doe')");
});

test("[text composer] command suggestion are shown after deleting a character", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "/he");
    await contains(".o-mail-Composer-suggestion strong:text('help')");
    await insertTextInComposer(".o-mail-Composer", "e");
    await contains(".o-mail-Composer-suggestion strong:text('help')", { count: 0 });
    const editor = getEditorFromComposerEl(".o-mail-Composer-html");
    deleteBackward(editor);
    await contains(".o-mail-Composer-suggestion strong:text('help')");
});

test.tags("html composer");
test("command suggestion are shown after deleting a character", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "/he");
    await contains(".o-mail-Composer-suggestion strong:text('help')");
    await insertTextInComposer(".o-mail-Composer", "e");
    await contains(".o-mail-Composer-suggestion strong:text('help')", { count: 0 });
    await press("Backspace");
    await contains(".o-mail-Composer-suggestion strong:text('help')");
});

test("mention suggestion displays OdooBot before archived partners", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane", active: false });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Our channel",
        channel_type: "group",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
            Command.create({ partner_id: serverState.odoobotId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@");
    await contains(".o-mail-Composer-suggestion", { count: 3 });
    await contains(".o-mail-Composer-suggestion:has(:text('OdooBot'))", {
        before: [
            ".o-mail-Composer-suggestion:has(:text('Mitchell Admin'))",
            {
                before: [".o-mail-Composer-suggestion:has(:text('Jane'))"],
            },
        ],
    });
});
