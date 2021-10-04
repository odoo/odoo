/** @odoo-module **/

import { insert } from '@mail/model/model_field_command';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    dragenterFiles,
    dropFiles,
    start,
} from '@mail/utils/test_utils';

import { file } from 'web.test_utils';

const { createFile } = file;

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_box', {}, function () {
QUnit.module('attachment_box_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createAttachmentBoxComponent = async (thread, otherProps) => {
            const chatter = this.messaging.models['mail.chatter'].insert({
                id: 1,
                threadId: thread.id,
                threadModel: thread.model,
            });
            const props = {
                chatterLocalId: chatter.localId,
                ...otherProps,
            };
            await createRootMessagingComponent(this, "AttachmentBox", {
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

QUnit.test('base empty rendering', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createAttachmentBoxComponent(thread);
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox`).length,
        1,
        "should have an attachment box"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox_buttonAdd`).length,
        1,
        "should have a button add"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_FileUploader_input`).length,
        1,
        "should have a file input"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        0,
        "should not have any attachment"
    );
});

QUnit.test('base non-empty rendering', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['ir.attachment'].records.push(
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: 100,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: 100,
            res_model: 'res.partner',
        }
    );
    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                assert.step('ir.attachment/search_read');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createAttachmentBoxComponent(thread);
    assert.verifySteps(
        ['ir.attachment/search_read'],
        "should have fetched attachments"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox`).length,
        1,
        "should have an attachment box"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox_buttonAdd`).length,
        1,
        "should have a button add"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_FileUploader_input`).length,
        1,
        "should have a file input"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_attachmentBox_attachmentList`).length,
        1,
        "should have an attachment list"
    );
});

QUnit.test('attachment box: drop attachments', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await thread.fetchAttachments();
    await this.createAttachmentBoxComponent(thread);
    const files = [
        await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        }),
    ];
    assert.strictEqual(
        document.querySelectorAll('.o_AttachmentBox').length,
        1,
        "should have an attachment box"
    );

    await afterNextRender(() =>
        dragenterFiles(document.querySelector('.o_AttachmentBox'))
    );
    assert.ok(
        document.querySelector('.o_AttachmentBox_dropZone'),
        "should have a drop zone"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        0,
        "should have no attachment before files are dropped"
    );

    await afterNextRender(() =>
        dropFiles(
            document.querySelector('.o_AttachmentBox_dropZone'),
            files
        )
    );

    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        1,
        "should have 1 attachment in the box after files dropped"
    );

    await afterNextRender(() =>
        dragenterFiles(document.querySelector('.o_AttachmentBox'))
    );
    const file1 = await createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text2.txt',
    });
    const file2 = await createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text3.txt',
    });
    await afterNextRender(() =>
        dropFiles(
            document.querySelector('.o_AttachmentBox_dropZone'),
            [file1, file2]
        )
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        3,
        "should have 3 attachments in the box after files dropped"
    );
});

QUnit.test('view attachments', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start({
        hasDialog: true,
    });
    const thread = this.messaging.models['mail.thread'].create({
        attachments: [
            insert({
                id: 143,
                mimetype: 'text/plain',
                name: 'Blah.txt'
            }),
            insert({
                id: 144,
                mimetype: 'text/plain',
                name: 'Blu.txt'
            })
        ],
        id: 100,
        model: 'res.partner',
    });
    const firstAttachment = this.messaging.models['mail.attachment'].findFromIdentifyingData({ id: 143 });
    await this.createAttachmentBoxComponent(thread);

    await afterNextRender(() =>
        document.querySelector(`
            .o_AttachmentCard[data-id="${firstAttachment.localId}"]
            .o_AttachmentCard_image
        `).click()
    );
    assert.containsOnce(
        document.body,
        '.o_Dialog',
        "a dialog should have been opened once attachment image is clicked",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer',
        "an attachment viewer should have been opened once attachment image is clicked",
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentViewer_name').textContent,
        'Blah.txt',
        "attachment viewer iframe should point to clicked attachment",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer_buttonNavigationNext',
        "attachment viewer should allow to see next attachment",
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentViewer_buttonNavigationNext').click()
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentViewer_name').textContent,
        'Blu.txt',
        "attachment viewer iframe should point to next attachment of attachment box",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer_buttonNavigationNext',
        "attachment viewer should allow to see next attachment",
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentViewer_buttonNavigationNext').click()
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentViewer_name').textContent,
        'Blah.txt',
        "attachment viewer iframe should point anew to first attachment",
    );
});

QUnit.test('remove attachment should ask for confirmation', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        attachments: insert({
            id: 143,
            mimetype: 'text/plain',
            name: 'Blah.txt',
        }),
        id: 100,
        model: 'res.partner',
    });
    await this.createAttachmentBoxComponent(thread);
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should have an attachment",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard_asideItemUnlink',
        "attachment should have a delete button"
    );

    await afterNextRender(() => document.querySelector('.o_AttachmentCard_asideItemUnlink').click());
    assert.containsOnce(
        document.body,
        '.o_AttachmentDeleteConfirmDialog',
        "A confirmation dialog should have been opened"
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentDeleteConfirmDialog_mainText').textContent,
        `Do you really want to delete "Blah.txt"?`,
        "Confirmation dialog should contain the attachment delete confirmation text"
    );

    // Confirm the deletion
    await afterNextRender(() => document.querySelector('.o_AttachmentDeleteConfirmDialog_confirmButton').click());
    assert.containsNone(
        document.body,
        '.o_AttachmentCard',
        "should no longer have an attachment",
    );
});

});
});
});
