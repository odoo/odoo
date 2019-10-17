odoo.define('mail.component.MessageTests', function (require) {
'use strict';

const Message = require('mail.component.Message');
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    pause,
    start: startUtils,
} = require('mail.owl.testUtils');

const testUtils = require('web.test_utils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Message', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createMessage = async (messageLocalId, otherProps) => {
            const env = await this.widget.call('env', 'get');
            this.message = new Message(env, {
                messageLocalId,
                ...otherProps
            });
            await this.message.mount(this.widget.$el[0]);
        };
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { store, widget } = await startUtils({
                ...params,
                data: this.data,
            });
            this.store = store;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.message) {
            this.message.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.store = undefined;
    }
});

QUnit.test('default', async function (assert) {
    assert.expect(12);

    await this.start();
    const messageLocalId = this.store.dispatch('_createMessage', {
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessage(messageLocalId);
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message')
            .length,
        1,
        "should display a message component");
    const message = document.querySelector('.o_Message');
    assert.strictEqual(
        message.dataset.messageLocalId,
        'mail.message_100',
        "message component should be linked to message store model");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_sidebar`)
            .length,
        1,
        "message should have a sidebar");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_sidebar
                .o_Message_authorAvatar`)
            .length,
        1,
        "message should have author avatar in the sidebar");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_sidebar
                .o_Message_authorAvatar`)
            .tagName,
        'IMG',
        "message author avatar should be an image");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_sidebar
                .o_Message_authorAvatar`)
            .dataset
            .src,
        '/web/image/res.partner/7/image_128',
        "message author avatar should GET image of the related partner");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_authorName`)
            .length,
        1,
        "message should display author name");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_authorName`)
            .textContent,
        "Demo User",
        "message should display correct author name");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_date`)
            .length,
        1,
        "message should display date");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_commands`)
            .length,
        1,
        "message should display list of commands");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_content`)
            .length,
        1,
        "message should display the content");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_content`)
            .innerHTML,
        "<p>Test</p>",
        "message should display the correct content");
});

QUnit.test('deleteAttachment', async function (assert) {
    assert.expect(2);

    await this.start();
    const messageLocalId = this.store.dispatch('_createMessage', {
        attachment_ids: [{
            filename: "BLAH.jpg",
            id: 10,
            name: "BLAH",
        }],
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        id: 100,
    });
    await this.createMessage(messageLocalId);
    await testUtils.nextTick();
    document.querySelector('.o_Attachment_asideItemUnlink').click();
    await testUtils.nextTick();
    assert.ok(!this.store.state.attachments['ir.attachment_10']);
    assert.ok(!this.store.state.messages[messageLocalId].attachmentLocalIds['ir.attachment_10']);
});

});
});
});
