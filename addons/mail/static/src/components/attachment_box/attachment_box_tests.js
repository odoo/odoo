odoo.define('mail/static/src/components/attachment_box/attachment_box_tests.js', function (require) {
"use strict";

const components = {
    AttachmentBox: require('mail/static/src/components/attachment_box/attachment_box.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    dragenterFiles,
    dropFiles,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const { file: { createFile } } = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_box', {}, function () {
QUnit.module('attachment_box_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createAttachmentBoxComponent = async (thread, otherProps) => {
            const AttachmentBoxComponent = components.AttachmentBox;
            AttachmentBoxComponent.env = this.env;
            this.component = new AttachmentBoxComponent(null, Object.assign({
                threadLocalId: thread.localId,
            }, otherProps));
            await this.component.mount(this.widget.el);
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
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        delete components.AttachmentBox.env;
        this.env = undefined;
    },
});

QUnit.test('base empty rendering', async function (assert) {
    assert.expect(4);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
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
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
        0,
        "should not have any attachment"
    );
});

QUnit.test('base non-empty rendering', async function (assert) {
    assert.expect(6);

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                assert.step('ir.attachment/search_read');
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
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await thread.fetchAttachments();
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

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    const thread = this.env.models['mail.thread'].create({
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
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
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
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
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
        document.querySelectorAll(`.o_AttachmentBox .o_Attachment`).length,
        3,
        "should have 3 attachments in the box after files dropped"
    );
});

QUnit.test('view attachments', async function (assert) {
    assert.expect(7);

    await this.start({
        hasDialog: true,
    });
    const thread = this.env.models['mail.thread'].create({
        attachments: [
            ['insert', {
                id: 143,
                filename: 'Blah.txt',
                mimetype: 'text/plain',
                name: 'Blah.txt'
            }],
            ['insert', {
                id: 144,
                filename: 'Blu.txt',
                mimetype: 'text/plain',
                name: 'Blu.txt'
            }]
        ],
        id: 100,
        model: 'res.partner',
    });
    const firstAttachment = this.env.models['mail.attachment'].find(
        attachment => attachment.id === 143
    );
    await this.createAttachmentBoxComponent(thread);

    await afterNextRender(() =>
        document.querySelector(`
            .o_Attachment[data-attachment-local-id="${firstAttachment.localId}"]
            .o_Attachment_image 
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


});
});
});

});
