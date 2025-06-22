/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("link preview");

QUnit.test("auto layout with link preview list", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message .o-mail-LinkPreviewList");
});

QUnit.test("auto layout with link preview as gif", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewImage");
});

QUnit.test("simplest card layout", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewCard");
    await contains(".o-mail-LinkPreviewCard h6", { text: "Article title" });
    await contains(".o-mail-LinkPreviewCard p", { text: "Description" });
});

QUnit.test("simplest card layout with image", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewCard");
    await contains(".o-mail-LinkPreviewCard h6", { text: "Article title" });
    await contains(".o-mail-LinkPreviewCard p", { text: "Description" });
    await contains(".o-mail-LinkPreviewCard img");
});

QUnit.test("Link preview video layout", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewVideo");
    await contains(".o-mail-LinkPreviewVideo h6", { text: "video title" });
    await contains(".o-mail-LinkPreviewVideo p", { text: "Description" });
    await contains(".o-mail-LinkPreviewVideo-overlay");
});

QUnit.test("Link preview image layout", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewImage");
});

QUnit.test("Remove link preview Gif", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-LinkPreviewImage button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewImage", { count: 0 });
});

QUnit.test("Remove link preview card", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-LinkPreviewCard button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewCard", { count: 0 });
});

QUnit.test("Remove link preview video", async () => {
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
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-LinkPreviewVideo button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewVideo", { count: 0 });
});

QUnit.test("Remove link preview image", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-LinkPreviewImage button[aria-label='Remove']");
    await contains("p", { text: "Do you really want to delete this preview?" });
    await click(".modal-footer button", { text: "Delete" });
    await contains(".o-mail-LinkPreviewImage", { count: 0 });
});

QUnit.test("No crash on receiving link preview of non-known message", async (assert) => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    const messageId = pyEnv["mail.message"].create({
        body: "https://make-link-preview.com",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { env, openDiscuss } = await start();
    openDiscuss();
    env.services.rpc("/mail/link_preview", { message_id: messageId });
    assert.ok(true);
    env.services.rpc("/mail/link_preview/delete", { link_preview_ids: [linkPreviewId] });
    assert.ok(true);
});

QUnit.test(
    "Squash the message and the link preview when the link preview is an image and the link is the only text in the message",
    async () => {
        const pyEnv = await startServer();
        const linkPreviewId = pyEnv["mail.link.preview"].create({
            image_mimetype: "image/jpg",
            source_url:
                "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
        });
        const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
        pyEnv["mail.message"].create({
            body: "<a href='linkPreviewLink'>http://linkPreview</a>",
            link_preview_ids: [linkPreviewId],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-LinkPreviewImage");
        await contains(".o-mail-Message-bubble", { count: 0 });
    }
);

QUnit.test(
    "Link preview and message should not be squashed when the link preview is not an image",
    async () => {
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
            link_preview_ids: [linkPreviewId],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Message-bubble");
    }
);

QUnit.test(
    "Link preview and message should not be squashed when there is more than the link in the message",
    async () => {
        const pyEnv = await startServer();
        const linkPreviewId = pyEnv["mail.link.preview"].create({
            image_mimetype: "image/jpg",
            source_url:
                "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
        });
        const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
        pyEnv["mail.message"].create({
            body: "<a href='linkPreviewLink'>http://linkPreview</a> not empty",
            link_preview_ids: [linkPreviewId],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Message-bubble");
    }
);

QUnit.test("Sending message with link preview URL should show a link preview card", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "https://make-link-preview.com");
    await click("button:not([disabled])", { text: "Send" });
    await contains(".o-mail-LinkPreviewCard");
});

QUnit.test("Delete all link previews at once", async () => {
    const pyEnv = await startServer();
    const linkPreviewIds = pyEnv["mail.link.preview"].create([
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
        link_preview_ids: linkPreviewIds,
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-LinkPreviewCard button[aria-label='Remove']");
    await click(".modal-footer button", { text: "Delete all previews" });
    await contains(".o-mail-LinkPreviewCard", { count: 0 });
    await contains(".o-mail-LinkPreviewImage", { count: 0 });
});

QUnit.test("Delete link preview of a non-editable (email) message", async () => {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_title: "Article title 1",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        model: "discuss.channel",
        res_id: channelId,
        message_type: "email",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-LinkPreviewCard button[aria-label='Remove']");
});
