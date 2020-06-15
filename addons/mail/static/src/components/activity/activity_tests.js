odoo.define('mail/static/src/components/activity/activity_tests.js', function (require) {
'use strict';

const components = {
    Activity: require('mail/static/src/components/activity/activity.js'),
};

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const Bus = require('web.Bus');
const { date_to_str } = require('web.time');

const { Component, tags: { xml } } = owl;

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createActivityComponent = async function (activity) {
            const ActivityComponent = components.Activity;
            ActivityComponent.env = this.env;
            this.component = new ActivityComponent(null, {
                activityLocalId: activity.localId,
            });
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
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
        this.env = undefined;
    },
});

QUnit.test('activity simplest layout', async function (assert) {
    assert.expect(12);

    await this.start();
    const activity = this.env.models['mail.activity'].create();
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_sidebar').length,
        1,
        "should have activity sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_core').length,
        1,
        "should have activity core"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_user').length,
        1,
        "should have activity user"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_info').length,
        1,
        "should have activity info"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_note').length,
        0,
        "should not have activity note"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        0,
        "should not have activity details"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_mailTemplates').length,
        0,
        "should not have activity mail templates"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_editButton').length,
        0,
        "should not have activity Edit button"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_cancelButton').length,
        0,
        "should not have activity Cancel button"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_markDoneButton').length,
        0,
        "should not have activity Mark as Done button"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_uploadButton').length,
        0,
        "should not have activity Upload button"
    );
});

QUnit.test('activity with note layout', async function (assert) {
    assert.expect(3);

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        note: 'There is no good or bad note'
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_note').length,
        1,
        "should have activity note"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_note').textContent,
        "There is no good or bad note",
        "activity note should be 'There is no good or bad note'"
    );
});

