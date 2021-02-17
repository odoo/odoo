/** @odoo-module **/

import { link } from '@mail/model/model_field_command';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_image', {}, function () {
QUnit.module('attachment_image_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createAttachmentListComponent = async (otherProps) => {
            const props = otherProps;
            await createRootMessagingComponent(this, "AttachmentList", {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('auto layout with image', async function (assert) {
    assert.expect(7);

    await this.start();
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
    await this.createAttachmentListComponent({
        areAttachmentsEditable: false,
        attachmentListLocalId: message.attachmentList.localId,
        attachmentsImageSize: '160x160'
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_AttachmentImage_details:not(.o_AttachmentImage_imageOverlayDetails)
        `).length,
        0,
        "attachment should not have a details part directly"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentImage_imageOverlayDetails`).length,
        1,
        "attachment should have a details part in the overlay"
    );
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
        document.querySelectorAll(`.o_AttachmentImage_filename`).length,
        1,
        "attachment should have its filename shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentImage_extension`).length,
        1,
        "attachment should have its extension shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentImage_aside`).length,
        0,
        "attachment should not have an aside element"
    );
});

QUnit.test('clicking on the delete attachment button multiple times should do the rpc only once', async function (assert) {
    assert.expect(2);
    await this.start({
        async mockRPC(route, args) {
            if (args.method === "unlink" && args.model === "ir.attachment") {
                assert.step('attachment_unlink');
                return;
            }
            return this._super(...arguments);
        },
    });

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });

    await this.createAttachmentImageComponent(attachment, {
        isEditable: true,
    });

    await afterNextRender(() => {
        document.querySelector('.o_AttachmentImage_actionUnlink').click();
    });

    await afterNextRender(() => {
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click();
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click();
        document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click();
    });
    assert.verifySteps(
        ['attachment_unlink'],
        "The unlink method must be called once"
    );
});

});
});
});
