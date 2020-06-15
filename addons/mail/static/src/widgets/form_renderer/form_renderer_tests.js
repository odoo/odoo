odoo.define('mail/static/src/widgets/form_renderer/form_renderer_tests.js', function (require) {
"use strict";

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

const FormView = require('web.FormView');

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('form_renderer', {}, function () {
QUnit.module('form_renderer_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);
        this.data['res.partner'].fields = {
            activity_ids: {
                string: "Activities",
                type: 'one2many',
                relation: 'mail.activity',
            },
            message_attachment_count: {
                string: 'Attachment count',
                type: 'integer',
            },
            message_follower_ids: {
                string: "Followers",
                type: 'one2many',
                relation: 'mail.followers',
            },
            message_ids: {
                string: "Messages",
                type: 'one2many',
                relation: 'mail.message',
            },
            name: {
                string: "Name",
                type: 'char',
            },
        };
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;
        // FIXME archs could be removed once task-2248306 is done
        this.createView = async (viewParams, ...args) => {
            await afterNextRender(async () => {
                const viewArgs = Object.assign({
                    archs: {
                        'mail.activity,false,list': '<tree/>',
                        'mail.followers,false,list': '<tree/>',
                        'mail.message,false,list': '<tree/>',
                    }},
                    viewParams,
                );
                const { widget } = await start(viewArgs, ...args);
                this.view = widget;
            });
        };
    },
    afterEach() {
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
        if (this.view) {
            this.view.destroy();
        }
        utilsAfterEach(this);
    },
});

QUnit.test('basic chatter rendering', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records = [{
        id: 2,
        display_name: "second partner",
    }];
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
        res_id: 2,
    });

    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
});

QUnit.test('basic chatter rendering without followers', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records = [{
        activity_ids: [],
        id: 2,
        display_name: "second partner",
        message_ids: [],
        message_follower_ids: [],
    }];
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
        res_id: 2,
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

    this.data['res.partner'].records = [{
        activity_ids: [],
        id: 2,
        display_name: "second partner",
        message_ids: [],
        message_follower_ids: [],
    }];
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
        res_id: 2,
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

    this.data['res.partner'].records = [{
        activity_ids: [],
        id: 2,
        display_name: "second partner",
        message_ids: [],
        message_follower_ids: [],
    }];
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
        res_id: 2,
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

    this.data['ir.attachment'].records = [{
        id: 1,
        mimetype: 'image/png',
        name: 'filename.jpg',
        res_id: 7,
        res_model: 'partner',
        type: 'url',
    }, {
        id: 2,
        mimetype: "application/x-msdos-program",
        name: "file2.txt",
        res_id: 7,
        res_model: 'partner',
        type: 'binary',
    }, {
        id: 3,
        mimetype: "application/x-msdos-program",
        name: "file3.txt",
        res_id: 5,
        res_model: 'partner',
        type: 'binary',
    }];
    this.data['mail.message'].records = [{
        id: 1000,
        body: "<p>test 1</p>",
        author_id: [100, "Someone"],
        model: 'res.partner',
        res_id: 2,
        moderation_status: 'accepted',
    }];
    this.data['res.partner'].records = [{
        id: 1,
        display_name: "first partner",
        message_ids: [],
    }, {
        id: 2,
        display_name: "second partner",
        message_ids: [],
    }];
    await this.createView({
        data: this.data,
        hasView: true,
        // View params
        View: FormView,
        model: 'res.partner',
        res_id: 1,
        viewOptions: {
            ids: [1, 2],
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

});
});
});

});
