odoo.define('mail/static/src/components/chatter/chatter_tests', function (require) {
'use strict';

const components = {
    Chatter: require('mail/static/src/components/chatter/chatter.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chatter', {}, function () {
QUnit.module('chatter_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createChatterComponent = async ({ chatter }, otherProps) => {
            const props = Object.assign({ chatterLocalId: chatter.localId }, otherProps);
            await createRootComponent(this, components.Chatter, {
                props,
                target: this.widget.el,
            });
        };

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

QUnit.test('base rendering when chatter has no attachment', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ id: 100 });
    for (let i = 0; i < 60; i++) {
        this.data['mail.message'].records.push({
            model: 'res.partner',
            res_id: 100,
        });
    }
    await this.start();
    const chatter = this.env.models['mail.chatter'].create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_thread`).length,
        1,
        "should have a thread in the chatter"
    );
    assert.strictEqual(
        document.querySelector(`.o_Chatter_thread`).dataset.threadLocalId,
        this.env.models['mail.thread'].find(thread =>
            thread.id === 100 &&
            thread.model === 'res.partner'
        ).localId,
        "thread should have the right thread local id"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "the first 30 messages of thread should be loaded"
    );
});

QUnit.test('base rendering when chatter has no record', async function (assert) {
    assert.expect(7);

    await this.start();
    const chatter = this.env.models['mail.chatter'].create({
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_thread`).length,
        1,
        "should have a thread in the chatter"
    );
    assert.ok(
        chatter.thread.isTemporary,
        "thread should have a temporary thread linked to chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        1,
        "should have a message"
    );
    assert.strictEqual(
        document.querySelector(`.o_Message_content`).textContent,
        "Creating a new record...",
        "should have the 'Creating a new record ...' message"
    );
});

QUnit.test('base rendering when chatter has attachments', async function (assert) {
    assert.expect(3);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['ir.attachment'].records.push(
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: 100,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: 100,
            res_model: 'res.partner',
        }
    );
    await this.start();
    const chatter = this.env.models['mail.chatter'].create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );
});

QUnit.test('show attachment box', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['ir.attachment'].records.push(
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: 100,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: 100,
            res_model: 'res.partner',
        }
    );
    await this.start();
    const chatter = this.env.models['mail.chatter'].create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "should have a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        0,
        "should not have an attachment box in the chatter"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonAttachments`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        1,
        "should have an attachment box in the chatter"
    );
});

QUnit.test('composer show/hide on log note/send message [REQUIRE FOCUS]', async function (assert) {
    assert.expect(10);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.env.models['mail.chatter'].create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonSendMessage`).length,
        1,
        "should have a send message button"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonLogNote`).length,
        1,
        "should have a log note button"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        0,
        "should not have a composer"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should have a composer"
    );
    assert.hasClass(
        document.querySelector('.o_Chatter_composer'),
        'o-focused',
        "composer 'send message' in chatter should have focus just after being displayed"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should still have a composer"
    );
    assert.hasClass(
        document.querySelector('.o_Chatter_composer'),
        'o-focused',
        "composer 'log note' in chatter should have focus just after being displayed"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        0,
        "should have no composer anymore"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should have a composer"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        0,
        "should have no composer anymore"
    );
});

QUnit.test('should not display user notification messages in chatter', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['mail.message'].records = [{
        id: 102,
        message_type: 'user_notification',
        model: 'res.partner',
        res_id: 100,
    }];
    await this.start();
    const chatter = this.env.models['mail.chatter'].create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });

    assert.containsNone(
        document.body,
        '.o_Message',
        "should display no messages"
    );
});

});
});
});

});
