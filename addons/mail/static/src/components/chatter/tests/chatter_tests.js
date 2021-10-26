/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chatter', {}, function () {
QUnit.module('chatter_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createChatterComponent = async ({ chatter }, otherProps) => {
            const props = Object.assign({ chatterLocalId: chatter.localId }, otherProps);
            await createRootMessagingComponent(this, "Chatter", {
                props,
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { env, widget } = res;
            this.env = env;
            this.widget = widget;
            return res;
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
            body: "not empty",
            model: 'res.partner',
            res_id: 100,
        });
    }
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
        this.messaging.models['mail.thread'].findFromIdentifyingData({
            id: 100,
            model: 'res.partner',
        }).localId,
        "thread should have the right thread local id"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "the first 30 messages of thread should be loaded"
    );
});

QUnit.test('base rendering when chatter has no record', async function (assert) {
    assert.expect(10);

    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
    assert.containsNone(
        document.body,
        '.o_MessageList_loadMore',
        "should not have the 'load more' button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message').click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessageActionList`).length,
        1,
        "should action list in message"
    );
    assert.containsNone(
        document.body,
        '.o_MessageActionList_action',
        "should not have any action in action list of message"
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
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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

QUnit.test('should display subject when subject is not the same as the thread name', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['mail.message'].records.push({
        body: "not empty",
        model: 'res.partner',
        res_id: 100,
        subject: "Salutations, voyageur",
    });
    await this.start();
    this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
        name: "voyageur",
    });
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });

    assert.containsOnce(
        document.body,
        '.o_Message_subject',
        "should display subject of the message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_subject').textContent,
        "Subject: Salutations, voyageur",
        "Subject of the message should be 'Salutations, voyageur'"
    );
});

QUnit.test('should not display subject when subject is the same as the thread name', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['mail.message'].records.push({
        body: "not empty",
        model: 'res.partner',
        res_id: 100,
        subject: "Salutations, voyageur",
    });
    await this.start();
    this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
        name: "Salutations, voyageur",
    });
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });

    assert.containsNone(
        document.body,
        '.o_Message_subject',
        "should not display subject of the message"
    );
});

QUnit.test('should not display user notification messages in chatter', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ id: 100 });
    this.data['mail.message'].records.push({
        id: 102,
        message_type: 'user_notification',
        model: 'res.partner',
        res_id: 100,
    });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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

QUnit.test('post message with "CTRL-Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in chatter"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatterTopbar_buttonSendMessage').click()
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { ctrlKey: true, key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in chatter after posting message from pressing 'CTRL-Enter' in text input of composer"
    );
});

QUnit.test('post message with "META-Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in chatter"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatterTopbar_buttonSendMessage').click()
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter", metaKey: true });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in channel after posting message from pressing 'META-Enter' in text input of composer"
    );
});

QUnit.test('do not post message with "Enter" keyboard shortcut', async function (assert) {
    // Note that test doesn't assert Enter makes a newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterComponent({ chatter });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in chatter"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatterTopbar_buttonSendMessage').click()
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
    document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should still not have any message in mailing channel after pressing 'Enter' in text input of composer"
    );
});

});
});
});
