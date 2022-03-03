/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

import { makeTestPromise } from 'web.test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chatter_topbar', {}, function () {
QUnit.module('chatter_topbar_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createChatterTopbarComponent = async (chatter, otherProps) => {
            const props = Object.assign({ chatterLocalId: chatter.localId }, otherProps);
            await createRootMessagingComponent(this, "ChatterTopbar", {
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

QUnit.test('base rendering', async function (assert) {
    assert.expect(8);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
        document.querySelectorAll(`.o_ChatterTopbar_followerListMenu`).length,
        1,
        "should have a follower menu"
    );
});

QUnit.test('base disabled rendering', async function (assert) {
    assert.expect(8);

    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
});

QUnit.test('attachment loading is delayed', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start({
        hasTimeControl: true,
        loadingBaseDelayDuration: 100,
        async mockRPC(route) {
            if (route.includes('/mail/thread/data')) {
                await makeTestPromise(); // simulate long loading
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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
        0,
        "attachments button should not have a loader yet"
    );

    await afterNextRender(async () => this.env.testUtils.advanceTime(100));
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatterTopbar_buttonAttachmentsCountLoader`).length,
        1,
        "attachments button should now have a loader"
    );
});

QUnit.test('attachment counter while loading attachments', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start({
        async mockRPC(route) {
            if (route.includes('/mail/thread/data')) {
                await makeTestPromise(); // simulate long loading
            }
            return this._super(...arguments);
        }
    });
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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

    this.data['res.partner'].records.push({ id: 100 });
    const attachmentPromise = makeTestPromise();
    await this.start({
        async mockRPC(route) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route.includes('/mail/thread/data')) {
                await attachmentPromise;
            }
            return _super();
        },
    });
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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

    await afterNextRender(() => attachmentPromise.resolve());
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

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
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

QUnit.test('composer state conserved when clicking on another topbar button', async function (assert) {
    assert.expect(8);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar`,
        "should have a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonSendMessage`,
        "should have a send message button in chatter menu"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonLogNote`,
        "should have a log note button in chatter menu"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonAttachments`,
        "should have an attachments button in chatter menu"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonLogNote.o-active`,
        "log button should now be active"
    );
    assert.containsNone(
        document.body,
        `.o_ChatterTopbar_buttonSendMessage.o-active`,
        "send message button should not be active"
    );

    document.querySelector(`.o_ChatterTopbar_buttonAttachments`).click();
    await nextAnimationFrame();
    assert.containsOnce(
        document.body,
        `.o_ChatterTopbar_buttonLogNote.o-active`,
        "log button should still be active"
    );
    assert.containsNone(
        document.body,
        `.o_ChatterTopbar_buttonSendMessage.o-active`,
        "send message button should still be not active"
    );
});

QUnit.test('rendering with multiple partner followers', async function (assert) {
    assert.expect(7);

    await this.start();
    this.data['res.partner'].records.push({
        id: 100,
        message_follower_ids: [1, 2],
    });
    this.data['mail.followers'].records.push(
        {
            // simulate real return from RPC
            id: 1,
            name: "Jean Michang",
            partner_id: 12,
            res_id: 100,
            res_model: 'res.partner',
        }, {
            // simulate real return from RPC
            id: 2,
            name: "Eden Hazard",
            partner_id: 11,
            res_id: 100,
            res_model: 'res.partner',
        },
    );
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        followerIds: [1, 2],
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);

    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be opened"
    );
    assert.containsN(
        document.body,
        '.o_Follower',
        2,
        "exactly two followers should be listed"
    );
    assert.containsN(
        document.body,
        '.o_Follower_name',
        2,
        "exactly two follower names should be listed"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Follower_name')[0].textContent.trim(),
        "Jean Michang",
        "first follower is 'Jean Michang'"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Follower_name')[1].textContent.trim(),
        "Eden Hazard",
        "second follower is 'Eden Hazard'"
    );
});

QUnit.test('log note/send message switching', async function (assert) {
    assert.expect(8);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonSendMessage',
        "should have a 'Send Message' button"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonSendMessage'),
        'o-active',
        "'Send Message' button should not be active"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonLogNote',
        "should have a 'Log Note' button"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonLogNote'),
        'o-active',
        "'Log Note' button should not be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).click()
    );
    assert.hasClass(
        document.querySelector('.o_ChatterTopbar_buttonSendMessage'),
        'o-active',
        "'Send Message' button should be active"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonLogNote'),
        'o-active',
        "'Log Note' button should not be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click()
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonSendMessage'),
        'o-active',
        "'Send Message' button should not be active"
    );
    assert.hasClass(
        document.querySelector('.o_ChatterTopbar_buttonLogNote'),
        'o-active',
        "'Log Note' button should be active"
    );
});

QUnit.test('log note toggling', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonLogNote',
        "should have a 'Log Note' button"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonLogNote'),
        'o-active',
        "'Log Note' button should not be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click()
    );
    assert.hasClass(
        document.querySelector('.o_ChatterTopbar_buttonLogNote'),
        'o-active',
        "'Log Note' button should be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).click()
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonLogNote'),
        'o-active',
        "'Log Note' button should not be active"
    );
});

QUnit.test('send message toggling', async function (assert) {
    assert.expect(4);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start();
    const chatter = this.messaging.models['mail.chatter'].create({
        id: 11,
        threadId: 100,
        threadModel: 'res.partner',
    });
    await this.createChatterTopbarComponent(chatter);
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonSendMessage',
        "should have a 'Send Message' button"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonSendMessage'),
        'o-active',
        "'Send Message' button should not be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).click()
    );
    assert.hasClass(
        document.querySelector('.o_ChatterTopbar_buttonSendMessage'),
        'o-active',
        "'Send Message' button should be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).click()
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_ChatterTopbar_buttonSendMessage'),
        'o-active',
        "'Send Message' button should not be active"
    );
});

});
});
});
