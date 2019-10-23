odoo.define('mail.store.GettersTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('store', {}, function () {
QUnit.module('Getters', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { store, widget } = await utilsStart({
                ...params,
                data: this.data,
            });
            this.store = store;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        this.store = undefined;
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
    }
});

QUnit.test('attachmentDisplayName', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.notOk(this.store.state.attachments['ir.attachment_750']);

    const attachmentLocalId = this.store.dispatch('createAttachment', {
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const attachment = this.store.state.attachments[attachmentLocalId];
    assert.ok(attachment);
    assert.strictEqual(this.store.getters.attachmentDisplayName(attachment.localId), "test.txt");
});

QUnit.test('attachmentExtension', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.notOk(this.store.state.attachments['ir.attachment_750']);

    const attachmentLocalId = this.store.dispatch('createAttachment', {
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const attachment = this.store.state.attachments[attachmentLocalId];
    assert.ok(attachment);
    assert.strictEqual(this.store.getters.attachmentExtension(attachment.localId), "txt");
});

QUnit.test('attachmentFileType', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.notOk(this.store.state.attachments['ir.attachment_750']);

    const attachmentLocalId = this.store.dispatch('createAttachment', {
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const attachment = this.store.state.attachments[attachmentLocalId];
    assert.ok(attachment);
    assert.strictEqual(this.store.getters.attachmentFileType(attachment.localId), 'text');
});

QUnit.test('isAttachmentTextFile', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.notOk(this.store.state.attachments['ir.attachment_750']);

    const attachmentLocalId = this.store.dispatch('createAttachment', {
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const attachment = this.store.state.attachments[attachmentLocalId];
    assert.ok(attachment);
    assert.ok(this.store.getters.isAttachmentTextFile(attachment.localId));
});

QUnit.test('isAttachmentViewable', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.notOk(this.store.state.attachments['ir.attachment_750']);

    const attachmentLocalId = this.store.dispatch('createAttachment', {
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const attachment = this.store.state.attachments[attachmentLocalId];
    assert.ok(attachment);
    assert.ok(this.store.getters.isAttachmentViewable(attachment.localId));
});

});
});
});
