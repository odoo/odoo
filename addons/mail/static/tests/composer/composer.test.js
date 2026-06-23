import { useSubEnv } from "@web/owl2/utils";
import {
    deleteBackward,
    pasteText,
    tripleClick,
} from "@html_editor/../tests/_helpers/user_actions";

import {
    SIZES,
    click,
    contains,
    defineMailModels,
    dragenterFiles,
    dropFiles,
    focus,
    inputFiles,
    onRpcBefore,
    openDiscuss,
    openFormView,
    pasteFiles,
    patchUiSize,
    registerArchs,
    scroll,
    setIndexedDB,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import {
    containsSelectionInComposer,
    containsTextInComposer,
    getEditorFromComposerEl,
    insertTextInComposer,
    setSelectionInComposer,
} from "@mail/../tests/mail_test_helpers_composer";
import { beforeEach, describe, expect, queryFirst, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-mock";
import {
    Command,
    getService,
    onRpc,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

import { Composer } from "@mail/core/common/composer";
import { press } from "@odoo/hoot-dom";
import { MailComposerFormController } from "@mail/chatter/web/mail_composer_form";
import { getIndexedDB } from "../mail_test_helpers";
import { waitNotifications } from "@bus/../tests/bus_test_helpers";

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

function cut(editor) {
    const clipboardData = new DataTransfer();
    const cutEvent = new ClipboardEvent("cut", { clipboardData });
    editor.editable.dispatchEvent(cutEvent);
    return clipboardData;
}

test("composer text input: basic rendering when posting a message", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button:text('Send message')");
    await contains(
        ".o-mail-Composer-html .o-we-hint[o-we-hint-text='Send a message to all followers and selected contacts…']"
    );
});

test("composer text input: basic rendering when logging note", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button:text('Log note')");
    await contains(".o-mail-Composer-html .o-we-hint[o-we-hint-text='Log an internal note…']");
});

test("composer text input: basic rendering when linked thread is a discuss.channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "dofus-disco" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer");
    await contains(".o-mail-Composer-html");
});

test("[text composer] composer text input placeholder should contain channel name when thread does not have specific correspondent", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-Composer-html.odoo-editor-editable .o-we-hint[o-we-hint-text='Message #General…']"
    );
});

test.tags("html composer");
test("composer text input placeholder should contain channel name when thread does not have specific correspondent", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-Composer-html.odoo-editor-editable .o-we-hint[o-we-hint-text='Message #General…']"
    );
});

test("[text composer] composer input placeholder in channel thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const subchannelID = pyEnv["discuss.channel"].create({
        name: "ThreadFromGeneral",
        parent_channel_id: channelId,
    });
    await start();
    await openDiscuss(subchannelID);
    await contains(
        ".o-mail-Composer-html.odoo-editor-editable .o-we-hint[o-we-hint-text='Message \"ThreadFromGeneral\"']"
    );
});

test.tags("html composer");
test("composer input placeholder in channel thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const subchannelID = pyEnv["discuss.channel"].create({
        name: "ThreadFromGeneral",
        parent_channel_id: channelId,
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(subchannelID);
    await contains(
        ".o-mail-Composer-html.odoo-editor-editable .o-we-hint[o-we-hint-text='Message \"ThreadFromGeneral\"']"
    );
});

test("[text composer] add an emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "swamp-safari" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('😤')");
    await contains(".o-mail-Composer-html.odoo-editor-editable:text('😤')");
});

test.tags("html composer");
test("add an emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "swamp-safari" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('😤')");
    await contains(".o-mail-Composer-html.odoo-editor-editable:text('😤')");
});

test.tags("html composer");
test("press Enter with emoji suggestions inserts emoji and does not send", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "swamp-safari" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", ":smil");
    await contains(".o-we-SuggestionList .o-navigable:has(:text('😃'))");
    await press("Enter");
    await containsTextInComposer(".o-mail-Composer", "😃");
});

test("[text composer] emojis are auto-substituted from text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", ":)");
    await containsTextInComposer(".o-mail-Composer", "😊");
    await press("Enter");
    await contains(".o-mail-Message-body:text('😊')");
    await insertTextInComposer(".o-mail-Composer", "x'D");
    await containsTextInComposer(".o-mail-Composer", "😂");
    await press("Enter");
    await contains(".o-mail-Message-body:text('😂')");
    await insertTextInComposer(".o-mail-Composer", ">:)");
    await containsTextInComposer(".o-mail-Composer", "😈");
    await press("Enter");
    await contains(".o-mail-Message-body:text('😈')");
});

test.tags("html composer");
test("emojis are auto-substituted from text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", ":)");
    await containsTextInComposer(".o-mail-Composer", "😊");
    await press("Enter");
    await contains(".o-mail-Message-body:text('😊')");
    await insertTextInComposer(".o-mail-Composer", "x'D");
    await containsTextInComposer(".o-mail-Composer", "😂");
    await press("Enter");
    await contains(".o-mail-Message-body:text('😂')");
    await insertTextInComposer(".o-mail-Composer", ">:)");
    await containsTextInComposer(".o-mail-Composer", "😈");
    await press("Enter");
    await contains(".o-mail-Message-body:text('😈')");
});

