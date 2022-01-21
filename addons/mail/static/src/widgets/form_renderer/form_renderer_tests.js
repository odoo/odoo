odoo.define('mail/static/src/widgets/form_renderer/form_renderer_tests.js', function (require) {
"use strict";

const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');
const {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

const config = require('web.config');
const FormView = require('web.FormView');
const {
    dom: { triggerEvent },
} = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('form_renderer', {}, function () {
QUnit.module('form_renderer_tests.js', {
    beforeEach() {
        beforeEach(this);

        // FIXME archs could be removed once task-2248306 is done
        // The mockServer will try to get the list view
        // of every relational fields present in the main view.
        // In the case of mail fields, we don't really need them,
        // but they still need to be defined.
        this.createView = async (viewParams, ...args) => {
            await afterNextRender(async () => {
                const viewArgs = Object.assign(
                    {
                        archs: {
                            'mail.activity,false,list': '<tree/>',
                            'mail.followers,false,list': '<tree/>',
                            'mail.message,false,list': '<tree/>',
                        },
                    },
                    viewParams,
                );
                const { afterEvent, env, widget } = await start(viewArgs, ...args);
                this.afterEvent = afterEvent;
                this.env = env;
                this.widget = widget;
            });
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('[technical] spinner when messaging is not created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(3);

    this.data['res.partner'].records.push({
        display_name: "second partner",
        id: 12,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        messagingBeforeCreationDeferred: makeDeferred(), // block messaging creation
        waitUntilMessagingCondition: 'none',
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>
        `,
        res_id: 12,
    });
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer',
        "should display chatter container even when messaging is not created yet"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not created"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet created"
    );
});

QUnit.test('[technical] keep spinner on transition from messaging non-created to messaging created (and non-initialized)', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(4);

    const messagingBeforeCreationDeferred = makeDeferred();
    this.data['res.partner'].records.push({
        display_name: "second partner",
        id: 12,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        messagingBeforeCreationDeferred,
        async mockRPC(route, args) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route === '/mail/init_messaging') {
                await new Promise(() => {}); // simulate messaging never initialized
            }
            return _super();
        },
        waitUntilMessagingCondition: 'none',
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>
        `,
        res_id: 12,
    });
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet created"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not created"
    );

    // simulate messaging become created
    messagingBeforeCreationDeferred.resolve();
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should still display spinner when messaging is created but not initialized"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should still not display any chatter when messaging not initialized"
    );
});

QUnit.test('spinner when messaging is created but not initialized', async function (assert) {
    assert.expect(3);

    this.data['res.partner'].records.push({
        display_name: "second partner",
        id: 12,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        async mockRPC(route, args) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route === '/mail/init_messaging') {
                await new Promise(() => {}); // simulate messaging never initialized
            }
            return _super();
        },
        waitUntilMessagingCondition: 'created',
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>
        `,
        res_id: 12,
    });
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer',
        "should display chatter container even when messaging is not fully initialized"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not initialized"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet initialized"
    );
});

QUnit.test('transition non-initialized messaging to initialized messaging: display spinner then chatter', async function (assert) {
    assert.expect(3);

    const messagingBeforeInitializationDeferred = makeDeferred();
    this.data['res.partner'].records.push({
        display_name: "second partner",
        id: 12,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        async mockRPC(route, args) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route === '/mail/init_messaging') {
                await messagingBeforeInitializationDeferred;
            }
            return _super();
        },
        waitUntilMessagingCondition: 'created',
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>
        `,
        res_id: 12,
    });
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet initialized"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not initialized"
    );

    // Simulate messaging becomes initialized
    await afterNextRender(() => messagingBeforeInitializationDeferred.resolve());
    assert.containsNone(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should now display chatter when messaging becomes initialized"
    );
});

QUnit.test('basic chatter rendering', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ display_name: "second partner", id: 12, });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>
        `,
        res_id: 12,
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
});

QUnit.test('basic chatter rendering without followers', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ display_name: "second partner", id: 12 });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        res_id: 12,
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar',
        "there should be a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonAttachments',
        "there should be an attachment button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "there should be a schedule activity button"
    );
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu',
        "there should be no followers menu"
    );
    assert.containsOnce(
        document.body,
        '.o_Chatter_thread',
        "there should be a thread"
    );
});

QUnit.test('basic chatter rendering without activities', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ display_name: "second partner", id: 12 });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        res_id: 12,
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar',
        "there should be a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonAttachments',
        "there should be an attachment button"
    );
    assert.containsNone(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "there should be a schedule activity button"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "there should be a followers menu"
    );
    assert.containsOnce(
        document.body,
        '.o_Chatter_thread',
        "there should be a thread"
    );
});

QUnit.test('basic chatter rendering without messages', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ display_name: "second partner", id: 12 });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>
        `,
        res_id: 12,
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar',
        "there should be a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonAttachments',
        "there should be an attachment button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "there should be a schedule activity button"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "there should be a followers menu"
    );
    assert.containsNone(
        document.body,
        '.o_Chatter_thread',
        "there should be a thread"
    );
});