QUnit.test('activity info layout when planned after tomorrow', async function (assert) {
    assert.expect(4);

    await this.start();
    const today = new Date();
    const fiveDaysFromNow = new Date();
    fiveDaysFromNow.setDate(today.getDate() + 5);
    const activity = this.env.models['mail.activity'].create({
        dateDeadline: date_to_str(fiveDaysFromNow),
        state: 'planned',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_dueDateText').length,
        1,
        "should have activity delay"
    );
    assert.ok(
        document.querySelector('.o_Activity_dueDateText').classList.contains('o-planned'),
        "activity delay should have the right color modifier class (planned)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "Due in 5 days:",
        "activity delay should have 'Due in 5 days:' as label"
    );
});

QUnit.test('activity info layout when planned tomorrow', async function (assert) {
    assert.expect(4);

    await this.start();
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const activity = this.env.models['mail.activity'].create({
        dateDeadline: date_to_str(tomorrow),
        state: 'planned',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_dueDateText').length,
        1,
        "should have activity delay"
    );
    assert.ok(
        document.querySelector('.o_Activity_dueDateText').classList.contains('o-planned'),
        "activity delay should have the right color modifier class (planned)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        'Tomorrow:',
        "activity delay should have 'Tomorrow:' as label"
    );
});

QUnit.test('activity info layout when planned today', async function (assert) {
    assert.expect(4);

    await this.start();
    const today = new Date();
    const activity = this.env.models['mail.activity'].create({
        dateDeadline: date_to_str(today),
        state: 'today',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_dueDateText').length,
        1,
        "should have activity delay"
    );
    assert.ok(
        document.querySelector('.o_Activity_dueDateText').classList.contains('o-today'),
        "activity delay should have the right color modifier class (today)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "Today:",
        "activity delay should have 'Today:' as label"
    );
});

QUnit.test('activity info layout when planned yesterday', async function (assert) {
    assert.expect(4);

    await this.start();
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const activity = this.env.models['mail.activity'].create({
        dateDeadline: date_to_str(yesterday),
        state: 'overdue',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_dueDateText').length,
        1,
        "should have activity delay"
    );
    assert.ok(
        document.querySelector('.o_Activity_dueDateText').classList.contains('o-overdue'),
        "activity delay should have the right color modifier class (overdue)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "Yesterday:",
        "activity delay should have 'Yesterday:' as label"
    );
});

QUnit.test('activity info layout when planned before yesterday', async function (assert) {
    assert.expect(4);

    await this.start();
    const today = new Date();
    const fiveDaysBeforeNow = new Date();
    fiveDaysBeforeNow.setDate(today.getDate() - 5);
    const activity = this.env.models['mail.activity'].create({
        dateDeadline: date_to_str(fiveDaysBeforeNow),
        state: 'overdue',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_dueDateText').length,
        1,
        "should have activity delay"
    );
    assert.ok(
        document.querySelector('.o_Activity_dueDateText').classList.contains('o-overdue'),
        "activity delay should have the right color modifier class (overdue)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "5 days overdue:",
        "activity delay should have '5 days overdue:' as label"
    );
});

QUnit.test('activity with a summary layout', async function (assert) {
    assert.expect(4);

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        summary: 'test summary',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_summary').length,
        1,
        "should have activity summary"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_type').length,
        0,
        "should not have the activity type as summary"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_summary').textContent.trim(),
        "“test summary”",
        "should have the specific activity summary in activity summary"
    );
});

QUnit.test('activity without summary layout', async function (assert) {
    assert.expect(5);

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        type: [['insert', { id: 1, displayName: "Fake type" }]],
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_type').length,
        1,
        "activity details should have an activity type section"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_type').textContent.trim(),
        "Fake type",
        "activity details should have the activity type display name in type section"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_summary.o_Activity_type').length,
        1,
        "should have activity type as summary"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_summary:not(.o_Activity_type)').length,
        0,
        "should not have a specific summary"
    );
});

QUnit.test('activity details toggle', async function (assert) {
    assert.expect(5);

    await this.start();
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const activity = this.env.models['mail.activity'].create({
        creator: [['insert', { id: 1, partnerDisplayName: "Admin" }]],
        dateCreate: date_to_str(today),
        dateDeadline: date_to_str(tomorrow),
        state: 'planned',
        type: [['insert', { id: 1, displayName: "Fake type" }]],
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        0,
        "activity details should not be visible by default"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_detailsButton').length,
        1,
        "activity should have a details button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Activity_detailsButton').click()
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        1,
        "activity details should be visible after clicking on details button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Activity_detailsButton').click()
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        0,
        "activity details should no longer be visible after clicking again on details button"
    );
});

QUnit.test('activity details layout', async function (assert) {
    assert.expect(11);

    await this.start();
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const activity = this.env.models['mail.activity'].create({
        assignee: [['insert', { id: 10, partnerDisplayName: "Pauvre pomme" }]],
        creator: [['insert', { id: 1, partnerDisplayName: "Admin" }]],
        dateCreate: date_to_str(today),
        dateDeadline: date_to_str(tomorrow),
        state: 'planned',
        type: [['insert', { id: 1, displayName: "Fake type" }]],
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_userAvatar').length,
        1,
        "should have activity user avatar"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_detailsButton').length,
        1,
        "activity should have a details button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Activity_detailsButton').click()
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        1,
        "activity details should be visible after clicking on details button"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details .o_Activity_type').length,
        1,
        "activity details should have type"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_details .o_Activity_type').textContent,
        "Fake type",
        "activity details type should be 'Fake type'"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_detailsCreation').length,
        1,
        "activity details should have creation date "
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_detailsCreator').length,
        1,
        "activity details should have creator"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_detailsAssignation').length,
        1,
        "activity details should have assignation information"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_detailsAssignation').textContent.indexOf('Pauvre pomme'),
        0,
        "activity details assignation information should contain creator display name"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_detailsAssignationUserAvatar').length,
        1,
        "activity details should have user avatar"
    );
});

QUnit.test('activity with mail template layout', async function (assert) {
    assert.expect(8);

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        mailTemplates: [['insert', { id: 1, name: "Dummy mail template" }]],
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_sidebar').length,
        1,
        "should have activity sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_mailTemplates').length,
        1,
        "should have activity mail templates"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_mailTemplate').length,
        1,
        "should have activity mail template"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_MailTemplate_name').length,
        1,
        "should have activity mail template name"
    );
    assert.strictEqual(
        document.querySelector('.o_MailTemplate_name').textContent,
        "Dummy mail template",
        "should have activity mail template name"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_MailTemplate_preview').length,
        1,
        "should have activity mail template name preview button"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_MailTemplate_send').length,
        1,
        "should have activity mail template name send button"
    );
});

QUnit.test('activity with mail template: preview mail', async function (assert) {
    assert.expect(10);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.context.default_res_id,
            42,
            'Action should have the activity res id as default res id in context'
        );
        assert.strictEqual(
            payload.action.context.default_model,
            'res.partner',
            'Action should have the activity res model as default model in context'
        );
        assert.ok(
            payload.action.context.default_use_template,
            'Action should have true as default use_template in context'
        );
        assert.strictEqual(
            payload.action.context.default_template_id,
            1,
            'Action should have the selected mail template id as default template id in context'
        );
        assert.strictEqual(
            payload.action.type,
            "ir.actions.act_window",
            'Action should be of type "ir.actions.act_window"'
        );
        assert.strictEqual(
            payload.action.res_model,
            "mail.compose.message",
            'Action should have "mail.compose.message" as res_model'
        );
    });

    await this.start({ env: { bus } });
    const activity = this.env.models['mail.activity'].create({
        mailTemplates: [['insert', {
            id: 1,
            name: "Dummy mail template",
        }]],
        res_id: 42,
        res_model: 'res.partner',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_MailTemplate_preview').length,
        1,
        "should have activity mail template name preview button"
    );

    document.querySelector('.o_MailTemplate_preview').click();
    assert.verifySteps(
        ['do_action'],
        "should have called 'compose email' action correctly"
    );
});

QUnit.test('activity with mail template: send mail', async function (assert) {
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'activity_send_mail') {
                assert.step('activity_send_mail');
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 42);
                assert.strictEqual(args.args[1], 1);
                return;
            } else {
                return this._super(...arguments);
            }
        },
    });
    const activity = this.env.models['mail.activity'].create({
        mailTemplates: [['insert', {
            id: 1,
            name: "Dummy mail template",
        }]],
        res_id: 42,
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_MailTemplate_send').length,
        1,
        "should have activity mail template name send button"
    );

    document.querySelector('.o_MailTemplate_send').click();
    assert.verifySteps(
        ['activity_send_mail'],
        "should have called activity_send_mail rpc"
    );
});