test.tags("focus required");
test("[text composer] Exiting emoji picker brings the focus back to the Composer textarea", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await contains(".o-mail-Composer-html.odoo-editor-editable:not(:focus)");
    triggerHotkey("Escape");
    await contains(".o-mail-Composer-html.odoo-editor-editable:focus");
});

test.tags("focus required", "html composer");
test("Exiting emoji picker brings the focus back to the Composer textarea", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await contains(".o-mail-Composer-html.odoo-editor-editable:not(:focus)");
    triggerHotkey("Escape");
    await contains(".o-mail-Composer-html.odoo-editor-editable:focus");
});

test("[text composer] add an emoji after some text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "beyblade-room" });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    await containsTextInComposer(".o-mail-Composer", "Blabla");
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤑')");
    await containsTextInComposer(".o-mail-Composer", "Blabla🤑");
});

test.tags("html composer");
test("add an emoji after some text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "beyblade-room" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    await containsTextInComposer(".o-mail-Composer", "Blabla");
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤑')");
    await containsTextInComposer(".o-mail-Composer", "Blabla🤑");
});

test("add emoji replaces (keyboard) text selection", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    await containsTextInComposer(".o-mail-Composer", "Blabla");
    // select all content
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    await tripleClick(editor.editable.querySelector("div.o-paragraph"));
    await animationFrame(); // wait synced with model selection
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤠')");
    await containsTextInComposer(".o-mail-Composer", "🤠");
});

test("Cursor is positioned after emoji after adding it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    await setSelectionInComposer(".o-mail-Composer", { start: 2, end: 2 });
    await animationFrame(); // wait synced with model selection
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤠')");
    await containsTextInComposer(".o-mail-Composer", "Bl🤠abla");
    await contains(".o-EmojiPicker", { count: 0 });
    const expectedPos = 2 + "🤠".length;
    await containsSelectionInComposer(".o-mail-Composer", {
        start: expectedPos,
        end: expectedPos,
    });
});

test.tags("aku-todo"); // AKU TODO: simulated click away not working with web editor
test.skip("selected text is not replaced after cancelling the selection", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Blabla");
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    await tripleClick(editor.editable.querySelector("div.o-paragraph")); // select all content
    await animationFrame(); // wait synced with model selection
    await animationFrame(); // wait synced with model selection
    await click(".o_navbar"); // click away
    await animationFrame(); // wait t-model of Composer input synced with selection reset
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('🤠')");
    await containsTextInComposer(".o-mail-Composer", "Blabla🤠\u00A0");
});

test("Selection is kept when changing channel and going back to original channel", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "channel1" },
        { name: "channel2" },
    ]);
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Foo");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // select all content
    await animationFrame(); // synced with model selection
    await click(":nth-child(2 of .o-mail-DiscussSidebarChannel-container)");
    await click(":nth-child(1 of .o-mail-DiscussSidebarChannel-container)");
    await containsSelectionInComposer(".o-mail-Composer", {
        start: 0,
        end: queryFirst(".o-mail-Composer-html").textContent.length,
    });
});

test("click on emoji button, select emoji, then re-click on button should show emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-skateboarding" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('👺')");
    await click("button[title='Add Emojis']");
    await contains(".o-EmojiPicker");
});

test("keep emoji picker scroll value when re-opening it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-carsurfing" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    // requires an extra delay (give time for auto scroll before setting new value)
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await click("button[title='Add Emojis']");
    await contains(".o-EmojiPicker-content", { count: 0 });
    await click("button[title='Add Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 150 });
});

test("reset emoji picker scroll value after an emoji is picked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-fingerskating" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    // requires an extra delay (give time for auto scroll before setting new value)
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await click(".o-Emoji:text('😎')");
    await click("button[title='Add Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
});

test("keep emoji picker scroll value independent if two or more different emoji pickers are used", async () => {
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([
        { name: "roblox-jaywalking" },
        { name: "Sales" },
    ]);
    setupChatHub({ opened: channelIds });
    await start();
    await click("button[title='Add Emojis']", {
        parent: [".o-mail-ChatWindow:has(:text('Sales'))"],
    });
    // requires an extra delay (give time for auto scroll before setting new value)
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 200);
    await contains(".o-EmojiPicker-content", { scroll: 200 });
    await click("button[title='Add Emojis']", {
        parent: [".o-mail-ChatWindow:has(:text('Sales'))"],
    });
    await contains(".o-EmojiPicker-content", { count: 0 });
    await click("button[title='Add Emojis']", {
        parent: [".o-mail-ChatWindow:has(:text('roblox-jaywalking'))"],
    });
    // requires an extra delay (give time for auto scroll before setting new value)
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await contains(".o-EmojiPicker-content", { scroll: 150 });
    await click("button[title='Add Emojis']", {
        parent: [".o-mail-ChatWindow:has(:text('roblox-jaywalking'))"],
    });
    await click("button[title='Add Emojis']", {
        parent: [".o-mail-ChatWindow:has(:text('Sales'))"],
    });
    await contains(".o-EmojiPicker-content", { scroll: 200 });
});

