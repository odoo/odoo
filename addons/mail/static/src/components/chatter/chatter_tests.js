odoo.define('mail/static/src/components/chatter/chatter_tests', function (require) {
'use strict';

const components = {
    Chatter: require('mail/static/src/components/chatter/chatter.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chatter', {}, function () {
QUnit.module('chatter_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createChatterComponent = async ({ chatter }, otherProps) => {
            const ChatterComponent = components.Chatter;
            ChatterComponent.env = this.env;
            this.component = new ChatterComponent(
                null,
                Object.assign({ chatterLocalId: chatter.localId }, otherProps)
            );
            await afterNextRender(() => this.component.mount(this.widget.el));
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
        delete components.Chatter.env;
        this.env = undefined;
    },
});

QUnit.test('base rendering when chatter has no attachment', async function (assert) {
    assert.expect(6);

    const messages = [...Array(60).keys()].map(id => {
        return {
            author_id: [10, "Demo User"],
            body: `<p>Message ${id + 1}</p>`,
            date: "2019-04-20 10:00:00",
            id: id + 1,
            message_type: 'comment',
            model: 'res.partner',
            record_name: 'General',
            res_id: 100,
        };
    });
    this.data['mail.message'].records = messages;

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

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [{
                    id: 143,
                    filename: 'Blah.txt',
                    mimetype: 'text/plain',
                    name: 'Blah.txt'
                }, {
                    id: 144,
                    filename: 'Blu.txt',
                    mimetype: 'text/plain',
                    name: 'Blu.txt'
                }];
            }
            return this._super(...arguments);
        }
    });
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

    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [{
                    id: 143,
                    filename: 'Blah.txt',
                    mimetype: 'text/plain',
                    name: 'Blah.txt'
                }, {
                    id: 144,
                    filename: 'Blu.txt',
                    mimetype: 'text/plain',
                    name: 'Blu.txt'
                }];
            }
            return this._super(...arguments);
        }
    });
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

QUnit.test('composer show/hide on log note/send message', async function (assert) {
    assert.expect(8);

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

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_composer`).length,
        1,
        "should still have a composer"
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

});
});
});

});
