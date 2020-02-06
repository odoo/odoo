odoo.define('mail.messaging.widget.FormRendererTests', function (require) {
"use strict";

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start,
} = require('mail.messaging.testUtils');

const FormView = require('web.FormView');

QUnit.module('mail', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('widget', {}, function () {
QUnit.module('FormRenderer', {
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
        this.createView = async (...args) => {
            const { widget } = await start(...args);
            this.view = widget;
            await afterNextRender();
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
    assert.expect(7);

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
                    <field name="activity_ids" widget="mail_activity"/>
                    <field name="message_ids" widget="mail_thread"/>
                </div>
            </form>
        `,
        res_id: 2,
    });

    assert.containsOnce(document.body, `.o_Chatter`,
        "there should be a chatter"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar`,
        "there should be a chatter topbar"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonAttachments`,
        "there should be an attachment button"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonScheduleActivity`,
        "there should be a schedule activity button"
    );
    assert.containsNone(document.body, `.o_ChatterTopbar_buttonFollow`,
        "there should be no follow button"
    );
    assert.containsNone(document.body, `.o_ChatterTopbar_buttonFollowers`,
        "there should be no followers button"
    );
    assert.containsOnce(document.body, `.o_Chatter_thread`,
        "there should be a thread"
    );
});

QUnit.test('basic chatter rendering without activities', async function (assert) {
    assert.expect(7);

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
                    <field name="message_follower_ids" widget="mail_followers"/>
                    <field name="message_ids" widget="mail_thread"/>
                </div>
            </form>
        `,
        res_id: 2,
    });

    assert.containsOnce(document.body, `.o_Chatter`,
        "there should be a chatter"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar`,
        "there should be a chatter topbar"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonAttachments`,
        "there should be an attachment button"
    );
    assert.containsNone(document.body, `.o_ChatterTopbar_buttonScheduleActivity`,
        "there should be a schedule activity button"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonFollow`,
        "there should be no follow button"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonFollowers`,
        "there should be no followers button"
    );
    assert.containsOnce(document.body, `.o_Chatter_thread`,
        "there should be a thread"
    );
});

QUnit.test('basic chatter rendering without messages', async function (assert) {
    assert.expect(7);

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
                    <field name="message_follower_ids" widget="mail_followers"/>
                    <field name="activity_ids" widget="mail_activity"/>
                </div>
            </form>
        `,
        res_id: 2,
    });

    assert.containsOnce(document.body, `.o_Chatter`,
        "there should be a chatter"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar`,
        "there should be a chatter topbar"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonAttachments`,
        "there should be an attachment button"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonScheduleActivity`,
        "there should be a schedule activity button"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonFollow`,
        "there should be no follow button"
    );
    assert.containsOnce(document.body, `.o_ChatterTopbar_buttonFollowers`,
        "there should be no followers button"
    );
    assert.containsNone(document.body, `.o_Chatter_thread`,
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
                    <field name="message_ids" widget="mail_thread"/>
                </div>
            </form>
        `,
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        0,
        "there should be no message"
    );

    document.querySelector(`.o_pager_next`).click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        1,
        "there should be a message"
    );
});

});
});
});

});
