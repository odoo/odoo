/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('attachment_tests.js');

QUnit.test('create (txt)', async function (assert) {
    assert.expect(9);

    const { messaging } = await start();
    assert.notOk(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['Attachment'].insert({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }), attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isUploading);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
});

QUnit.test('displayName', async function (assert) {
    assert.expect(5);

    const { messaging } = await start();
    assert.notOk(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['Attachment'].insert({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment.displayName, "test.txt");
});

QUnit.test('extension', async function (assert) {
    assert.expect(5);

    const { messaging } = await start();
    assert.notOk(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['Attachment'].insert({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment.extension, 'txt');
});

QUnit.test('fileType', async function (assert) {
    assert.expect(5);

    const { messaging } = await start();
    assert.notOk(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['Attachment'].insert({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['Attachment'].findFromIdentifyingData({
        id: 750,
    }));
    assert.ok(attachment.isText);
});

QUnit.test('isTextFile', async function (assert) {
    assert.expect(5);

    const { messaging } = await start();
    assert.notOk(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['Attachment'].insert({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.ok(attachment.isText);
});

QUnit.test('isViewable', async function (assert) {
    assert.expect(5);

    const { messaging } = await start();
    assert.notOk(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));

    const attachment = messaging.models['Attachment'].insert({
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    assert.ok(attachment);
    assert.ok(messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.strictEqual(attachment, messaging.models['Attachment'].findFromIdentifyingData({ id: 750 }));
    assert.ok(attachment.isViewable);
});

});
});
