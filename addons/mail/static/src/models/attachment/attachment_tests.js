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
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));

    const attachment = this.env.models['mail.attachment'].create({
        __mfield_filename: "test.txt",
        __mfield_id: 750,
        __mfield_mimetype: 'text/plain',
        __mfield_name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750), attachment);
    assert.strictEqual(attachment.__mfield_filename(), "test.txt");
    assert.strictEqual(attachment.__mfield_id(), 750);
    assert.notOk(attachment.__mfield_isTemporary());
    assert.strictEqual(attachment.__mfield_mimetype(), 'text/plain');
    assert.strictEqual(attachment.__mfield_name(), "test.txt");
});

QUnit.test('displayName', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));

    const attachment = this.env.models['mail.attachment'].create({
        __mfield_filename: "test.txt",
        __mfield_id: 750,
        __mfield_mimetype: 'text/plain',
        __mfield_name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment.__mfield_displayName(), "test.txt");
});

QUnit.test('extension', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));

    const attachment = this.env.models['mail.attachment'].create({
        __mfield_filename: "test.txt",
        __mfield_id: 750,
        __mfield_mimetype: 'text/plain',
        __mfield_name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment.__mfield_extension(), 'txt');
});

QUnit.test('fileType', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));

    const attachment = this.env.models['mail.attachment'].create({
        __mfield_filename: "test.txt",
        __mfield_id: 750,
        __mfield_mimetype: 'text/plain',
        __mfield_name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment =>
        attachment.__mfield_id() === 750)
    );
    assert.strictEqual(attachment.__mfield_fileType(), 'text');
});

QUnit.test('isTextFile', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));

    const attachment = this.env.models['mail.attachment'].create({
        __mfield_filename: "test.txt",
        __mfield_id: 750,
        __mfield_mimetype: 'text/plain',
        __mfield_name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.ok(attachment.__mfield_isTextFile());
});

QUnit.test('isViewable', async function (assert) {
    assert.expect(5);

    await this.start();
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));

    const attachment = this.env.models['mail.attachment'].create({
        __mfield_filename: "test.txt",
        __mfield_id: 750,
        __mfield_mimetype: 'text/plain',
        __mfield_name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.strictEqual(attachment, this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.ok(attachment.__mfield_isViewable());
});

});
});
});

});
