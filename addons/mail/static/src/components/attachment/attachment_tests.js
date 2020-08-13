odoo.define('mail/static/src/components/attachment/attachment_tests.js', function (require) {
'use strict';

const components = {
    Attachment: require('mail/static/src/components/attachment/attachment.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment', {}, function () {
QUnit.module('attachment_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createAttachmentComponent = async (attachment, otherProps) => {
            const props = Object.assign({ attachmentLocalId: attachment.localId }, otherProps);
            await createRootComponent(this, components.Attachment, {
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

QUnit.test('simplest layout', async function (assert) {
    assert.expect(8);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'none',
        isDownloadable: false,
        isEditable: false,
        showExtension: false,
        showFilename: false,
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Attachment').length,
        1,
        "should have attachment component in DOM"
    );
    const attachmentEl = document.querySelector('.o_Attachment');
    assert.strictEqual(
        attachmentEl.dataset.attachmentLocalId,
        this.env.models['mail.attachment'].find(attachment => attachment.id === 750).localId,
        "attachment component should be linked to attachment store model"
    );
    assert.strictEqual(
        attachmentEl.title,
        "test.txt",
        "attachment should have filename as title attribute"
    );
    assert.strictEqual(
        attachmentEl.querySelectorAll(`:scope .o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    const attachmentImage = document.querySelector(`.o_Attachment_image`);
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
        document.querySelectorAll(`.o_Attachment_details`).length,
        0,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        0,
        "attachment should not have an aside part"
    );
});

QUnit.test('simplest layout + deletable', async function (assert) {
    assert.expect(6);

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('web/image/750')) {
                assert.ok(
                    route.includes('/160x160'),
                    "should fetch image with 160x160 pixels ratio");
                assert.step('fetch_image');
            }
            return this._super(...arguments);
        },
    });
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'none',
        isDownloadable: false,
        isEditable: true,
        showExtension: false,
        showFilename: false
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Attachment').length,
        1,
        "should have attachment component in DOM"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        0,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        1,
        "attachment should have an aside part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItem`).length,
        1,
        "attachment should have only one aside item"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItemUnlink`).length,
        1,
        "attachment should have a delete button"
    );
});

QUnit.test('simplest layout + downloadable', async function (assert) {
    assert.expect(6);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'none',
        isDownloadable: true,
        isEditable: false,
        showExtension: false,
        showFilename: false
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Attachment').length,
        1,
        "should have attachment component in DOM"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        0,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        1,
        "attachment should have an aside part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItem`).length,
        1,
        "attachment should have only one aside item"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItemDownload`).length,
        1,
        "attachment should have a download button"
    );
});

QUnit.test('simplest layout + deletable + downloadable', async function (assert) {
    assert.expect(8);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'none',
        isDownloadable: true,
        isEditable: true,
        showExtension: false,
        showFilename: false
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Attachment').length,
        1,
        "should have attachment component in DOM"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        0,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        1,
        "attachment should have an aside part"
    );
    assert.ok(
        document.querySelector(`.o_Attachment_aside`).classList.contains('o-has-multiple-action'),
        "attachment aside should contain multiple actions"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItem`).length,
        2,
        "attachment should have only two aside items"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItemDownload`).length,
        1,
        "attachment should have a download button"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_asideItemUnlink`).length,
        1,
        "attachment should have a delete button"
    );
});

QUnit.test('layout with card details', async function (assert) {
    assert.expect(3);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'card',
        isDownloadable: false,
        isEditable: false,
        showExtension: false,
        showFilename: false
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        0,
        "attachment should not have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        0,
        "attachment should not have an aside part"
    );
});

QUnit.test('layout with card details and filename', async function (assert) {
    assert.expect(3);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'card',
        isDownloadable: false,
        isEditable: false,
        showExtension: false,
        showFilename: true
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        1,
        "attachment should have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_filename`).length,
        1,
        "attachment should not have its filename shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_extension`).length,
        0,
        "attachment should have its extension shown"
    );
});

QUnit.test('layout with card details and extension', async function (assert) {
    assert.expect(3);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'card',
        isDownloadable: false,
        isEditable: false,
        showExtension: true,
        showFilename: false
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        1,
        "attachment should have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_filename`).length,
        0,
        "attachment should not have its filename shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_extension`).length,
        1,
        "attachment should have its extension shown"
    );
});

QUnit.test('layout with card details and filename and extension', async function (assert) {
    assert.expect(3);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'card',
        isDownloadable: false,
        isEditable: false,
        showExtension: true,
        showFilename: true
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_details`).length,
        1,
        "attachment should have a details part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_filename`).length,
        1,
        "attachment should have its filename shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_extension`).length,
        1,
        "attachment should have its extension shown"
    );
});

QUnit.test('simplest layout with hover details and filename and extension', async function (assert) {
    assert.expect(8);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    await this.createAttachmentComponent(attachment, {
        detailsMode: 'hover',
        isDownloadable: true,
        isEditable: true,
        showExtension: true,
        showFilename: true
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Attachment_details:not(.o_Attachment_imageOverlayDetails)
        `).length,
        0,
        "attachment should not have a details part directly"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_imageOverlayDetails`).length,
        1,
        "attachment should have a details part in the overlay"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_imageOverlay`).length,
        1,
        "attachment should have an image overlay part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_filename`).length,
        1,
        "attachment should have its filename shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_extension`).length,
        1,
        "attachment should have its extension shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_actions`).length,
        1,
        "attachment should have an actions part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        0,
        "attachment should not have an aside element"
    );
});

QUnit.test('auto layout with image', async function (assert) {
    assert.expect(7);

    await this.start();
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });

    await this.createAttachmentComponent(attachment, {
        detailsMode: 'auto',
        isDownloadable: false,
        isEditable: false,
        showExtension: true,
        showFilename: true
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Attachment_details:not(.o_Attachment_imageOverlayDetails)
        `).length,
        0,
        "attachment should not have a details part directly"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_imageOverlayDetails`).length,
        1,
        "attachment should have a details part in the overlay"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_image`).length,
        1,
        "attachment should have an image part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_imageOverlay`).length,
        1,
        "attachment should have an image overlay part"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_filename`).length,
        1,
        "attachment should have its filename shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_extension`).length,
        1,
        "attachment should have its extension shown"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Attachment_aside`).length,
        0,
        "attachment should not have an aside element"
    );
});

QUnit.test('view attachment', async function (assert) {
    assert.expect(3);

    await this.start({
        hasDialog: true,
    });
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });

    await this.createAttachmentComponent(attachment, {
        detailsMode: 'hover',
        isDownloadable: false,
        isEditable: false,
    });
    assert.containsOnce(
        document.body,
        '.o_Attachment_image',
        "attachment should have an image part"
    );
    await afterNextRender(() => document.querySelector('.o_Attachment_image').click());
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

    await this.start({ hasDialog: true });
    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.png",
        id: 750,
        mimetype: 'image/png',
        name: "test.png",
    });

    await this.createAttachmentComponent(attachment, {
        detailsMode: 'hover',
        isDownloadable: false,
        isEditable: false,
    });
    assert.containsOnce(
        document.body,
        '.o_Attachment_image',
        "attachment should have an image part"
    );

    await afterNextRender(() => document.querySelector('.o_Attachment_image').click());
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer',
        "an attachment viewer should have been opened once attachment image is clicked",
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentViewer_headerItemButtonClose').click()
    );
    assert.containsNone(
        document.body,
        '.o_Dialog',
        "attachment viewer should be closed after clicking on close button"
    );
});

});
});
});

});