test("composer text input cleared on message post", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "au-secours-aidez-moi" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "test message");
    await contains(".o-mail-Composer-html:text('test message')");
    await press("Enter");
    await contains(".o-mail-Message");
    await contains(".o-mail-Composer-html", { textContent: "" });
});

test("[text composer] send message only once when ENTER twice quickly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "nether-picnic" });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "test message");
    press("Enter");
    press("Enter");
    await contains(".o-mail-Message");
});

test.tags("html composer");
test("send message only once when ENTER twice quickly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "nether-picnic" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "test message");
    press("Enter");
    press("Enter");
    await contains(".o-mail-Message");
});

test("Show send button in mobile", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    await start();
    await openDiscuss();
    await contains("button.active:text('Notifications')");
    await click("button:text('Channels')");
    await click(".o-mail-NotificationItem-name:text('minecraft-wii-u')");
    await contains(".o-mail-Composer button[title='Send']");
    await contains(".o-mail-Composer button[title='Send'] i.fa-paper-plane-o");
});

test("composer textarea content is retained when changing channel then going back", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "minigolf-galaxy-iv" },
        { name: "epic-shrek-lovers" },
    ]);
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "According to all known laws of aviation,");
    await click("span:text('epic-shrek-lovers')");
    await contains(
        ".o-mail-Composer-html .o-we-hint[o-we-hint-text='Message #epic-shrek-lovers…']"
    );
    await containsTextInComposer(".o-mail-Composer", "");
    await click("span:text('minigolf-galaxy-iv')");
    await containsTextInComposer(".o-mail-Composer", "According to all known laws of aviation,");
    await insertTextInComposer(".o-mail-Composer", "", { replace: true });
    await contains(
        ".o-mail-Composer-html .o-we-hint[o-we-hint-text='Message #minigolf-galaxy-iv…']"
    );
});

test("add an emoji after a partner mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "@Te");
    await click(".o-mail-Composer-suggestion");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@TestPartner\uFEFF\u00A0");
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('😊')");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@TestPartner\uFEFF\u00A0😊");
});

test("pending mentions are kept when toggling composer", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button:text('Send message')");
    await insertTextInComposer(".o-mail-Composer", "@");
    await click(".o-mail-Composer-suggestion strong:text('Mitchell Admin')");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00A0");
    await click("button:text('Send message')");
    await contains(".o-mail-Composer", { count: 0 });
    await click("button:text('Send message')");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body a.o_mail_redirect:text('@Mitchell Admin')");
});

test("composer suggestion should match with input selection", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "Luigi",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer");
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "@");
    await contains(".o-mail-Composer-suggestion:has(:text('Luigi'))");
    await setSelectionInComposer(".o-mail-Composer", {
        start: queryFirst(".o-mail-Composer-html").textContent.length,
        end: queryFirst(".o-mail-Composer-html").textContent.length,
    });
    await contains(".o-mail-Composer-suggestion:has(:text('Luigi'))");
});

test('[text composer] do not post message on channel with "SHIFT-Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Test");
    await contains(".o-mail-Message", { count: 0 });
    triggerHotkey("shift+Enter");
    await tick(); // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", { count: 0 });
});

test.tags("html composer");
test("do not post message on channel with 'SHIFT-Enter' keyboard shortcut", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Test");
    await contains(".o-mail-Message", { count: 0 });
    triggerHotkey("shift+Enter");
    await tick(); // Wait for potential message posting
    await contains(".o-mail-Message", { count: 0 });
});

test('[text composer] post message on channel with "Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Test");
    await contains(".o-mail-Message", { count: 0 });
    await press("Enter");
    await contains(".o-mail-Message");
    await insertTextInComposer(".o-mail-Composer", "test");
    await press("Enter", { isComposing: true });
    await animationFrame();
    await contains(".o-mail-Message");
});

test.tags("html composer");
test("post message on channel with 'Enter' keyboard shortcut", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Test");
    await contains(".o-mail-Message", { count: 0 });
    await press("Enter");
    await contains(".o-mail-Message");
    await insertTextInComposer(".o-mail-Composer", "test");
    await press("Enter", { isComposing: true });
    await animationFrame();
    await contains(".o-mail-Message");
});

test("leave command on channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel.o-active:text('general')");
    await insertTextInComposer(".o-mail-Composer", "/leave");
    await contains(".o-mail-Composer-suggestion strong", { count: 1 });
    triggerHotkey("Enter");
    await containsTextInComposer(".o-mail-Composer", "/leave\u00A0");
    triggerHotkey("Enter");
    await click("button:text(Leave Conversation)");
    await contains(".o-mail-DiscussSidebarChannel:text('general')", { count: 0 });
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
});

test("Can handle leave notification from unknown member", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Dobby" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dobby", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await withUser(userId, () =>
        getService("orm").call("discuss.channel", "action_unfollow", [channelId])
    );
    await contains(".o-discuss-ChannelMember:text('Mitchell Admin')");
    await contains(".o-discuss-ChannelMember:text('Dobby')", { count: 0 });
});

test("leave command on chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck Norris" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel.o-active:text('Chuck Norris')");
    await insertTextInComposer(".o-mail-Composer", "/leave");
    await contains(".o-mail-Composer-suggestion strong", { count: 1 });
    triggerHotkey("Enter");
    await containsTextInComposer(".o-mail-Composer", "/leave\u00A0");
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel:text('Chuck Norris')", { count: 0 });
    await contains(".o-mail-DiscussContent-threadName", { value: "Inbox" });
});

