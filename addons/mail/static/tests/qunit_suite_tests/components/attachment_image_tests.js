/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_image_tests.js');

QUnit.test('auto layout with image', async function (assert) {
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
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentImage img`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentImage_imageOverlay`).length,
        1,
        "attachment should have an image overlay part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentImage_aside`).length,
        0,
        "attachment should not have an aside element"
    );
});

});
});