QUnit.test('activity upload document is available', async function (assert) {
    assert.expect(3);

    await this.start();
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'upload_file',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_uploadButton').length,
        1,
        "should have activity upload button"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_FileUploader').length,
        1,
        "should have a file uploader"
    );
});

QUnit.test('activity click on mark as done', async function (assert) {
    assert.expect(4);

    await this.start();
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
    });
    await this.createActivityComponent(activity);

    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_markDoneButton').length,
        1,
        "should have activity Mark as Done button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Activity_markDoneButton').click();
    });
    assert.strictEqual(
        document.querySelectorAll('.o_ActivityMarkDonePopover').length,
        1,
        "should have opened the mark done popover"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Activity_markDoneButton').click();
    });
    assert.strictEqual(
        document.querySelectorAll('.o_ActivityMarkDonePopover').length,
        0,
        "should have closed the mark done popover"
    );
});

QUnit.test('activity click on edit', async function (assert) {
    assert.expect(9);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.context.default_res_id,
            42,
            'Action should have the activity res id as default res id in context'
        );
        assert.strictEqual(
            payload.action.context.default_res_model,
            'res.partner',
            'Action should have the activity res model as default res model in context'
        );
        assert.strictEqual(
            payload.action.type,
            "ir.actions.act_window",
            'Action should be of type "ir.actions.act_window"'
        );
        assert.strictEqual(
            payload.action.res_model,
            "mail.activity",
            'Action should have "mail.activity" as res_model'
        );
        assert.strictEqual(
            payload.action.res_id,
            12,
            'Action should have activity id as res_id'
        );
    });

    await this.start({ env: { bus } });
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        id: 12,
        mailTemplates: [['insert', { id: 1, name: "Dummy mail template" }]],
        res_id: 42,
        res_model: 'res.partner',
    });
    await this.createActivityComponent(activity);
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_editButton').length,
        1,
        "should have activity edit button"
    );

    document.querySelector('.o_Activity_editButton').click();
    assert.verifySteps(
        ['do_action'],
        "should have called 'schedule activity' action correctly"
    );
});

