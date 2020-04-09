odoo.define('mail.messaging.component.MessageTests', function (require) {
'use strict';

const components = {
    Message: require('mail.messaging.component.Message'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Message', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createMessageComponent = async (message, otherProps) => {
            const MessageComponent = components.Message;
            MessageComponent.env = this.env;
            this.component = new MessageComponent(null, Object.assign({
                messageLocalId: message.localId,
            }, otherProps));
            await this.component.mount(this.widget.el);
            await afterNextRender();
        };
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
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.Message.env;
    },
});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(12);

    await this.start();
    const message = this.env.entities.Message.create({
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessageComponent(message);
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a message component"
    );
    const messageEl = document.querySelector('.o_Message');
    assert.strictEqual(
        messageEl.dataset.messageLocalId,
        this.env.entities.Message.fromId(100).localId,
        "message component should be linked to message store model"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_sidebar`).length,
        1,
        "message should have a sidebar"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_sidebar .o_Message_authorAvatar`).length,
        1,
        "message should have author avatar in the sidebar"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_authorAvatar`).tagName,
        'IMG',
        "message author avatar should be an image"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_authorAvatar`).dataset.src,
        '/web/image/res.partner/7/image_128',
        "message author avatar should GET image of the related partner"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_authorName`).length,
        1,
        "message should display author name"
    );
    assert.strictEqual(
        messageEl.querySelector(`:scope .o_Message_authorName`).textContent,
        "Demo User",
        "message should display correct author name"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_date`).length,
        1,
        "message should display date"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_commands`).length,
        1,
        "message should display list of commands"
    );
    assert.strictEqual(
        messageEl.querySelectorAll(`:scope .o_Message_content`).length,
        1,
        "message should display the content"
    );
    assert.strictEqual(messageEl.querySelector(`:scope .o_Message_content`).innerHTML,
        "<p>Test</p>",
        "message should display the correct content"
    );
});

QUnit.test('delete attachment linked to message', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.entities.Message.create({
        attachment_ids: [{
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
        }],
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessageComponent(message);
    document.querySelector('.o_Attachment_asideItemUnlink').click();
    await afterNextRender();
    assert.notOk(this.env.entities.Attachment.fromId(10));
});

QUnit.test('moderation: moderated channel with pending moderation message (author)', async function (assert) {
    assert.expect(1);

    await this.start();
    const message = this.env.entities.Message.create({
        author_id: [1, "Admin"],
        body: "<p>Test</p>",
        channel_ids: [20],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        res_id: 20,
    });
    await this.createMessageComponent(message);

    assert.strictEqual(
        document.querySelectorAll(`.o_Message_moderationPending.o-author`).length,
        1,
        "should have the message pending moderation"
    );
});

QUnit.test('moderation: moderated channel with pending moderation message (moderator)', async function (assert) {
    assert.expect(9);

    Object.assign(this.data.initMessaging, {
        moderation_channel_ids: [20],
    });
    await this.start();
    const message = this.env.entities.Message.create({
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        channel_ids: [20],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        res_id: 20,
    });
    await this.createMessageComponent(message);
    const messageEl = document.querySelector('.o_Message');
    assert.ok(messageEl, "should display a message");
    assert.containsOnce(messageEl, `.o_Message_moderationSubHeader`,
        "should have the message pending moderation"
    );
    assert.containsNone(messageEl, `.o_Message_checkbox`,
        "should not have the moderation checkbox by default"
    );
    assert.containsN(messageEl, '.o_Message_moderationAction', 5,
        "there should be 5 contextual moderation decisions next to the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-accept',
        "there should be a contextual moderation decision to accept the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-reject',
        "there should be a contextual moderation decision to reject the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-discard',
        "there should be a contextual moderation decision to discard the message"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-allow',
        "there should be a contextual moderation decision to allow the user of the message)"
    );
    assert.containsOnce(messageEl, '.o_Message_moderationAction.o-ban',
        "there should be a contextual moderation decision to ban the user of the message"
    );
    // The actions are tested as part of discuss tests.
});

});
});
});

});
