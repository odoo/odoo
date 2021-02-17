/** @odoo-module **/

import AttachmentLinkPreview from '@mail/components/attachment_link_preview/attachment_link_preview';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} from '@mail/utils/test_utils';

const components = { AttachmentLinkPreview };

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_link_preview', {}, function () {
QUnit.module('attachment_link_preview_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createAttachmentLinkPreviewComponent = async (attachment, otherProps) => {
            const props = Object.assign({ attachmentLocalId: attachment.localId }, otherProps);
            await createRootComponent(this, components.AttachmentLinkPreview, {
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

QUnit.test('Link preview card is not viewable', async function(assert) {
    assert.expect(1);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "https://tenor.com/view/gato-gif-18532922",
        id: 750,
        mimetype: 'application/octet-stream',
        name: "https://tenor.com/view/gato-gif-18532922",
        url: "https://tenor.com/view/gato-gif-18532922",
        linkPreview: [{
            "type": "video.other",
            "url": "https://tenor.com/view/gato-gif-18532922",
            "title": "Gato GIF - Gato - Discover & Share GIFs",
            "image_url": "https://media1.tenor.com/images/fd1edd05b33d229e6e845c473042c088/tenor.gif?itemid=18532922",
            "description": "Click to view the GIF"
        }]
    });
    await this.createAttachmentLinkPreviewComponent(attachment);

    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview',
        "Attachment is a link preview"
    );
});

QUnit.test('simplest layout', async function (assert) {
    assert.expect(4);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "https://tenor.com/view/gato-gif-18532922",
        id: 750,
        mimetype: 'application/octet-stream',
        name: "https://tenor.com/view/gato-gif-18532922",
        url: "https://tenor.com/view/gato-gif-18532922",
        linkPreview: {
            "type": "video.other",
            "url": "https://tenor.com/view/gato-gif-18532922",
            "title": "Gato GIF - Gato - Discover & Share GIFs",
            "image_url": "https://media1.tenor.com/images/fd1edd05b33d229e6e845c473042c088/tenor.gif?itemid=18532922",
            image: "/mail/image/2",
            "description": "Click to view the GIF",
        },
    });
    await this.createAttachmentLinkPreviewComponent(attachment);

    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview',
        "should have attachment link preview in DOM"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview_title',
        "Should display the page title"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview_linkImage',
        "attachment should have an image part"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview_excerpt',
        "attachment should show the link description"
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
        filename: "https://tenor.com/view/gato-gif-18532922",
        id: 750,
        mimetype: 'application/octet-stream',
        name: "https://tenor.com/view/gato-gif-18532922",
        url: "https://tenor.com/view/gato-gif-18532922",
        linkPreview: [{
            "type": "video.other",
            "url": "https://tenor.com/view/gato-gif-18532922",
            "title": "Gato GIF - Gato - Discover & Share GIFs",
            "image_url": "https://media1.tenor.com/images/fd1edd05b33d229e6e845c473042c088/tenor.gif?itemid=18532922",
            "description": "Click to view the GIF"
        }]
    });
    await this.createAttachmentLinkPreviewComponent(attachment);

    await afterNextRender(() => {
        document.querySelector('.o_AttachmentLinkPreview_asideItemUnlink').click();
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
