/** @odoo-module **/

import { link } from '@mail/model/model_field_command';
import {
    afterEach,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_image', {}, function () {
QUnit.module('attachment_image_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { afterEvent, components, env, widget } = res;
            this.afterEvent = afterEvent;
            this.components = components;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('auto layout with image', async function (assert) {
    assert.expect(3);

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
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
});
