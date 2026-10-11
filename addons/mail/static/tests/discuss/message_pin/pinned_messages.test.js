import {
    actionPanel,
    click,
    contains,
    defineMailModels,
    hover,
    openDiscuss,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { disableAnimations } from "@odoo/hoot-mock";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

async function assertPinnedPanelUnpinCount(expectedCount) {
    await contains(".dropdown-item", { text: "Unpin", count: expectedCount });
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await contains(`${actionPanel("Pinned Messages")} .o-mail-Message`, {
        text: "Test pinned message",
    });
    expect(`${actionPanel("Pinned Messages")} button[title='Unpin']`).toHaveCount(expectedCount);
}

test("Pin message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await waitFor(
        `${actionPanel(
            "Pinned Messages"
        )} p:text("This channel doesn't have any pinned messages."):count(1)`
    );
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:text('Pin')");
    await click(".modal-footer button:text('Pin Message')");
    await waitFor(
        `${actionPanel("Pinned Messages")} .o-mail-Message:has(:text('Hello world!')):count(1)`
    );
});

test("Unpin message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await waitFor(`${actionPanel("Pinned Messages")} .o-mail-Message:count(1)`);
    await hover(".o-mail-Thread .o-mail-Message");
    await click(".o-mail-Thread .o-mail-Message [title='Expand']");
    await click(".dropdown-item:text('Unpin')");
    await click(".modal-footer button:text('Unpin Message')");
    await waitForNone(`${actionPanel("Pinned Messages")} .o-mail-Message`);
});

test("Open pinned panel from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await hover(":nth-child(1 of .o-mail-Message)");
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".dropdown-item:text('Pin')");
    await click(".modal-footer button:text('Pin Message')");
    await waitForNone(actionPanel("Pinned Messages"));
    await waitFor(
        `.o-mail-NotificationMessage span:text('${serverState.partnerName} pinned a message to this channel.'):count(1)`
    );
    await waitFor(
        ".o-mail-NotificationMessage-seeAllPins:text('See all pinned messages.'):count(1)"
    );
    await waitFor(
        ".o-mail-NotificationMessage a[data-oe-type='highlight']:text('a message'):count(1)"
    );
    await click(
        ".o-mail-NotificationMessage a[data-oe-type='pin-menu']:text('all pinned messages')"
    );
    await waitFor(`${actionPanel("Pinned Messages")}:count(1)`);
});

test("Jump to message", async () => {
    disableAnimations();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-04-03 08:15:04",
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await click(`${actionPanel("Pinned Messages")} a[role='button']:text('Jump')`);
    await contains(".o-mail-Thread .o-mail-Message-body:text('Hello world!')", { visible: true });
});

test("Jump to message from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:count(21)");
    await hover(":nth-child(1 of .o-mail-Message)");
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".dropdown-item:text('Pin')");
    await click(".modal-footer button:text('Pin Message')");
    await waitFor(".o-mail-NotificationMessage:count(1)");
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click(".o-mail-NotificationMessage a[data-oe-type='highlight']:text('a message')");
    await contains(".o-mail-Thread", { count: 0, scroll: "bottom" });
});

test("can add reactions from pinned panel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2025-10-09 11:15:04",
    });
    await start();
    await openDiscuss(channelId);
    await hover(".o-mail-Message");
    await click(".o-mail-Message-actions [title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button:text('👍')");
    await waitFor(".o-mail-MessageReaction:text('👍 1'):count(1)");
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await hover(`${actionPanel("Pinned Messages")} .o-mail-Message`);
    await click(`${actionPanel("Pinned Messages")} .o-mail-Message [title='Add a Reaction']`);
    await click(".o-mail-QuickReactionMenu button:text('👍')");
    await waitForNone(".o-mail-MessageReaction");
});

test("Guest user cannot see unpin button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        body: "Test pinned message",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start({ authenticateAs: false });
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Test pinned message" });
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await contains(".dropdown-item", { text: "Reply" });
    await contains(".dropdown-item", { text: "Unpin", count: 0 });
    await assertPinnedPanelUnpinCount(0);
});

test("Internal user can see unpin button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Test pinned message",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start();
    await openDiscuss(channelId);
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await assertPinnedPanelUnpinCount(1);
});
