odoo.define('mail.component.ChatterTopBarTests', function (require) {
'use strict';

const ChatterTopBar = require('mail.component.ChatterTopbar');
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('ChatterTopbar', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createThread = async ({ _model, id }, { fetchAttachments=false }={}) => {
            const threadLocalId = this.env.store.dispatch('_createThread', { _model, id });
            if (fetchAttachments) {
                await this.env.store.dispatch('fetchThreadAttachments', threadLocalId);
            }
            return threadLocalId;
        };
        this.createChatterTopbar = async (threadLocalId, otherProps) => {
            ChatterTopBar.env = this.env;
            this.chatterTopbar = new ChatterTopBar(null, Object.assign({ threadLocalId }, otherProps));
            await this.chatterTopbar.mount(this.widget.el);
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
        if (this.chatterTopbar) {
            this.chatterTopbar.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        delete ChatterTopBar.env;
        this.env = undefined;
    }
});

QUnit.test('base rendering', async function (assert) {
    assert.expect(9);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    const threadLocalId = await this.createThread({ _model: 'res.partner', id: 100 });
    await this.createChatterTopbar(threadLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonSendMessage`).length,
        1,
        "should have a send message button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonLogNote`).length,
        1,
        "should have a log note button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonScheduleActivity`).length,
        1,
        "should have a schedule activity button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonFollow`).length,
        1,
        "should have a follow button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonFollowers`).length,
        1,
        "should have a followers button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonFollowersCount`).length,
        1,
        "followers button should have a counter"
    );
});

QUnit.test('attachment count without attachments', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    const threadLocalId = await this.createThread({ _model: 'res.partner', id: 100 });
    await this.createChatterTopbar(threadLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatterTopbar_buttonAttachmentsCount`).textContent,
        '0',
        'attachment counter should contain "0"'
    );
});

QUnit.test('attachment count with attachments', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
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
    const threadLocalId = await this.createThread({ _model: 'res.partner', id: 100 }, { fetchAttachments: true });
    await this.createChatterTopbar(threadLocalId);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatterTopbar_buttonAttachmentsCount`).textContent,
        '2',
        'attachment counter should contain "2"'
    );
});

});
});
});