test("Can post suggestions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@Mi");
    await contains(".o-mail-Composer-suggestion strong", { count: 1 });
    triggerHotkey("Enter");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00A0");
    triggerHotkey("Enter");
    await contains(".o-mail-Message .o_mail_redirect");
});

test("[text composer] composer text input placeholder should contain correspondent name when thread has exactly one correspondent", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-Composer-html.odoo-editor-editable .o-we-hint[o-we-hint-text='Message Marc Demo…']"
    );
});

test.tags("html composer");
test("composer text input placeholder should contain correspondent name when thread has exactly one correspondent", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-Composer-html.odoo-editor-editable .o-we-hint[o-we-hint-text='Message Marc Demo…']"
    );
});

test.tags("focus required");
test("[text composer] quick edit last self-message from UP arrow", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "Test-1",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: serverState.partnerId,
            body: "Test-2",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-content:text('Test-1')");
    await contains(".o-mail-Message-content:text('Test-2')");
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    triggerHotkey("ArrowUp");
    await contains(".o-mail-Message .o-mail-Composer-html.odoo-editor-editable:text('Test-2')");
    triggerHotkey("Escape");
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    await contains(".o-mail-Composer-html.odoo-editor-editable:focus");
    // non-empty composer should not trigger quick edit
    let editor = getEditorFromComposerEl(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Shrek");
    await containsTextInComposer(".o-mail-Composer", "Shrek");
    triggerHotkey("ArrowUp");
    // Navigable List relies on useEffect, which behaves with 2 animation frames
    // Wait 2 animation frames to make sure it doesn't show quick edit
    await tick();
    await tick();
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    // ArrowUp for quick edit last stays on last edit message, does not jump to older messages.
    await focus(editor.editable);
    await press(["ctrl", "a"]);
    deleteBackward(editor);
    await containsTextInComposer(".o-mail-Composer", "");
    triggerHotkey("ArrowUp");
    await contains(".o-mail-Message:eq(1) .o-mail-Composer-html");
    editor = getEditorFromComposerEl(".o-mail-Message:eq(1) .o-mail-Composer-html");
    await press(["ctrl", "a"]); // CTRL+A selects all — then type replacement text
    deleteBackward(editor);
    triggerHotkey("ArrowUp");
    await containsTextInComposer(".o-mail-Message .o-mail-Composer", "");
    await press(["ctrl", "a"]); // CTRL+A selects all — then type replacement text
    await insertTextInComposer(".o-mail-Message .o-mail-Composer", "edited message");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content:text('edited message (edited)')");
});

test.tags("focus required", "html composer");
test("quick edit last self-message from UP arrow", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Test",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-content:text('Test')");
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    triggerHotkey("ArrowUp");
    await contains(".o-mail-Message .o-mail-Composer");
    triggerHotkey("Escape");
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    await contains(".o-mail-Composer-html:focus");
    await insertTextInComposer(".o-mail-Composer", "Shrek");
    triggerHotkey("ArrowUp");
    // Navigable List relies on useEffect, which behaves with 2 animation frames
    // Wait 2 animation frames to make sure it doesn't show quick edit
    await tick();
    await tick();
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
});

test("Select composer suggestion via Enter does not send the message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "shrek@odoo.com",
        name: "Shrek",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@Shrek");
    await contains(".o-mail-Composer-suggestion");
    triggerHotkey("Enter");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Shrek\uFEFF\u00A0");
    // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", { count: 0 });
});

test("composer: drop attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    const text2 = new File(["hello, worlduh"], "text2.txt", { type: "text/plain" });
    const text3 = new File(["hello, world"], "text3.txt", { type: "text/plain" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer");
    await contains(".o-mail-Composer-html");
    await contains(".o-Dropzone", { count: 0 });
    await contains(".o-mail-AttachmentContainer", { count: 0 });
    const files = [text, text2];
    await dragenterFiles(".o-mail-Composer-html", files);
    await contains(".o-Dropzone");
    await contains(".o-mail-AttachmentContainer", { count: 0 });
    await dropFiles(".o-Dropzone", files);
    await contains(".o-Dropzone", { count: 0 });
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading)", { count: 2 });
    const extraFiles = [text3];
    await dragenterFiles(".o-mail-Composer-html", extraFiles);
    await dropFiles(".o-Dropzone", extraFiles);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading)", { count: 3 });
});

test("composer: add an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt) .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(
        ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)"
    );
});

test("composer: add an attachment in reply to message in history", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
        is_read: true,
    });
    await start();
    await openDiscuss("mail.box_history");
    await click("[title='Expand']");
    await click(".o-dropdown-item:contains('Reply')");
    await inputFiles(".o-mail-Composer .o_input_file", [text]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt) .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(
        ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)"
    );
});

