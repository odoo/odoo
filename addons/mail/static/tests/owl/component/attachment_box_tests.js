odoo.define('mail.component.AttachmentBoxTests', function (require) {
"use strict";

const AttachmentBox = require('mail.component.AttachmentBox');
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    dragenterFiles,
    dropFiles,
    pause,
    start: utilsStart,
} = require('mail.messagingTestUtils');

const { file: { createFile } } = require('web.test_utils');

QUnit.module('mail.messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('AttachmentBox', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createThread = async ({ model, id }, { fetchAttachments = false } = {}) => {
            const threadLocalId = this.env.store.dispatch('_createThread', { _model: model, id });
            if (fetchAttachments) {
                await this.env.store.dispatch('fetchThreadAttachments', threadLocalId);
            }
            return threadLocalId;
        };
        this.createAttachmentBox = async (threadLocalId, otherProps) => {
            AttachmentBox.env = this.env;
            this.attachmentBox = new AttachmentBox(null, Object.assign({ threadLocalId }, otherProps));
            await this.attachmentBox.mount(this.widget.el);
        };
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
             let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.attachmentBox) {
            this.attachmentBox.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        delete AttachmentBox.env;
        this.env = undefined;
    }
});

QUnit.test('base empty rendering', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    // attachmentBox needs an existing thread to work
    const threadLocalId = await this.createThread({ model: 'res.partner', id: 100 });
    await this.createAttachmentBox(threadLocalId);
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
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
        0,
        "should not have any attachment"
    );
});

QUnit.test('base non-empty rendering', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [{
                    id: 143,
                    filename: 'Blah.txt',
                    mimetype: 'text/plain',
                    name: 'Blah.txt'
                }, {
                    id: 144,
                    filename: 'Blu.txt',
                    mimetype: 'text/plain',
                    name: 'Blu.txt'
                }];
            }
            return this._super(...arguments);
        }
    });
    // attachmentBox needs an existing thread to work
    const threadLocalId = await this.createThread({ model: 'res.partner', id: 100 }, { fetchAttachments: true });
    await this.createAttachmentBox(threadLocalId);
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

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    // attachmentBox needs an existing thread to work
    const threadLocalId = await this.createThread({ model: 'res.partner', id: 100 }, { fetchAttachments: true });
    await this.createAttachmentBox(threadLocalId);
    const files = [
        await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        }),
    ];
    assert.ok(
        document.querySelectorAll('.o_AttachmentBox').length,
        1,
        "should have an attachment box"
    );

    dragenterFiles(document.querySelector('.o_AttachmentBox'));
    await afterNextRender();
    assert.ok(
        document.querySelector('.o_AttachmentBox_dropZone'),
        "should have a drop zone"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
        0,
        "should have no attachment before files are dropped"
    );

    dropFiles(
        document.querySelector('.o_AttachmentBox_dropZone'),
        files
    );
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
        1,
        "should have 1 attachment in the box after files dropped"
    );

    dragenterFiles(document.querySelector('.o_AttachmentBox'));
    await afterNextRender();
    dropFiles(
        document.querySelector('.o_AttachmentBox_dropZone'),
        [
            await createFile({
                content: 'hello, world',
                contentType: 'text/plain',
                name: 'text2.txt',
            }),
            await createFile({
                content: 'hello, world',
                contentType: 'text/plain',
                name: 'text3.txt',
            })
        ]
    );
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
        3,
        "should have 3 attachments in the box after files dropped"
    );
});

});
});
});
