/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("link preview");

QUnit.test("auto layout with link preview list", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "test description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_mimetype: "image/gif",
        og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
        og_type: "video.other",
        source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message .o-LinkPreviewList");
});

QUnit.test("auto layout with link preview as gif", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "test description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_mimetype: "image/gif",
        og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
        og_type: "video.other",
        source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-LinkPreviewImage");
});

QUnit.test("simplest card layout", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-LinkPreviewCard");
    assert.containsOnce($, ".o-LinkPreviewCard:contains(Article title)");
    assert.containsOnce($, ".o-LinkPreviewCard:contains(Description)");
});

QUnit.test("simplest card layout with image", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-LinkPreviewCard");
    assert.containsOnce($, ".o-LinkPreviewCard:contains(Article title)");
    assert.containsOnce($, ".o-LinkPreviewCard:contains(Description)");
    assert.containsOnce($, ".o-LinkPreviewCard img");
});

QUnit.test("Link preview video layout", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_title: "video title",
        og_type: "video.other",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-LinkPreviewVideo");
    assert.containsOnce($, ".o-LinkPreviewVideo:contains(video title)");
    assert.containsOnce($, ".o-LinkPreviewVideo:contains(Description)");
    assert.containsOnce($, ".o-LinkPreviewVideo-overlay");
});

QUnit.test("Link preview image layout", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-LinkPreviewImage");
});

QUnit.test("Remove link preview Gif", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "test description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_mimetype: "image/gif",
        og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
        og_type: "video.other",
        source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-LinkPreviewImage button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
});

QUnit.test("Remove link preview card", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_title: "Article title",
        og_type: "article",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-LinkPreviewCard button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
});

QUnit.test("Remove link preview video", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        og_description: "Description",
        og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
        og_title: "video title",
        og_type: "video.other",
        source_url: "https://www.odoo.com",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-LinkPreviewVideo button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
});

QUnit.test("Remove link preview image", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create({
        image_mimetype: "image/jpg",
        source_url:
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
    });
    const channelId = pyEnv["mail.channel"].create({ name: "wololo" });
    pyEnv["mail.message"].create({
        body: "not empty",
        link_preview_ids: [linkPreviewId],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-LinkPreviewImage button[aria-label='Remove']");
    assert.containsOnce($, "p:contains(Do you really want to delete this preview?)");
});
