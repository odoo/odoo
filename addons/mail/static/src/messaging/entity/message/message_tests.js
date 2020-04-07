odoo.define('mail.messaging.entity.MessageTests', function (require) {
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
QUnit.module('Message', {
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

QUnit.test('create', async function (assert) {
    assert.expect(31);

    await this.start();
    assert.notOk(this.env.entities.Partner.fromId(5));
    assert.notOk(this.env.entities.Thread.channelFromId(100));
    assert.notOk(this.env.entities.Attachment.fromId(750));
    assert.notOk(this.env.entities.Message.fromId(4000));

    const message = this.env.entities.Message.create({
        attachment_ids: [{
            filename: "test.txt",
            id: 750,
            mimetype: 'text/plain',
            name: "test.txt",
        }],
        author_id: [5, "Demo"],
        body: "<p>Test</p>",
        channel_ids: [100],
        date: "2019-05-05 10:00:00",
        id: 4000,
        model: 'mail.channel',
        needaction_partner_ids: [2, 3],
        record_name: "General",
        starred_partner_ids: [3, 4],
        res_id: 100,
    });

    assert.ok(this.env.entities.Partner.fromId(5));
    assert.ok(this.env.entities.Thread.channelFromId(100));
    assert.ok(this.env.entities.Attachment.fromId(750));
    assert.ok(this.env.entities.Message.fromId(4000));

    assert.ok(message);
    assert.strictEqual(this.env.entities.Message.fromId(4000), message);
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.ok(message.date instanceof moment);
    assert.strictEqual(
        moment(message.date).utc().format('YYYY-MM-DD hh:mm:ss'),
        "2019-05-05 10:00:00"
    );
    assert.strictEqual(message.id, 4000);
    assert.strictEqual(message.originThread, this.env.entities.Thread.channelFromId(100));
    assert.ok(
        message.allThreads.includes(this.env.entities.Thread.channelFromId(100))
    );
    // from partnerId being in needaction_partner_ids
    assert.ok(message.allThreads.includes(this.env.entities.Thread.mailboxFromId('inbox')));
    // from partnerId being in starred_partner_ids
    assert.ok(message.allThreads.includes(this.env.entities.Thread.mailboxFromId('starred')));
    const attachment = this.env.entities.Attachment.fromId(750);
    assert.ok(attachment);
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isTemporary);
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
    const channel = this.env.entities.Thread.channelFromId(100);
    assert.ok(channel);
    assert.strictEqual(channel.model, 'mail.channel');
    assert.strictEqual(channel.id, 100);
    assert.strictEqual(channel.name, "General");
    const partner = this.env.entities.Partner.fromId(5);
    assert.ok(partner);
    assert.strictEqual(partner.display_name, "Demo");
    assert.strictEqual(partner.id, 5);
});

});
});
});

});
