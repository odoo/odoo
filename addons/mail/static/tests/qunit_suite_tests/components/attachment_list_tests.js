/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_list_tests.js');

QUnit.test('simplest layout', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.txt",
        mimetype: 'text/plain',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll('.o_AttachmentList').length,
        1,
        "should have attachment list component in DOM"
    );
    const attachmentEl = document.querySelector('.o_AttachmentList .o_AttachmentCard');
    assert.strictEqual(
        attachmentEl.dataset.id,
        messaging.models['Attachment'].findFromIdentifyingData({ id: messageAttachmentId }).localId,
        "attachment component should be linked to attachment store model"
    );
    assert.strictEqual(
        attachmentEl.title,
        "test.txt",
        "attachment should have filename as title attribute"
    );

    assert.strictEqual(
        attachmentEl.querySelectorAll(`:scope .o_AttachmentCard_image`).length,
        1,
        "attachment should have an image part"
    );
    const attachmentImage = document.querySelector(`.o_AttachmentCard_image`);
    assert.ok(
        attachmentImage.classList.contains('o_image'),
        "attachment should have o_image classname (required for mimetype.scss style)"
    );
    assert.strictEqual(
        attachmentImage.dataset.mimetype,
        'text/plain',
        "attachment should have data-mimetype set (required for mimetype.scss style)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentList_details`).length,
        0,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentList_aside`).length,
        0,
        "attachment should not have an aside part"
    );
});

QUnit.test('simplest layout + editable', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.txt",
        mimetype: 'text/plain',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
        async mockRPC(route, args) {
            if (route.includes('web/image/750')) {
                assert.ok(
                    route.includes('/200x200'),
                    "should fetch image with 200x200 pixels ratio");
                assert.step('fetch_image');
            }
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll('.o_AttachmentList').length,
        1,
        "should have attachment component in DOM"
    );

    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_details`).length,
        1,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_aside`).length,
        1,
        "attachment should have an aside part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_asideItem`).length,
        2,
        "attachment should have two aside item"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_asideItemUnlink`).length,
        1,
        "attachment should have a delete button"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_asideItemDownload`).length,
        1,
        "attachment should have a download button"
    );
});

QUnit.test('layout with card details and filename and extension', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.txt",
        mimetype: 'text/plain',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_details`).length,
        1,
        "attachment should have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentCard_extension`).length,
        1,
        "attachment should have its extension shown"
    );
});

QUnit.test('view attachment', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.png",
        mimetype: 'image/png',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { click, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_AttachmentImage img',
        "attachment should have an image part"
    );
    await click('.o_AttachmentImage');
    assert.containsOnce(
        document.body,
        '.o_Dialog',
        'a dialog should have been opened once attachment image is clicked',
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer',
        'an attachment viewer should have been opened once attachment image is clicked',
    );
});

QUnit.test('close attachment viewer', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.png",
        mimetype: 'image/png',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { click, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_AttachmentImage img',
        "attachment should have an image part"
    );

    await click('.o_AttachmentImage');
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer',
        "an attachment viewer should have been opened once attachment image is clicked",
    );

    await click('.o_AttachmentViewer_headerItemButtonClose');
    assert.containsNone(
        document.body,
        '.o_Dialog',
        "attachment viewer should be closed after clicking on close button"
    );
});

QUnit.test('clicking on the delete attachment button multiple times should do the rpc only once', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.txt",
        mimetype: 'text/plain',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { click, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
        async mockRPC(route, args) {
            if (route === '/mail/attachment/delete') {
                assert.step('attachment_unlink');
            }
        },
    });
    await openDiscuss();

    await click('.o_AttachmentCard_asideItemUnlink');

    await afterNextRender(() => {
        document.querySelector('.o_AttachmentDeleteConfirm_confirmButton').click();
        document.querySelector('.o_AttachmentDeleteConfirm_confirmButton').click();
        document.querySelector('.o_AttachmentDeleteConfirm_confirmButton').click();
    });
    assert.verifySteps(
        ['attachment_unlink'],
        "The unlink method must be called once"
    );
});

QUnit.test('[technical] does not crash when the viewer is closed before image load', async function (assert) {
    /**
     * When images are displayed using `src` attribute for the 1st time, it fetches the resource.
     * In this case, images are actually displayed (fully fetched and rendered on screen) when
     * `<image>` intercepts `load` event.
     *
     * Current code needs to be aware of load state of image, to display spinner when loading
     * and actual image when loaded. This test asserts no crash from mishandling image becoming
     * loaded from being viewed for 1st time, but viewer being closed while image is loading.
     */
    assert.expect(1);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.png",
        mimetype: 'image/png',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { click, openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    await click('.o_AttachmentImage');
    const imageEl = document.querySelector('.o_AttachmentViewer_viewImage');
    await click('.o_AttachmentViewer_headerItemButtonClose');
    // Simulate image becoming loaded.
    let successfulLoad;
    try {
        imageEl.dispatchEvent(new Event('load', { bubbles: true }));
        successfulLoad = true;
    } catch (_err) {
        successfulLoad = false;
    } finally {
        assert.ok(successfulLoad, 'should not crash when the image is loaded');
    }
});

QUnit.test('plain text file is viewable', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.txt",
        mimetype: 'text/plain',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();

    assert.hasClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should be viewable",
    );
});

QUnit.test('HTML file is viewable', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.html",
        mimetype: 'text/html',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    assert.hasClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should be viewable",
    );
});

QUnit.test('ODT file is not viewable', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.odt",
        mimetype: 'application/vnd.oasis.opendocument.text',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    assert.doesNotHaveClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should not be viewable",
    );
});

QUnit.test('DOCX file is not viewable', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.docx",
        mimetype: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    assert.doesNotHaveClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should not be viewable",
    );
});

});
});
