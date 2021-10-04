/** @odoo-module **/

import { link } from '@mail/model/model_field_command';

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_list', {}, function () {
QUnit.module('attachment_list_tests.js', {
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

QUnit.test('simplest layout', async function (assert) {
    assert.expect(8);

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

    assert.strictEqual(
        document.querySelectorAll('.o_AttachmentList').length,
        1,
        "should have attachment list component in DOM"
    );
    const attachmentEl = document.querySelector('.o_AttachmentList .o_AttachmentCard');
    assert.strictEqual(
        attachmentEl.dataset.id,
        this.messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }).localId,
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

    const { createMessageComponent } = await this.start({
        async mockRPC(route, args) {
            if (route.includes('web/image/750')) {
                assert.ok(
                    route.includes('/200x200'),
                    "should fetch image with 200x200 pixels ratio");
                assert.step('fetch_image');
            }
            return this._super(...arguments);
        },
    });
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

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

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

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

    const { createMessageComponent } = await this.start({
        hasDialog: true,
    });
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

    assert.containsOnce(
        document.body,
        '.o_AttachmentImage img',
        "attachment should have an image part"
    );
    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
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

    const { createMessageComponent } = await this.start({ hasDialog: true });
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

    assert.containsOnce(
        document.body,
        '.o_AttachmentImage img',
        "attachment should have an image part"
    );

    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
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

QUnit.test('clicking on the delete attachment button multiple times should do the rpc only once', async function (assert) {
    assert.expect(2);

    const { createMessageComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/mail/attachment/delete') {
                assert.step('attachment_unlink');
                return;
            }
            return this._super(...arguments);
        },
    });
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

    await afterNextRender(() => {
        document.querySelector('.o_AttachmentCard_asideItemUnlink').click();
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

    const { createMessageComponent } = await this.start({ hasDialog: true });
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
    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
    const imageEl = document.querySelector('.o_AttachmentViewer_viewImage');
    await afterNextRender(() =>
        document.querySelector('.o_AttachmentViewer_headerItemButtonClose').click()
    );
    // Simulate image becoming loaded.
    let successfulLoad;
    try {
        imageEl.dispatchEvent(new Event('load', { bubbles: true }));
        successfulLoad = true;
    } catch (err) {
        successfulLoad = false;
    } finally {
        assert.ok(successfulLoad, 'should not crash when the image is loaded');
    }
});

QUnit.test('plain text file is viewable', async function (assert) {
    assert.expect(1);

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);

    assert.hasClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should be viewable",
    );
});

QUnit.test('HTML file is viewable', async function (assert) {
    assert.expect(1);

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.html",
        id: 750,
        mimetype: 'text/html',
        name: "test.html",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);
    assert.hasClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should be viewable",
    );
});

QUnit.test('ODT file is not viewable', async function (assert) {
    assert.expect(1);

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.odt",
        id: 750,
        mimetype: 'application/vnd.oasis.opendocument.text',
        name: "test.odt",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);
    assert.doesNotHaveClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should not be viewable",
    );
});

QUnit.test('DOCX file is not viewable', async function (assert) {
    assert.expect(1);

    const { createMessageComponent } = await this.start();
    const attachment = this.messaging.models['mail.attachment'].create({
        filename: "test.docx",
        id: 750,
        mimetype: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        name: "test.docx",
    });
    const message = this.messaging.models['mail.message'].create({
        attachments: link(attachment),
        author: link(this.messaging.currentPartner),
        body: "<p>Test</p>",
        id: 100,
    });
    await createMessageComponent(message);
    assert.doesNotHaveClass(
        document.querySelector('.o_AttachmentCard'),
        'o-viewable',
        "should not be viewable",
    );
});

});
});
});