test("composer: send button is disabled if attachment upload is not finished", async () => {
    const pyEnv = await startServer();
    const { promise, resolve } = Promise.withResolvers();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    onRpcBefore("/mail/attachment/upload", async () => await promise);
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text]);
    await contains(".o-mail-AttachmentContainer.o-isUploading:contains(text.txt)");
    await press("Enter");
    // simulates attachment finishes uploading
    resolve();
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)");
    await contains(".o-mail-AttachmentContainer.o-isUploading", { count: 0 });
    await press("Enter");
});

test("remove an attachment from composer does not need any confirmation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt) .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await click(".o-mail-Attachment-unlink");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentContainer", { count: 0 });
});

test("[text composer] composer: paste attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-html.odoo-editor-editable");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentContainer", { count: 0 });
    await pasteFiles(".o-mail-Composer-html.odoo-editor-editable", [text]);
    await contains(
        ".o-mail-AttachmentList .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)"
    );
});

test.tags("html composer");
test("composer: paste attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-html.odoo-editor-editable");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentContainer", { count: 0 });
    await pasteFiles(".o-mail-Composer-html.odoo-editor-editable", [text]);
    await contains(
        ".o-mail-AttachmentList .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)"
    );
});

test.tags("focus required");
test("Replying on a channel should focus composer initially", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "general",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Expand']");
    await click(".o-dropdown-item:contains('Reply')");
    await contains(".o-mail-Composer-html:focus");
});

test("removing attachment from composer should not delete it from template", async () => {
    patchWithCleanup(MailComposerFormController.prototype, {
        setup() {
            if (!this.env.dialogData) {
                useSubEnv({ dialogData: {} });
            }
            super.setup();
        },
    });
    const pyEnv = await startServer();
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "TemplateAttachment",
        res_model: "mail.template", // Attachment of mail.template
    });
    const templateId = pyEnv["mail.template"].create({
        name: "TestTemplate",
        attachment_ids: [attachmentId],
    });
    registerArchs({
        "mail.compose.message,false,form": `
            <form string="Compose Email" js_class="mail_composer_form">
                <field name="attachment_ids" widget="mail_composer_attachment_list"/>
            </form>`,
    });
    await start();
    const composer = pyEnv["mail.compose.message"].create({
        model: "res.partner",
        attachment_ids: [attachmentId],
    });
    await openFormView("mail.compose.message", composer);
    await contains(".o_field_mail_composer_attachment_list", { text: "TemplateAttachment" });
    await click(".o_field_mail_composer_attachment_list button");
    await contains(".o_field_mail_composer_attachment_list li", { count: 0 });
    const [updatedTemplate] = pyEnv["mail.template"].read([templateId]);
    expect(updatedTemplate.attachment_ids).toEqual([attachmentId], {
        message: "The attachment must remain on the template after being removed from the composer",
    });
});

test("remove an uploading attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    onRpc("/mail/attachment/upload", () => new Promise(() => {})); // simulates uploading indefinitely
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text]);
    await contains(".o-mail-AttachmentContainer.o-isUploading:contains(text.txt)");
    await click(".o-mail-Attachment-unlink");
    await contains(".o-mail-Composer .o-mail-AttachmentContainer", { count: 0 });
});

test("Uploading multiple files in the composer create multiple temporary attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const text1 = new File(["hello, world"], "text1.txt", { type: "text/plain" });
    const text2 = new File(["hello, world"], "text2.txt", { type: "text/plain" });
    onRpc("/mail/attachment/upload", () => new Promise(() => {}));
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text1, text2]);
    await contains(".o-mail-AttachmentContainer.o-isUploading:contains(text1.txt)");
    await contains(".o-mail-AttachmentContainer.o-isUploading:contains(text2.txt)");
    await contains(".o-mail-AttachmentContainer div[title='Uploading']", { count: 2 });
});

test("[technical] does not crash when an attachment is removed before its upload starts", async () => {
    // Uploading multiple files uploads attachments one at a time, this test
    // ensures that there is no crash when an attachment is destroyed before its
    // upload started.
    const pyEnv = await startServer();
    // Promise to block attachment uploading
    const { promise, resolve } = Promise.withResolvers();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const text1 = new File(["hello, world"], "text1.txt", { type: "text/plain" });
    const text2 = new File(["hello, world"], "text2.txt", { type: "text/plain" });
    onRpcBefore("/mail/attachment/upload", async () => await promise);
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text1, text2]);
    await contains(".o-mail-AttachmentContainer.o-isUploading:contains(text1.txt)");
    await click(
        ".o-mail-AttachmentContainer.o-isUploading:contains(text2.txt) .o-mail-Attachment-unlink"
    );
    await contains(".o-mail-AttachmentContainer:contains('text2.txt')", { count: 0 });
    // Simulates the completion of the upload of the first attachment
    resolve();
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text1.txt)");
});

test("Message is sent only once when pressing enter twice in a row", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Hello World!");
    triggerHotkey("Enter");
    triggerHotkey("Enter");
    // weak test, no guarantee that we waited long enough for the potential second message to be posted
    await contains(".o-mail-Message-content:text('Hello World!')");
});

test('[text composer] display canned response suggestions on typing "::"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-Composer-suggestionList .o-open");
    await contains(".o-mail-NavigableList-item:text('hello Hello! How are you?')");
});

