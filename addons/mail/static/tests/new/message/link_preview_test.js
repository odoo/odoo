/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("link preview");

const linkPreviewGifPayload = {
    og_description: "test description",
    og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
    og_mimetype: "image/gif",
    og_title: "Yay Minions GIF - Yay Minions Happiness - Discover & Share GIFs",
    og_type: "video.other",
    source_url: "https://tenor.com/view/yay-minions-happiness-happy-excited-gif-15324023",
};
const linkPreviewCardPayload = {
    og_description: "Description",
    og_title: "Article title",
    og_type: "article",
    source_url: "https://www.odoo.com",
};
const linkPreviewCardImagePayload = {
    og_description: "Description",
    og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
    og_title: "Article title",
    og_type: "article",
    source_url: "https://www.odoo.com",
};
const linkPreviewVideoPayload = {
    og_description: "Description",
    og_image: "https://c.tenor.com/B_zYdea4l-4AAAAC/yay-minions.gif",
    og_title: "video title",
    og_type: "video.other",
    source_url: "https://www.odoo.com",
};
const linkPreviewImagePayload = {
    image_mimetype: "image/jpg",
    source_url:
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Siberischer_tiger_de_edit02.jpg/290px-Siberischer_tiger_de_edit02.jpg",
};

QUnit.test("auto layout with link preview list", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewGifPayload);
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
    assert.containsOnce(document.body, ".o-mail-message .o-mail-link-preview-list");
});

QUnit.test("auto layout with link preview as gif", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewGifPayload);
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
    assert.containsOnce(document.body, ".o-mail-link-preview-image");
});

QUnit.test("simplest card layout", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewCardPayload);
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
    assert.containsOnce(document.body, ".o-mail-link-preview-card");
    assert.containsOnce(document.body, ".o-mail-link-preview-card-title");
    assert.containsOnce(document.body, ".o-mail-link-preview-card-description");
});

QUnit.test("simplest card layout with image", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewCardImagePayload);
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
    assert.containsOnce(document.body, ".o-mail-link-preview-card");
    assert.containsOnce(document.body, ".o-mail-link-preview-card-title");
    assert.containsOnce(document.body, ".o-mail-link-preview-card-description");
    assert.containsOnce(document.body, ".o-mail-link-preview-card-image");
});

QUnit.test("Link preview video layout", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewVideoPayload);
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
    assert.containsOnce(document.body, ".o-mail-link-preview-video");
    assert.containsOnce(document.body, ".o-mail-link-preview-video-title");
    assert.containsOnce(document.body, ".o-mail-link-preview-video-description");
    assert.containsOnce(document.body, ".o-mail-link-preview-video-overlay");
});

QUnit.test("Link preview image layout", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewImagePayload);
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
    assert.containsOnce(document.body, ".o-mail-link-preview-image");
});

QUnit.test("Remove link preview Gif", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewGifPayload);
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
    await click(".o-mail-link-preview-aside");
    assert.containsOnce(document.body, ".o-link-preview-confirm-delete-text");
});

QUnit.test("Remove link preview card", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewCardPayload);
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
    await click(".o-mail-link-preview-aside");
    assert.containsOnce(document.body, ".o-link-preview-confirm-delete-text");
});

QUnit.test("Remove link preview video", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewVideoPayload);
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
    await click(".o-mail-link-preview-aside");
    assert.containsOnce(document.body, ".o-link-preview-confirm-delete-text");
});

QUnit.test("Remove link preview image", async function (assert) {
    const pyEnv = await startServer();
    const linkPreviewId = pyEnv["mail.link.preview"].create(linkPreviewImagePayload);
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
    await click(".o-mail-link-preview-aside");
    assert.containsOnce(document.body, ".o-link-preview-confirm-delete-text");
});
