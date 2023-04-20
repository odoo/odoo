/** @odoo-module **/

import { click, nextAnimationFrame, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("link preview");

QUnit.test("auto layout with link preview list", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message .o-mail-LinkPreviewList");
});

QUnit.test("auto layout with link preview as gif", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-LinkPreviewImage");
});

QUnit.test("simplest card layout", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-LinkPreviewCard");
    assert.containsOnce($, ".o-mail-LinkPreviewCard:contains(Article title)");
    assert.containsOnce($, ".o-mail-LinkPreviewCard:contains(Description)");
});

QUnit.test("simplest card layout with image", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-LinkPreviewCard");
    assert.containsOnce($, ".o-mail-LinkPreviewCard:contains(Article title)");
    assert.containsOnce($, ".o-mail-LinkPreviewCard:contains(Description)");
    assert.containsOnce($, ".o-mail-LinkPreviewCard img");
});

QUnit.test("Link preview video layout", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-LinkPreviewVideo");
    assert.containsOnce($, ".o-mail-LinkPreviewVideo:contains(video title)");
    assert.containsOnce($, ".o-mail-LinkPreviewVideo:contains(Description)");
    assert.containsOnce($, ".o-mail-LinkPreviewVideo-overlay");
});

QUnit.test("Link preview image layout", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-LinkPreviewImage");
});

QUnit.test("Remove link preview Gif", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewImage button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
    await click(".modal-footer button:contains(Ok)");
    assert.containsNone($, ".o-mail-LinkPreviewImage");
});

QUnit.test("Remove link preview card", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewCard button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
    await click(".modal-footer button:contains(Ok)");
    assert.containsNone($, ".o-mail-LinkPreviewCard");
});

QUnit.test("Remove link preview video", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewVideo button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
    await click(".modal-footer button:contains(Ok)");
    assert.containsNone($, ".o-mail-LinkPreviewVideo");
});

QUnit.test("Remove link preview image", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-LinkPreviewImage button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
    await click(".modal-footer button:contains(Ok)");
    assert.containsNone($, ".o-mail-LinkPreviewImage");
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
    await openDiscuss();
    env.services.rpc("/mail/link_preview", { message_id: messageId });
    await nextAnimationFrame();
    assert.ok(true);
});

QUnit.test(
    "Squash the message and the link preview when the link preview is an image and the link is the only text in the message",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.containsNone($, ".o-mail-Message-bubble");
    }
);

QUnit.test(
    "Link preview and message should not be squashed when the link preview is not an image",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message-bubble");
    }
);

QUnit.test(
    "Link preview and message should not be squashed when there is more than the link in the message",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message-bubble");
    }
);
