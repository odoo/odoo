/** @odoo-module **/

import { link, replace } from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_image_tests.js');

QUnit.test('auto layout with image', async function (assert) {
    assert.expect(3);

    const { createMessageComponent, messaging } = await start();
    const attachment = messaging.models['Attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });
    const message = messaging.models['Message'].create({
        attachments: link(attachment),
        author: replace(messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);
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
