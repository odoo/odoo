import {
    click,
    contains,
    defineMailModels,
    hover,
    insertText,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { asyncStep, waitForSteps, Command, serverState } from "@web/../tests/web_test_helpers";
import { press } from "@odoo/hoot-dom";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("auto layout with link preview list", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "test description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_mimetype: "image/gif",
        og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
        og_type: "video.other",
        source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message .o-mail-LinkPreviewList");
});

test("auto layout with link preview as gif", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "test description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_mimetype: "image/gif",
        og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
        og_type: "video.other",
        source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewImage");
});

test("simplest card layout", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewCard");
    await contains(".o-mail-LinkPreviewCard h6", { text: "Article title" });
    await contains(".o-mail-LinkPreviewCard p", { text: "Description" });
});

test("simplest card layout with image", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewCard");
    await contains(".o-mail-LinkPreviewCard h6", { text: "Article title" });
    await contains(".o-mail-LinkPreviewCard p", { text: "Description" });
    await contains(".o-mail-LinkPreviewCard img");
});

test("Link preview video layout", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_title: "video title",
        og_type: "video.other",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewVideo");
    await contains(".o-mail-LinkPreviewVideo h6", { text: "video title" });
    await contains(".o-mail-LinkPreviewVideo p", { text: "Description" });
    await contains(".o-mail-LinkPreviewVideo-overlay");
});

test("Link preview image layout", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewImage");
});

test("Remove link preview Gif", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "test description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_mimetype: "image/gif",
        og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
        og_type: "video.other",
        source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewImage button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewImage", { count: 0 });
});

test("Remove link preview card", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewCard button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewCard", { count: 0 });
});

test("Remove link preview video", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_title: "video title",
        og_type: "video.other",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewVideo button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewVideo", { count: 0 });
});

test("Remove link preview image", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewImage button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewImage", { count: 0 });
});

test("No crash on receiving link preview of non-known message", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    const messageId = pyEnv["mail.message"].create({
        body: "https://make-link-preview.com",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    const messageLinkPreviewId = pyEnv["mail.message.link.preview"].create({
        message_id: messageId,
        link_preview_id: linkPreviewId,
    });
    await start();
    await openDiscuss();
    rpc("/mail/link_preview", { message_id: messageId });
    rpc("/mail/link_preview/hide", { message_link_preview_ids: [messageLinkPreviewId] });
    expect(true).toBe(true, { message: "no assertions" });
});

test("Squash the message and the link preview when the link preview is an image and the link is the only text in the message", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "<a href='linkPreviewLink'>http://linkPreview</a>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewImage");
    await contains(".o-mail-Message-bubble", { count: 0 });
});

test("Link preview and message should not be squashed when the link preview is not an image", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "<a href='linkPreviewLink'>http://linkPreview</a>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-bubble");
});

test("Link preview and message should not be squashed when there is more than the link in the message", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "<a href='linkPreviewLink'>http://linkPreview</a> not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId })],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-bubble");
});

test("Sending message with link preview URL should show a link preview card", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "https://make-link-preview.com");
    await press("Enter");
    await contains(".o-mail-LinkPreviewCard");
});

test("Delete all link previews at once", async () => {
    const pyEnv = await startServer();
    const [linkPreviewId_1, linkPreviewId_2] = pyEnv["mail.link.preview"].create([
        {
            og_description: "Description",
            og_title: "Article title 1",
            og_type: "article",
            source_url: "https://www.odoo.com",
        },
        {
            image_mimetype: "image/jpg",
            source_url:
                "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
        },
    ]);
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        message_link_preview_ids: [
            Command.create({ link_preview_id: linkPreviewId_1 }),
            Command.create({ link_preview_id: linkPreviewId_2 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewCard button[aria-label='Remove']");
    await click(".modal-footer button", { text: "Delete all previews" });
    await contains(".o-mail-LinkPreviewCard", { count: 0 });
    await contains(".o-mail-LinkPreviewImage", { count: 0 });
});

test("link preview request is only made when message contains URL", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Sales" });
    onRpcBefore("/mail/link_preview", () => asyncStep("/mail/link_preview"));
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello, this message does not contain any link");
    await press("Enter");
    await contains(".o-mail-Message", {
        text: "Hello, this message does not contain any link",
    });
    await waitForSteps([]);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-NavigableList-item", { text: "Sales" });
    await press("Enter");
    await contains(".o-mail-Message", { text: "Sales" });
    await waitForSteps([]);
    await insertText(".o-mail-Composer-input", "https://www.odoo.com");
    await press("Enter");
    await waitForSteps(["/mail/link_preview"]);
});

test("youtube and gdrive videos URL are embed", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [linkPreviewId_1, linkPreviewId_2] = pyEnv["mail.link.preview"].create([
        {
            og_title: "vokoscreenNG-2024-08-22_13-56-37.mkv",
            og_type: "article",
            source_url: "https://drive.google.com/file/d/195a8fSNxwmkfs9sDS7OCB2nX03iFr21P/view",
        },
        {
            og_title: "Cinematic",
            og_type: "video",
            source_url: "https://www.youtube.com/watch?v=9bZkp7q19f0",
        },
    ]);
    pyEnv["mail.message"].create([
        {
            body: "GDrive video preview",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId_1 })],
        },
        {
            body: "YT video preview",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId_2 })],
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewVideo[data-provider=google-drive] .fa-play");
    await contains(
        "iframe[data-src='https://drive.google.com/file/d/195a8fSNxwmkfs9sDS7OCB2nX03iFr21P/preview']",
        { parent: [".o-mail-LinkPreviewVideo[data-provider=google-drive]"] }
    );
    await click(".o-mail-LinkPreviewVideo[data-provider=youtube] .fa-play");
    await contains("iframe[data-src='https://www.youtube.com/embed/9bZkp7q19f0?autoplay=1']", {
        parent: [".o-mail-LinkPreviewVideo[data-provider=youtube]"],
    });
});

test("Internal user can't delete others preview", async () => {
    const pyEnv = await startServer();
    const [linkPreviewId_1, linkPreviewId_2] = pyEnv["mail.link.preview"].create([
        {
            og_description: "Description",
            og_title: "Article title 1",
            og_type: "article",
            source_url: "https://www.odoo.com/",
        },
        {
            og_description: "Description",
            og_title: "Article title 2",
            og_type: "article",
            source_url: "https://example.com",
        },
    ]);
    const partnerId = pyEnv["res.partner"].create({ name: "Test User" });
    const userId = pyEnv["res.users"].create({
        partner_id: partnerId,
        login: "testUser",
        password: "testUser",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "wololo",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    pyEnv["mail.message"].create([
        {
            body: "msg-1",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            author_id: serverState.partnerId,
            message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId_1 })],
        },
        {
            body: "msg-2",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            author_id: partnerId,
            message_link_preview_ids: [Command.create({ link_preview_id: linkPreviewId_2 })],
        },
    ]);
    await start({ authenticateAs: pyEnv["res.users"].read(userId)[0] });
    await openDiscuss(channelId);
    await hover(".o-mail-Message:contains('msg-2') .o-mail-LinkPreviewCard");
    await contains(
        ".o-mail-Message:contains('msg-2') .o-mail-LinkPreviewCard button[aria-label='Remove']"
    );
    await hover(".o-mail-Message:contains('msg-1') .o-mail-LinkPreviewCard");
    await contains(
        ".o-mail-Message:contains('msg-1') .o-mail-LinkPreviewCard button[aria-label='Remove']",
        { count: 0 }
    );
});
