odoo.define('mail.component.ChatterTests', function (require) {
'use strict';

const Chatter = require('mail.component.Chatter');
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Chatter', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createChatter = async ({ id, model }, otherProps) => {
            Chatter.env = this.env;
            this.chatter = new Chatter(null, Object.assign({ model, id }, otherProps));
            await this.chatter.mount(this.widget.el);
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
        if (this.chatter) {
            this.chatter.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        delete Chatter.env;
        this.env = undefined;
    }
});

QUnit.test('base rendering when chatter has no attachments', async function (assert) {
    assert.expect(6);
    let amountOfCalls = 0;
    let lastId = 1000;
    await this.start({
        async mockRPC(route, args) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            if (args.method === 'message_fetch') {
                // multiple calls here to be able to test load more (up to (10000 / 30) calls normally
                let messagesData = [];
                const amountOfMessages = 30;
                const firstIValue = (lastId - amountOfCalls * amountOfMessages) - 1;
                const lastIValue = firstIValue - amountOfMessages;

                for (let i = firstIValue; i > lastIValue; i--) {
                    messagesData.push({
                        author_id: [firstIValue, `#${firstIValue}`],
                        body: `<em>Page ${amountOfCalls + 1}</em><br/><p>#${i} message</p>`,
                        channel_ids: [20],
                        date: "2019-04-20 10:00:00",
                        id: lastId + i,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: 'General',
                        res_id: 20,
                    });
                }
                lastId = lastIValue;
                amountOfCalls++;
                return messagesData;
            }
            return this._super(...arguments);
        }
    });
    await this.createChatter({
        id: 100,
        model: 'res.partner'
    });
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
        'res.partner_100',
        'thread should have the right thread local id'
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "the first 30 messages of thread should be loaded"
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
    await this.createChatter({
        id: 100,
        model: 'res.partner'
    });
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
    await this.createChatter({
        id: 100,
        model: 'res.partner'
    });
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

    document.querySelector(`.o_ChatterTopbar_buttonAttachments`).click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter_attachmentBox`).length,
        1,
        "should have an attachment box in the chatter"
    );
});

});
});
});