test.tags("html composer");
test('display canned response suggestions on typing "::"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-Composer-suggestionList .o-open");
    await contains(".o-mail-NavigableList-item:text('hello Hello! How are you?')");
});

test("[text composer] select a canned response suggestion", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "::");
    await click(".o-mail-Composer-suggestion");
    await containsTextInComposer(".o-mail-Composer", "Hello! How are you?\u00A0");
});

test.tags("html composer");
test("select a canned response suggestion", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "::");
    await click(".o-mail-Composer-suggestion");
    await containsTextInComposer(".o-mail-Composer", "Hello! How are you?\u00A0");
});

test("[text composer] select a canned response suggestion with some text", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "bluhbluh ");
    await containsTextInComposer(".o-mail-Composer", "bluhbluh ");
    await insertTextInComposer(".o-mail-Composer", "::");
    await click(".o-mail-Composer-suggestion");
    await containsTextInComposer(".o-mail-Composer", "bluhbluh\u00A0Hello! How are you?\u00A0");
});

test.tags("html composer");
test("select a canned response suggestion with some text", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "bluhbluh ");
    await containsTextInComposer(".o-mail-Composer", "bluhbluh ");
    await insertTextInComposer(".o-mail-Composer", "::");
    await click(".o-mail-Composer-suggestion");
    await containsTextInComposer(".o-mail-Composer", "bluhbluh\u00A0Hello! How are you?\u00A0");
});

test("add an emoji after a canned response", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await containsTextInComposer(".o-mail-Composer", "");
    await insertTextInComposer(".o-mail-Composer", "::");
    await click(".o-mail-Composer-suggestion");
    await containsTextInComposer(".o-mail-Composer", "Hello! How are you?\u00A0");
    await click("button[title='Add Emojis']");
    await click(".o-Emoji:text('😊')");
    await containsTextInComposer(".o-mail-Composer", "Hello! How are you?\u00A0😊");
});

test("Canned response can be inserted from the bus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-NavigableList-item", { count: 0 });
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    await tripleClick(editor.editable.querySelector("div.o-paragraph"));
    deleteBackward(editor);
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await waitNotifications(["mail.record/insert", (payload) => payload["mail.canned.response"]]);
    await contains(".o-mail-NavigableList-item", { count: 0 });
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-NavigableList-item:text('hello Hello! How are you?')");
});

test("Canned response can be updated from the bus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    const cannedResponseId = pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-NavigableList-item", { count: 1 });
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    await tripleClick(editor.editable.querySelector("div.o-paragraph"));
    deleteBackward(editor);
    pyEnv["mail.canned.response"].write([cannedResponseId], {
        substitution: "Howdy! How are you?",
    });
    await waitNotifications(["mail.record/insert", (payload) => payload["mail.canned.response"]]);
    await contains(".o-mail-NavigableList-item", { count: 0 });
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-NavigableList-item:text('hello Howdy! How are you?')");
});

test("Canned response can be deleted from the bus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    const [cannedResponseId] = pyEnv["mail.canned.response"].create([
        {
            source: "hello",
            substitution: "Hello! How are you?",
        },
        {
            source: "test",
            substitution: "test",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-NavigableList-item", { count: 2 });
    await contains(".o-mail-NavigableList-item:has(:text('hello'))");
    await contains(".o-mail-NavigableList-item:has(:text('test'))");
    const editor = getEditorFromComposerEl(".o-mail-Composer");
    await tripleClick(editor.editable.querySelector("div.o-paragraph"));
    deleteBackward(editor);
    await contains(".o-mail-NavigableList-item", { count: 0 });
    pyEnv["mail.canned.response"].unlink([cannedResponseId]);
    await waitNotifications(["mail.record/insert", (payload) => payload["mail.canned.response"]]);
    await insertTextInComposer(".o-mail-Composer", "::");
    await contains(".o-mail-NavigableList-item", { count: 1 });
    await contains(".o-mail-NavigableList-item:has(:text('test'))");
});

test("Canned response last used changes on posting", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Expelliarmus" });
    const cannedResponseId = pyEnv["mail.canned.response"].create({
        source: "test",
        substitution: "Test a canned response?",
    });
    let cannedResponse = pyEnv["mail.canned.response"].search_read([
        ["id", "=", cannedResponseId],
    ])[0];
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "::");
    await click(".o-mail-NavigableList-item:text('test Test a canned response?')");
    await containsTextInComposer(".o-mail-Composer", "Test a canned response?\u00A0");
    expect(cannedResponse.last_used).toBeEmpty();
    await press("Enter");
    await contains(".o-mail-Message");
    cannedResponse = pyEnv["mail.canned.response"].search_read([["id", "=", cannedResponseId]])[0];
    expect(cannedResponse.last_used).not.toBeEmpty();
});

