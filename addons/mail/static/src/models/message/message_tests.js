odoo.define('mail/static/src/models/message/message_tests.js', function (require) {
'use strict';

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

const { str_to_datetime } = require('web.time');

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('message', {}, function () {
QUnit.module('message_tests.js', {
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

QUnit.test('create', async function (assert) {
    assert.expect(31);

    await this.start();
    assert.notOk(this.env.models['mail.partner'].findFromIdentifyingData({ id: 5 }));
    assert.notOk(this.env.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    }));
    assert.notOk(this.env.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.notOk(this.env.models['mail.message'].findFromIdentifyingData({ id: 4000 }));

    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'mail.channel',
        name: "General",
    });
    const message = this.env.models['mail.message'].create({
        attachments: [['insert-and-replace', {
            filename: "test.txt",
            id: 750,
            mimetype: 'text/plain',
            name: "test.txt",
        }]],
        author: [['insert', { id: 5, display_name: "Demo" }]],
        body: "<p>Test</p>",
        date: moment(str_to_datetime("2019-05-05 10:00:00")),
        id: 4000,
        isNeedaction: true,
        isStarred: true,
        originThread: [['link', thread]],
    });

    assert.ok(this.env.models['mail.partner'].findFromIdentifyingData({ id: 5 }));
    assert.ok(this.env.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    }));
    assert.ok(this.env.models['mail.attachment'].findFromIdentifyingData({ id: 750 }));
    assert.ok(this.env.models['mail.message'].findFromIdentifyingData({ id: 4000 }));

    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 4000 }), message);
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.ok(message.date instanceof moment);
    assert.strictEqual(
        moment(message.date).utc().format('YYYY-MM-DD hh:mm:ss'),
        "2019-05-05 10:00:00"
    );
    assert.strictEqual(message.id, 4000);
    assert.strictEqual(message.originThread, this.env.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    }));
    assert.ok(
        message.threads.includes(this.env.models['mail.thread'].findFromIdentifyingData({
            id: 100,
            model: 'mail.channel',
        }))
    );
    // from partnerId being in needaction_partner_ids
    assert.ok(message.threads.includes(this.env.messaging.inbox));
    // from partnerId being in starred_partner_ids
    assert.ok(message.threads.includes(this.env.messaging.starred));
    const attachment = this.env.models['mail.attachment'].findFromIdentifyingData({ id: 750 });
    assert.ok(attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isTemporary);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
    const channel = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 100,
        model: 'mail.channel',
    });
    assert.ok(channel);
    assert.strictEqual(channel.model, 'mail.channel');
    assert.strictEqual(channel.id, 100);
    assert.strictEqual(channel.name, "General");
    const partner = this.env.models['mail.partner'].findFromIdentifyingData({ id: 5 });
    assert.ok(partner);
    assert.strictEqual(partner.display_name, "Demo");
    assert.strictEqual(partner.id, 5);
});

QUnit.test('message without body should be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "" should be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p></p>" should be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<p></p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p><br></p>" should be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<p><br></p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p><br/></p>" should be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<p><br/></p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test(String.raw`message with body "<p>\n</p>" should be considered empty`, async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<p>\n</p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test(String.raw`message with body "<p>\r\n\r\n</p>" should be considered empty`, async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<p>\r\n\r\n</p>", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test('message with body "<p>   </p>  " should be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<p>   </p>  ", id: 11 });
    assert.ok(message.isEmpty);
});

QUnit.test(`message with body "<img src=''>" should not be considered empty`, async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "<img src=''>", id: 11 });
    assert.notOk(message.isEmpty);
});

QUnit.test('message with body "test" should not be considered empty', async function (assert) {
    assert.expect(1);
    await this.start();
    const message = this.env.models['mail.message'].create({ body: "test", id: 11 });
    assert.notOk(message.isEmpty);
});

});
});
});

});
