/** @odoo-module **/

import { beforeEach, } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('attachment', {}, function () {
QUnit.module('attachment_tests.js', { beforeEach });

QUnit.test('create (txt)', async function (assert) {
    assert.expect(9);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }), attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isUploading);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
});

QUnit.test('displayName', async function (assert) {
    assert.expect(5);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment.displayName, "test.txt");
});

QUnit.test('extension', async function (assert) {
    assert.expect(5);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment.extension, 'txt');
});

QUnit.test('fileType', async function (assert) {
    assert.expect(5);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['mail.attachment'].findFromIdentifyingData({
        id: 750,
    }));
    assert.strictEqual(attachment.fileType, 'text');
});

QUnit.test('isTextFile', async function (assert) {
    assert.expect(5);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.ok(attachment.isTextFile);
});

QUnit.test('isViewable', async function (assert) {
    assert.expect(5);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['mail.attachment'].create({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.ok(attachment.isViewable);
});

});
});
});
