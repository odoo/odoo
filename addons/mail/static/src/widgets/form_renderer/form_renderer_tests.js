odoo.define('mail/static/src/widgets/form_renderer/form_renderer_tests.js', function (require) {
"use strict";

const {
    afterEach,
    afterNextRender,
    beforeEach,
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
                const { env, widget } = await start(viewArgs, ...args);
                this.env = env;
                this.widget = widget;
            });
        };
    },
    afterEach() {
        afterEach(this);
    },
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
    assert.expect(3);

    this.data['mail.message'].records.push({ model: 'res.partner', res_id: 12 });
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
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsNone(
        document.body,
        '.o_Message',
        "there should be no message"
    );

    await afterNextRender(() => {
        document.querySelector('.o_pager_next').click();
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message"
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

    await afterNextRender(() => {
        document.querySelector('.o_form_button_edit').click();
    });
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should still be only one read more after switching to edit mode"
    );

    await afterNextRender(() => {
        document.querySelector('.o_form_button_cancel').click();
    });
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

    await afterNextRender(() => {
        document.querySelector('.o_form_button_edit').click();
    });
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        'read more',
        "read more/less link should contain 'read more' as text"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_readMoreLess').click();
    });
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
        controllerContentEl.scrollTop = controllerContentEl.scrollHeight - controllerContentEl.offsetHeight;
        await triggerEvent(
            document.querySelector('.o_ThreadViewer_messageList'),
            'scroll'
        );
    });
    assert.strictEqual(
        controllerContentEl.scrollTop,
        controllerContentEl.scrollHeight - controllerContentEl.offsetHeight,
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

});
});
});

});
