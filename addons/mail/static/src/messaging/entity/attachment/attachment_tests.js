odoo.define('mail.messaging.entity.AttachmentTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('entity', {}, function () {
QUnit.module('Attachment', {
    beforeEach() {
        utilsBeforeEach(this);
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
        this.env = undefined;
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
    },
});

QUnit.test('create (txt)', async function (assert) {
    assert.expect(9);

    await this.start();
    assert.notOk(this.env.entities.Attachment.fromId(750));

    const attachment = this.env.entities.Attachment.create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.strictEqual(this.env.entities.Attachment.fromId(750), attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isTemporary);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
});

QUnit.test('displayName', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.entities.Attachment.fromId(750));

    const attachment = this.env.entities.Attachment.create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment, this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment.displayName, "test.txt");
});

QUnit.test('extension', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.entities.Attachment.fromId(750));

    const attachment = this.env.entities.Attachment.create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment, this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment.extension, 'txt');
});

QUnit.test('fileType', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.entities.Attachment.fromId(750));

    const attachment = this.env.entities.Attachment.create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment, this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment.fileType, 'text');
});

QUnit.test('isTextFile', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.entities.Attachment.fromId(750));

    const attachment = this.env.entities.Attachment.create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment, this.env.entities.Attachment.fromId(750));
    assert.ok(attachment.isTextFile);
});

QUnit.test('isViewable', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.entities.Attachment.fromId(750));

    const attachment = this.env.entities.Attachment.create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.strictEqual(attachment, this.env.entities.Attachment.fromId(750));
    assert.ok(attachment.isViewable);
});

});
});
});

});
