odoo.define('mail.messaging.component.ChatterTopBarTests', function (require) {
'use strict';

const components = {
    ChatterTopBar: require('mail.messaging.component.ChatterTopbar'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

const { makeTestPromise } = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('ChatterTopbar', {
    beforeEach() {
        utilsBeforeEach(this);
        this.createChatterTopbarComponent = async (chatter, otherProps) => {
            const ChatterTopBarComponent = components.ChatterTopBar;
            ChatterTopBarComponent.env = this.env;
            const defaultProps = {
                isComposerLog: false,
                isComposerVisible: false
            };
            this.component = new ChatterTopBarComponent(
                null,
                Object.assign({ chatterLocalId: chatter.localId }, defaultProps, otherProps)
            );
            await this.component.mount(this.widget.el);
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
        delete components.ChatterTopBar.env;
        this.env = undefined;
    },
});

QUnit.test('base rendering', async function (assert) {
    assert.expect(10);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

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
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader"
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

QUnit.test('base disabled rendering', async function (assert) {
    assert.expect(11);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar`).length,
        1,
        "should have a chatter topbar"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).disabled,
        "send message button should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).disabled,
        "log note button should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonScheduleActivity`).disabled,
        "schedule activity should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonAttachments`).disabled,
        "attachments button should be disabled"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatterTopbar_buttonAttachmentsCount`).textContent,
        '0',
        "attachments button counter should be 0"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonFollow`).disabled,
        "follow button should be disabled"
    );
    assert.ok(
        document.querySelector(`.o_ChatterTopbar_buttonFollowers`).disabled,
        "followers button should be disabled"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonFollowersCount`).length,
        1,
        "followers button should have a counter"
    );
});

QUnit.test('attachment counter while loading attachments', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return new Promise(() => {}); // simulate long loading
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

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
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        1,
        "attachments button should have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        0,
        "attachments button should not have a counter"
    );
});

QUnit.test('attachment counter transition when attachments become loaded)', async function (assert) {
    assert.expect(7);

    const attachmentPromise = makeTestPromise();
    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                await attachmentPromise;
                return [];
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
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
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        1,
        "attachments button should have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        0,
        "attachments button should not have a counter"
    );

    attachmentPromise.resolve(); // Simulates attachments are loaded
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachments`).length,
        1,
        "should have an attachments button in chatter menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        0,
        "attachments button should not have a loader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCount`).length,
        1,
        "attachments button should have a counter"
    );
});

QUnit.test('attachment counter without attachments', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route) {
            if (route.includes('ir.attachment/search_read')) {
                return [];
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

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

QUnit.test('attachment counter with attachments', async function (assert) {
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
    const chatter = this.env.entities.Chatter.create({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

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

});