QUnit.test('activity edition', async function (assert) {
    assert.expect(14);

    this.data['mail.activity'].records = [{
        can_write: true,
        icon: 'fa-times',
        id: 12,
        res_id: 42,
        res_model: 'res.partner',
    }];

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.context.default_res_id,
            42,
            'Action should have the activity res id as default res id in context'
        );
        assert.strictEqual(
            payload.action.context.default_res_model,
            'res.partner',
            'Action should have the activity res model as default res model in context'
        );
        assert.strictEqual(
            payload.action.type,
            'ir.actions.act_window',
            'Action should be of type "ir.actions.act_window"'
        );
        assert.strictEqual(
            payload.action.res_model,
            'mail.activity',
            'Action should have "mail.activity" as res_model'
        );
        assert.strictEqual(
            payload.action.res_id,
            12,
            'Action should have activity id as res_id'
        );
        this.data['mail.activity'].records[0].icon = 'fa-check';
        payload.options.on_close();
    });

    await this.start({ env: { bus } });
    const activity = this.env.models['mail.activity'].create(
        this.env.models['mail.activity'].convertData(
            this.data['mail.activity'].records[0]
        )
    );
    await this.createActivityComponent(activity);

    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_editButton',
        "should have activity edit button"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_icon',
        "should have activity icon"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_icon.fa-times',
        "should have initial activity icon"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_icon.fa-check',
        "should not have new activity icon when not edited yet"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Activity_editButton').click();
    });
    assert.verifySteps(
        ['do_action'],
        "should have called 'schedule activity' action correctly"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_icon.fa-times',
        "should no more have initial activity icon once edited"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_icon.fa-check',
        "should now have new activity icon once edited"
    );
});

QUnit.test('activity click on cancel', async function (assert) {
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                assert.step('unlink');
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
                return;
            } else {
                return this._super(...arguments);
            }
        },
    });
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        id: 12,
        mailTemplates: [['insert', {
            id: 1,
            name: "Dummy mail template",
        }]],
        res_id: 42,
        res_model: 'res.partner',
    });

    // Create a parent component to surround the Activity component in order to be able
    // to check that activity component has been destroyed
    class ParentComponent extends Component {
        constructor(...args) {
            super(... args);
            useStore(props => {
                const activity = this.env.models['mail.activity'].get(props.activityLocalId);
                return {
                    activity: activity ? activity.__state : undefined,
                };
            });
        }

        /**
         * @returns {mail.activity}
         */
        get activity() {
            return this.env.models['mail.activity'].get(this.props.activityLocalId);
        }
    }
    ParentComponent.env = this.env;
    Object.assign(ParentComponent, {
        components,
        props: { activityLocalId: String },
        template: xml`
            <div>
                <p>parent</p>
                <t t-if="activity">
                    <Activity activityLocalId="activity.localId"/>
                </t>
            </div>
        `,
    });
    this.component = new ParentComponent(null, { activityLocalId: activity.localId });
    await this.component.mount(this.widget.el);

    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        1,
        "should have activity component"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_cancelButton').length,
        1,
        "should have activity cancel button"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Activity_cancelButton').click()
    );
    assert.verifySteps(
        ['unlink'],
        "should have called unlink rpc after clicking on cancel"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Activity').length,
        0,
        "should no longer display activity after clicking on cancel"
    );
});

});
});
});

});