QUnit.test('chatter updating', async function (assert) {
    assert.expect(1);

    this.data['mail.message'].records.push({ body: "not empty", model: 'res.partner', res_id: 12 });
    this.data['res.partner'].records.push(
        { display_name: "first partner", id: 11 },
        { display_name: "second partner", id: 12 }
    );
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        res_id: 11,
        viewOptions: {
            ids: [11, 12],
            index: 0,
        },
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        waitUntilEvent: {
            eventName: 'o-thread-view-hint-processed',
            message: "should wait until partner 11 thread loaded messages initially",
            predicate: ({ hint, threadViewer }) => {
                return (
                    hint.type === 'messages-loaded' &&
                    threadViewer.thread.model === 'res.partner' &&
                    threadViewer.thread.id === 11
                );
            },
        }
    });

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_pager_next').click(),
        message: "should wait until partner 12 thread loaded messages after clicking on next",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === 12
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message in partner 12 thread"
    );
});

QUnit.test('chatter should become enabled when creation done', async function (assert) {
    assert.expect(10);

    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        viewOptions: {
            mode: 'edit',
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonSendMessage',
        "there should be a send message button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonLogNote',
        "there should be a log note button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonLogNote',
        "there should be an attachments button"
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
        document.querySelector(`.o_ChatterTopbar_buttonAttachments`).disabled,
        "attachments button should be disabled"
    );

    document.querySelectorAll('.o_field_char')[0].focus();
    document.execCommand('insertText', false, "hello");
    await afterNextRender(() => {
        document.querySelector('.o_form_button_save').click();
    });
    assert.notOk(
        document.querySelector(`.o_ChatterTopbar_buttonSendMessage`).disabled,
        "send message button should now be enabled"
    );
    assert.notOk(
        document.querySelector(`.o_ChatterTopbar_buttonLogNote`).disabled,
        "log note button should now be enabled"
    );
    assert.notOk(
        document.querySelector(`.o_ChatterTopbar_buttonAttachments`).disabled,
        "attachments button should now be enabled"
    );
});

QUnit.test('read more/less links are not duplicated when switching from read to edit mode', async function (assert) {
    assert.expect(5);

    this.data['mail.message'].records.push({
        author_id: 100,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>
        `,
        id: 1000,
        model: 'res.partner',
        res_id: 2,
    });
    this.data['res.partner'].records.push({
        display_name: "Someone",
        id: 100,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        res_id: 2,
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        waitUntilEvent: {
            eventName: 'o-component-message-read-more-less-inserted',
            message: "should wait until read more/less is inserted initially",
            predicate: ({ message }) => message.id === 1000,
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should be only one read more"
    );
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-component-message-read-more-less-inserted',
        func: () => document.querySelector('.o_form_button_edit').click(),
        message: "should wait until read more/less is inserted after clicking on edit",
        predicate: ({ message }) => message.id === 1000,
    }));
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should still be only one read more after switching to edit mode"
    );

    await afterNextRender(() => this.afterEvent({
        eventName: 'o-component-message-read-more-less-inserted',
        func: () => document.querySelector('.o_form_button_cancel').click(),
        message: "should wait until read more/less is inserted after canceling edit",
        predicate: ({ message }) => message.id === 1000,
    }));
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should still be only one read more after switching back to read mode"
    );
});

QUnit.test('read more links becomes read less after being clicked', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records = [{
        author_id: 100,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>
        `,
        id: 1000,
        model: 'res.partner',
        res_id: 2,
    }];
    this.data['res.partner'].records.push({
        display_name: "Someone",
        id: 100,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        res_id: 2,
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        waitUntilEvent: {
            eventName: 'o-component-message-read-more-less-inserted',
            message: "should wait until read more/less is inserted initially",
            predicate: ({ message }) => message.id === 1000,
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should be a read more"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        'read more',
        "read more/less link should contain 'read more' as text"
    );

    await afterNextRender(() => this.afterEvent({
        eventName: 'o-component-message-read-more-less-inserted',
        func: () => document.querySelector('.o_form_button_edit').click(),
        message: "should wait until read more/less is inserted after clicking on edit",
        predicate: ({ message }) => message.id === 1000,
    }));
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        'read more',
        "read more/less link should contain 'read more' as text"
    );

    document.querySelector('.o_Message_readMoreLess').click();
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        'read less',
        "read more/less link should contain 'read less' as text after it has been clicked"
    );
});

