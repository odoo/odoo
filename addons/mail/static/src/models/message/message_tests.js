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
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 5));
    assert.notOk(this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    assert.notOk(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.notOk(this.env.models['mail.message'].find(message => message.__mfield_id() === 4000));

    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 100,
        __mfield_model: 'mail.channel',
        __mfield_name: "General",
    });
    const message = this.env.models['mail.message'].create({
        __mfield_attachments: [['insert-and-replace', {
            __mfield_filename: "test.txt",
            __mfield_id: 750,
            __mfield_mimetype: 'text/plain',
            __mfield_name: "test.txt",
        }]],
        __mfield_author: [['insert', {
            __mfield_id: 5,
            __mfield_display_name: "Demo",
        }]],
        __mfield_body: "<p>Test</p>",
        __mfield_date: moment(str_to_datetime("2019-05-05 10:00:00")),
        __mfield_id: 4000,
        __mfield_isNeedaction: true,
        __mfield_isStarred: true,
        __mfield_originThread: [['link', thread]],
    });

    assert.ok(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 5));
    assert.ok(this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    assert.ok(this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750));
    assert.ok(this.env.models['mail.message'].find(message => message.__mfield_id() === 4000));

    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].find(message => message.__mfield_id() === 4000), message);
    assert.strictEqual(message.__mfield_body(), "<p>Test</p>");
    assert.ok(message.__mfield_date() instanceof moment);
    assert.strictEqual(
        moment(message.__mfield_date()).utc().format('YYYY-MM-DD hh:mm:ss'),
        "2019-05-05 10:00:00"
    );
    assert.strictEqual(message.__mfield_id(), 4000);
    assert.strictEqual(message.__mfield_originThread(), this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    assert.ok(
        message.__mfield_threads().includes(this.env.models['mail.thread'].find(thread =>
            thread.__mfield_id() === 100 &&
            thread.__mfield_model() === 'mail.channel'
        ))
    );
    // from partnerId being in needaction_partner_ids
    assert.ok(message.__mfield_threads().includes(this.env.messaging.__mfield_inbox()));
    // from partnerId being in starred_partner_ids
    assert.ok(message.__mfield_threads().includes(this.env.messaging.__mfield_starred()));
    const attachment = this.env.models['mail.attachment'].find(attachment => attachment.__mfield_id() === 750);
    assert.ok(attachment);
    assert.strictEqual(attachment.__mfield_filename(), "test.txt");
    assert.strictEqual(attachment.__mfield_id(), 750);
    assert.notOk(attachment.__mfield_isTemporary());
    assert.strictEqual(attachment.__mfield_mimetype(), 'text/plain');
    assert.strictEqual(attachment.__mfield_name(), "test.txt");
    const channel = this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    );
    assert.ok(channel);
    assert.strictEqual(channel.__mfield_model(), 'mail.channel');
    assert.strictEqual(channel.__mfield_id(), 100);
    assert.strictEqual(channel.__mfield_name(), "General");
    const partner = this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 5);
    assert.ok(partner);
    assert.strictEqual(partner.__mfield_display_name(), "Demo");
    assert.strictEqual(partner.__mfield_id(), 5);
});

});
});
});

});