test("Tab to select of canned response suggestion works in chat window", async () => {
    // This might conflict with focusing next chat window
    const pyEnv = await startServer();
    const channelIds = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Extra" }]);
    pyEnv["mail.canned.response"].create([
        { source: "Hello", substitution: "Hello! How are you?" },
        { source: "Goodbye", substitution: "Goodbye! See you soon!" },
    ]);
    setupChatHub({ opened: channelIds });
    await start();
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatWindow:eq(1) .o-mail-Composer-html:focus"); // wait auto-focus
    await insertTextInComposer(".o-mail-ChatWindow:eq(0) .o-mail-Composer", "::");
    // Assuming the suggestions are displayed in alphabetical order
    await contains(".o-mail-NavigableList-item:text('Goodbye Goodbye! See you soon!')", {
        before: [".o-mail-NavigableList-item:text('Hello Hello! How are you?')"],
    });
    await contains(".o-mail-NavigableList-active:text('Goodbye Goodbye! See you soon!')");
    await triggerHotkey("Tab");
    await contains(".o-mail-NavigableList-active:text('Hello Hello! How are you?')");
    await animationFrame();
    await triggerHotkey("Enter");
    await containsTextInComposer(
        ".o-mail-ChatWindow:eq(0) .o-mail-Composer",
        "Hello! How are you?\u00A0"
    );
});

test('[text composer] can quickly add emoji with ":" keyword', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", ":sweat");
    await contains(".o-we-SuggestionList");
    await click(".o-navigable:text('😅 :sweat_smile:')");
    await containsTextInComposer(".o-mail-Composer", "😅");
    await contains(".o-we-SuggestionList", { count: 0 });
    // check at least 2 chars to trigger it, so that emoji substitution like :p are still easy to use
    await insertTextInComposer(".o-mail-Composer", " :sw");
    await contains(".o-we-SuggestionList");
    await contains(".o-navigable:text('😅 :sweat_smile:')");
    await insertTextInComposer(".o-mail-Composer", ":s", { replace: true });
    await contains(".o-we-SuggestionList", { count: 0 });
});

test.tags("html composer");
test("can quickly add emoji with ':' keyword", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", ":sweat");
    await contains(".o-we-SuggestionList");
    await click(".o-navigable:text('😅 :sweat_smile:')");
    await containsTextInComposer(".o-mail-Composer", "😅");
    await contains(".o-we-SuggestionList", { count: 0 });
    await insertTextInComposer(".o-mail-Composer", " :sw");
    await contains(".o-we-SuggestionList");
    await contains(".o-navigable:text('😅 :sweat_smile:')");
    await insertTextInComposer(".o-mail-Composer", ":s", { replace: true });
    await contains(".o-we-SuggestionList", { count: 0 });
});

test("composer reply-to message is restored on thread change", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Test",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:contains('Reply')");
    await contains(".o-mail-Composer:contains('Replying to')");
    await insertTextInComposer(".o-mail-Composer", "Hello World!");
    await click(".o-mail-DiscussSidebar-item:contains('Inbox')");
    await contains(".o-mail-Message", { count: 0 });
    await click(".o-mail-DiscussSidebar-item:contains('General')");
    await contains(".o-mail-Message");
    await contains(".o-mail-Composer:contains('Replying to')");
    const store = getService("mail.store");
    expect(
        JSON.stringify(
            await getIndexedDB("composer", store["discuss.channel"].get(channelId).composer.localId)
        )
    ).toBe(
        '{"emailAddSignature":true,"replyToMessageId":1,"composerHtml":["markup","<div>Hello World!</div>"],"fromFullComposer":false}'
    );
    // check IndexedDB emptied on message post
    await click(".o-mail-Composer button:enabled[aria-label='Send']");
    await click(".o-mail-Message[data-persistent]:contains(Hello World!)");
    expect(
        await getIndexedDB("composer", store["discuss.channel"].get(channelId).composer.localId)
    ).toBe(undefined);
    // check IndexedDB empty, change thread to force save in local storage if needed (debounced otherwise)
    await click(".o-mail-DiscussSidebar-item:contains('Inbox')");
    await contains(".o-mail-Message", { count: 0 });
    await click(".o-mail-DiscussSidebar-item:contains('General')");
    expect(
        await getIndexedDB("composer", store["discuss.channel"].get(channelId).composer.localId)
    ).toBe(undefined);
});

test("composer reply-to message is restored page reload", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
        name: "General",
    });
    const [messageId_1] = pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "Test-1",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: serverState.partnerId,
            body: "Test-2",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    // simulate composer was replying to 1st message before page reload
    // not taking last message as to not fetch last message data prematurely
    await setIndexedDB(
        "composer",
        `Composer,(mail.thread,discuss.channel AND ${channelId}) OR (undefined)`,
        { replyToMessageId: messageId_1, text: "some text" }
    );
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer:contains('Replying to')");
});

test.tags("html composer");
test("html composer: send a message in a chatter", async () => {
    await startServer();
    await start();
    getService("mail.composer").setHtmlComposer();
    await openFormView("res.partner", serverState.partnerId);
    await click("button:text('Send message')");
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await click(".o-mail-Composer-send:enabled");
    await click(".o-mail-Message[data-persistent]:contains(Hello)");
});

test.tags("html composer");
test("html composer: send a message with styling", async () => {
    await startServer();
    await start();
    getService("mail.composer").setHtmlComposer();
    await openFormView("res.partner", serverState.partnerId);
    await click("button:text('Send message')");
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph"));
    await press("Control+b");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message[data-persistent]:has(strong:text('Hello'))");
});

