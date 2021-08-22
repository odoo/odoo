/** @odoo-module **/

import { insert, insertAndReplace, link } from '@mail/model/model_field_command';
import { beforeEach } from '@mail/utils/test_utils';

import { str_to_datetime } from 'web.time';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('message', {}, function () {
QUnit.module('message_tests.js', { beforeEach });

QUnit.test('create', async function (assert) {
    assert.expect(31);

    const { messaging } = await this.start();
    assert.notOk(messaging.models['mail.partner'].findFromIdentifyingData({ id: 5 }));
    assert.notOk(messaging.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    }));
    assert.notOk(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.notOk(messaging.models['mail.message'].findFromIdentifyingData({ id: 4000 }));

    const thread = messaging.models['mail.thread'].create({
        id: 100,
        model: 'mail.channel',
        name: "General",
    });
    const message = messaging.models['mail.message'].create({
        attachments: insertAndReplace({
            filename: "test.txt",
            id: 750,
            mimetype: 'text/plain',
            name: "test.txt",
        }),
        author: insert({ id: 5, display_name: "Demo" }),
        body: "<p>Test</p>",
        date: moment(str_to_datetime("2019-05-05 10:00:00")),
        id: 4000,
        isNeedaction: true,
        isStarred: true,
        originThread: link(thread),
    });

    assert.ok(messaging.models['mail.partner'].findFromIdentifyingData({ id: 5 }));
    assert.ok(messaging.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    }));
    assert.ok(messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.ok(messaging.models['mail.message'].findFromIdentifyingData({ id: 4000 }));

    assert.ok(message);
    assert.strictEqual(messaging.models['mail.message'].findFromIdentifyingData({ id: 4000 }), message);
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.ok(message.date instanceof moment);
    assert.strictEqual(
        moment(message.date).utc().format('YYYY-MM-DD hh:mm:ss'),
        "2019-05-05 10:00:00"
    );
    assert.strictEqual(message.id, 4000);
    assert.strictEqual(message.originThread, messaging.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    }));
    assert.ok(
        message.threads.includes(messaging.models['mail.thread'].findFromIdentifyingData({
            id: 100,
            model: 'mail.channel',
        }))
    );
    // from partnerId being in needaction_partner_ids
    assert.ok(message.threads.includes(messaging.inbox));
    // from partnerId being in starred_partner_ids
    assert.ok(message.threads.includes(messaging.starred));
    const attachment = messaging.models['mail.attachment'].findFromIdentifyingData({ id: 750 });
    assert.ok(attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isUploading);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
    const channel = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    });
    assert.ok(channel);
    assert.strictEqual(channel.model, 'mail.channel');
    assert.strictEqual(channel.id, 100);
    assert.strictEqual(channel.name, "General");
    const partner = messaging.models['mail.partner'].findFromIdentifyingData({ id: 5 });
    assert.ok(partner);
    assert.strictEqual(partner.display_name, "Demo");
    assert.strictEqual(partner.id, 5);
});

QUnit.test('message without body should be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "" should be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p></p>" should be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<p></p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p><br></p>" should be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<p><br></p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p><br/></p>" should be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<p><br/></p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test(String.raw`message with body "<p>\n</p>" should be considered empty`, async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<p>\n</p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test(String.raw`message with body "<p>\r\n\r\n</p>" should be considered empty`, async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<p>\r\n\r\n</p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p>   </p>  " should be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<p>   </p>  ", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test(`message with body "<img src=''>" should not be considered empty`, async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "<img src=''>", id: 11 });
    assert.notOk(message.isEmpty);
});

QUnit.test('message with body "test" should not be considered empty', async function (assert) {
    assert.expect(1);
    const { messaging } = await this.start();
    const message = messaging.models['mail.message'].create({ body: "test", id: 11 });
    assert.notOk(message.isEmpty);
});

});
});
});