QUnit.test('Form view not scrolled when switching record', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push(
        {
            id: 11,
            display_name: "Partner 1",
            description: [...Array(60).keys()].join('\n'),
        },
        {
            id: 12,
            display_name: "Partner 2",
        }
    );

    const messages = [...Array(60).keys()].map(id => {
        return {
            model: 'res.partner',
            res_id: id % 2 ? 11 : 12,
        };
    });
    this.data['mail.message'].records = messages;

    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
        viewOptions: {
            currentId: 11,
            ids: [11, 12],
        },
        config: {
            device: { size_class: config.device.SIZES.LG },
        },
        env: {
            device: { size_class: config.device.SIZES.LG },
        },
    });

    const controllerContentEl = document.querySelector('.o_content');

    assert.strictEqual(
        document.querySelector('.breadcrumb-item.active').textContent,
        'Partner 1',
        "Form view should display partner 'Partner 1'"
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The top of the form view is visible"
    );

    await afterNextRender(async () => {
        controllerContentEl.scrollTop = controllerContentEl.scrollHeight - controllerContentEl.clientHeight;
        await triggerEvent(
            document.querySelector('.o_ThreadView_messageList'),
            'scroll'
        );
    });
    assert.strictEqual(
        controllerContentEl.scrollTop,
        controllerContentEl.scrollHeight - controllerContentEl.clientHeight,
        "The controller container should be scrolled to its bottom"
    );

    await afterNextRender(() =>
        document.querySelector('.o_pager_next').click()
    );
    assert.strictEqual(
        document.querySelector('.breadcrumb-item.active').textContent,
        'Partner 2',
        "The form view should display partner 'Partner 2'"
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The top of the form view should be visible when switching record from pager"
    );

    await afterNextRender(() =>
        document.querySelector('.o_pager_previous').click()
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "Form view's scroll position should have been reset when switching back to first record"
    );
});

QUnit.test('Attachments that have been unlinked from server should be visually unlinked from record', async function (assert) {
    // Attachments that have been fetched from a record at certain time and then
    // removed from the server should be reflected on the UI when the current
    // partner accesses this record again.
    assert.expect(2);

    this.data['res.partner'].records.push(
        { display_name: "Partner1", id: 11 },
        { display_name: "Partner2", id: 12 }
    );
    this.data['ir.attachment'].records.push(
        {
           id: 11,
           mimetype: 'text.txt',
           res_id: 11,
           res_model: 'res.partner',
        },
        {
           id: 12,
           mimetype: 'text.txt',
           res_id: 11,
           res_model: 'res.partner',
        }
    );
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        res_id: 11,
        viewOptions: {
            ids: [11, 12],
            index: 0,
        },
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
    });
    assert.strictEqual(
        document.querySelector('.o_ChatterTopbar_buttonCount').textContent,
        '2',
        "Partner1 should have 2 attachments initially"
    );

    // The attachment links are updated on (re)load,
    // so using pager is a way to reload the record "Partner1".
    await afterNextRender(() =>
        document.querySelector('.o_pager_next').click()
    );
    // Simulate unlinking attachment 12 from Partner 1.
    this.data['ir.attachment'].records.find(a => a.id === 11).res_id = 0;
    await afterNextRender(() =>
        document.querySelector('.o_pager_previous').click()
    );
    assert.strictEqual(
        document.querySelector('.o_ChatterTopbar_buttonCount').textContent,
        '1',
        "Partner1 should now have 1 attachment after it has been unlinked from server"
    );
});

QUnit.test('chatter just contains "creating a new record" message during the creation of a new record after having displayed a chatter for an existing record', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 12 });
    await this.createView({
        data: this.data,
        hasView: true,
        View: FormView,
        model: 'res.partner',
        res_id: 12,
        arch: `
            <form>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
    });

    await afterNextRender(() => {
        document.querySelector('.o_form_button_create').click();
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "Should have a single message when creating a new record"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_content').textContent,
        'Creating a new record...',
        "the message content should be in accord to the creation of this record"
    );
});

QUnit.test('[TECHNICAL] unfolded read more/less links should not fold on message click besides those button links', async function (assert) {
    // message click triggers a re-render. Before writing of this test, the
    // insertion of read more/less links were done during render. This meant
    // any re-render would re-insert the read more/less links. If some button
    // links were unfolded, any re-render would fold them again.
    //
    // This previous behavior is undesirable, and results to bothersome UX
    // such as inability to copy/paste unfolded message content due to click
    // from text selection automatically folding all read more/less links.
    assert.expect(3);

    this.data['mail.message'].records.push({
        author_id: 100,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>
        `,
        id: 1000,
        model: 'res.partner',
        res_id: 2,
    });
    this.data['res.partner'].records.push({
        display_name: "Someone",
        id: 100,
    });
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        res_id: 2,
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>
        `,
    });
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        "read more",
        "read more/less link on message should be folded initially (read more)"
    );

    document.querySelector('.o_Message_readMoreLess').click(),
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        "read less",
        "read more/less link on message should be unfolded after a click from initial rendering (read less)"
    );

    await afterNextRender(
        () => document.querySelector('.o_Message').click(),
    );
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        "read less",
        "read more/less link on message should still be unfolded after a click on message aside of this button click (read less)"
    );
});

});
});
});

});