test("[text composer] send a message end with a space clears the composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Hello ");
    await containsTextInComposer(".o-mail-Composer", "Hello ");
    await press("Enter");
    await containsTextInComposer(".o-mail-Composer", "");
});

test.tags("html composer");
test("send a message end with a space clears the composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "Hello ");
    await containsTextInComposer(".o-mail-Composer", "Hello ");
    await press("Enter");
    await containsTextInComposer(".o-mail-Composer", "");
});

test.tags("html composer");
test("parse link correctly in html composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "www.google.com");
    await containsTextInComposer(".o-mail-Composer", "www.google.com");
    await contains(`.o-mail-Composer-html a:text('www.google.com')`, {
        count: 0,
    });
    await insertTextInComposer(".o-mail-Composer", " ");
    await contains(`.o-mail-Composer-html a[target='_blank']:text('www.google.com')`);
    await press("Enter");
    await contains(`.o-mail-Composer-html:text('www.google.com')`, {
        count: 0,
    });
    await pasteText(getEditorFromComposerEl(".o-mail-Composer"), "www.baidu.com");
    await contains(`.o-mail-Composer-html a[target='_blank']:text('www.baidu.com')`);
});

test.tags("html composer");
test("mention insertion adds FEFF markers for safe cursor placement", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    await insertTextInComposer(".o-mail-Composer", "@admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(".o-mail-Composer", `\uFEFF@Mitchell Admin\uFEFF\u00A0`);
});

test.tags("html composer");
test("mentions can be correctly selected with ctrl+A and deleted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await focus(".o-mail-Composer-html");
    // partner beginning of the message
    await insertTextInComposer(".o-mail-Composer", "@admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00A0");
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00A0Hello");
    await focus(".o-mail-Composer-html");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // FIXME: cannot properly simulate ctrl+A + press Backpace, using tripleclick + custom backward action
    deleteBackward(getEditorFromComposerEl(".o-mail-Composer"));
    await containsTextInComposer(".o-mail-Composer", "");

    //partner in the middle of the message
    await insertTextInComposer(".o-mail-Composer", "Hello @admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(
        ".o-mail-Composer",
        "Hello\u00A0\uFEFF@Mitchell Admin\uFEFF\u00A0"
    );
    await insertTextInComposer(".o-mail-Composer", "nice to meet you!");
    await containsTextInComposer(
        ".o-mail-Composer",
        "Hello\u00A0\uFEFF@Mitchell Admin\uFEFF\u00A0nice to meet you!"
    );
    await focus(".o-mail-Composer-html");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // FIXME: cannot properly simulate ctrl+A + press Backpace, using tripleclick + custom backward action
    deleteBackward(getEditorFromComposerEl(".o-mail-Composer"));
    await containsTextInComposer(".o-mail-Composer", "");

    //partner at the end of the message
    await insertTextInComposer(".o-mail-Composer", "Hello @admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(
        ".o-mail-Composer",
        "Hello\u00A0\uFEFF@Mitchell Admin\uFEFF\u00A0"
    );
    await focus(".o-mail-Composer-html");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // FIXME: cannot properly simulate ctrl+A + press Backpace, using tripleclick + custom backward action
    deleteBackward(getEditorFromComposerEl(".o-mail-Composer"));
    await containsTextInComposer(".o-mail-Composer", "");
});

test.tags("html composer");
test("mentions can be correctly cut with ctrl+A and ctrl+X", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00A0");
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await containsTextInComposer(".o-mail-Composer", "\uFEFF@Mitchell Admin\uFEFF\u00A0Hello");
    await focus(".o-mail-Composer-html");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // FIXME: cannot properly simulate ctrl+A, using tripleclick
    cut(getEditorFromComposerEl(".o-mail-Composer"));
    await containsTextInComposer(".o-mail-Composer", "");

    // partner in the middle of the message
    await insertTextInComposer(".o-mail-Composer", "Hello @admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(
        ".o-mail-Composer",
        "Hello\u00A0\uFEFF@Mitchell Admin\uFEFF\u00A0"
    );
    await insertTextInComposer(".o-mail-Composer", "nice to meet you!");
    await containsTextInComposer(
        ".o-mail-Composer",
        "Hello\u00A0\uFEFF@Mitchell Admin\uFEFF\u00A0nice to meet you!"
    );
    await focus(".o-mail-Composer-html");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // FIXME: cannot properly simulate ctrl+A, using tripleclick
    cut(getEditorFromComposerEl(".o-mail-Composer"));
    await containsTextInComposer(".o-mail-Composer", "");

    // partner at the end of the message
    await insertTextInComposer(".o-mail-Composer", "Hello @admin");
    await click(".o-mail-NavigableList-item:text('Mitchell Admin')");
    await containsTextInComposer(
        ".o-mail-Composer",
        "Hello\u00A0\uFEFF@Mitchell Admin\uFEFF\u00A0"
    );
    await focus(".o-mail-Composer-html");
    await tripleClick(queryFirst(".o-mail-Composer-html .o-paragraph")); // FIXME: cannot properly simulate ctrl+A, using tripleclick
    cut(getEditorFromComposerEl(".o-mail-Composer"));
    await containsTextInComposer(".o-mail-Composer", "");
});
