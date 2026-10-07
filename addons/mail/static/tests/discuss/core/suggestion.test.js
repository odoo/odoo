import {
    contains as mailContains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { htmlInsertText } from "@mail/../tests/mail_test_helpers_html";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, contains, getService, serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import { Composer } from "@mail/core/common/composer";
import { press, waitFor, waitForNone } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    // Simulate real user interactions
    patch(Composer.prototype, {
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
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await insertText(".o-mail-Composer-input", "/");
    await waitFor(".o-mail-Composer-suggestionList .o-open:count(1)");
});

test.tags("html composer");
test("display command suggestions on typing '/'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "/");
    await waitFor(".o-mail-Composer-suggestionList .o-open:count(1)");
});

test("[text composer] use a command for a specific channel type", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await mailContains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-Composer-suggestion strong:text('who'):count(1)").click();
    await mailContains(".o-mail-Composer-input", { value: "/who " });
});

test.tags("html composer");
test("use a command for a specific channel type", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "/");
    await contains(".o-mail-Composer-suggestion strong:text('who'):count(1)").click();
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:text('/who'):count(1)");
});

test("[text composer] command suggestion should only open if command is the first character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await mailContains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    await mailContains(".o-mail-Composer-input", { value: "bluhbluh " });
    await insertText(".o-mail-Composer-input", "/");
    // weak test, no guarantee that we waited long enough for the potential list to open
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
});

test.tags("html composer");
test("command suggestion should only open if command is the first character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "bluhbluh");
    await waitFor(".o-mail-Composer-html.odoo-editor-editable:text('bluhbluh'):count(1)");
    await htmlInsertText(editor, "/");
    // weak test, no guarantee that we waited long enough for the potential list to open
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
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
    getService("bus_service").subscribe("discuss.channel/new_message", () =>
        // Message notification holds the last_interest_dt update. We must wait for it to
        // ensure the suggestion service sort is deterministic.
        expect.step("new_message")
    );
    await openDiscuss();
    await contains(".o-mail-NotificationItem:has(:text('User 2')):count(1)").click();
    await insertText(".o-mail-Composer-input", "This is a test");
    await press("Enter");
    await waitFor(".o-mail-Message-content:text('This is a test'):count(1)");
    await expect.waitForSteps(["new_message"]);
    await contains(".o-mail-MessagingMenu-tab[data-id='channel']:count(1)").click();
    await contains(".o-mail-NotificationItem:has(:text('General')):count(1)").click();
    await insertText(".o-mail-Composer-input[placeholder='Message #General…']", "@");
    await insertText(".o-mail-Composer-input", "User");
    await waitFor(".o-mail-Composer-suggestion strong:count(3)");
    await waitFor(".o-mail-Composer-suggestion:eq(0) strong:text('User 2'):count(1)");
    await waitFor(".o-mail-Composer-suggestion:eq(1) strong:text('User 3'):count(1)");
    await waitFor(".o-mail-Composer-suggestion:eq(2) strong:text('User 1'):count(1)");
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
    await insertText(".o-mail-Composer-input", "@John D");
    await waitFor(".o-mail-Composer-suggestion strong:text('John Doe'):count(1)");
    await insertText(".o-mail-Composer-input", "a");
    await waitForNone(".o-mail-Composer-suggestion strong:text('John D')");
    // Simulate pressing backspace
    const textarea = document.querySelector(".o-mail-Composer-input");
    textarea.value = textarea.value.slice(0, -1);
    await waitFor(".o-mail-Composer-suggestion strong:text('John Doe'):count(1)");
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
    await insertText(".o-mail-Composer-input", "/he");
    await waitFor(".o-mail-Composer-suggestion strong:text('help'):count(1)");
    await insertText(".o-mail-Composer-input", "e");
    await waitForNone(".o-mail-Composer-suggestion strong:text('help')");
    // Simulate pressing backspace
    const textarea = document.querySelector(".o-mail-Composer-input");
    textarea.value = textarea.value.slice(0, -1);
    await waitFor(".o-mail-Composer-suggestion strong:text('help'):count(1)");
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
    const composerService = getService("mail.composer");
    composerService.setHtmlComposer();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-suggestionList:count(1)");
    await waitForNone(".o-mail-Composer-suggestionList .o-open");
    await focus(".o-mail-Composer-html.odoo-editor-editable");
    const editor = {
        document,
        editable: document.querySelector(".o-mail-Composer-html.odoo-editor-editable"),
    };
    await htmlInsertText(editor, "/he");
    await waitFor(".o-mail-Composer-suggestion strong:text('help'):count(1)");
    await htmlInsertText(editor, "e");
    await waitForNone(".o-mail-Composer-suggestion strong:text('help')");
    await press("Backspace");
    await waitFor(".o-mail-Composer-suggestion strong:text('help'):count(1)");
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
    await insertText(".o-mail-Composer-input", "@");
    await waitFor(".o-mail-Composer-suggestion:count(3)");
    await mailContains(".o-mail-Composer-suggestion:has(:text('OdooBot'))", {
        before: [
            ".o-mail-Composer-suggestion:has(:text('Mitchell Admin'))",
            {
                before: [".o-mail-Composer-suggestion:has(:text('Jane'))"],
            },
        ],
    });
});
