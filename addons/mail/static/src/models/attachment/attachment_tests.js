odoo.define('mail/static/src/models/attachment/attachment_tests.js', function (require) {
'use strict';

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('attachment', {}, function () {
QUnit.module('attachment_tests.js', {
    beforeEach() {
        beforeEach(this);

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

QUnit.test('create (txt)', async function (assert) {
    assert.expect(9);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(this.env.models['mail.attachment'].find(attachment => attachment.id === 750), attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isTemporary);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
});

QUnit.test('displayName', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment.displayName, "test.txt");
});

QUnit.test('extension', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment.extension, 'txt');
});

QUnit.test('fileType', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment =>
        attachment.id === 750)
    );
    assert.strictEqual(attachment.fileType, 'text');
});

QUnit.test('isTextFile', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.ok(attachment.isTextFile);
});

QUnit.test('isViewable', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));

    const attachment = this.env.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.id === 750));
    assert.ok(attachment.isViewable);
});

});
});
});

});
