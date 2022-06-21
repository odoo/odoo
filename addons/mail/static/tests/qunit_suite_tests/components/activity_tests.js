/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';

import { date_to_str } from 'web.time';
import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity_tests.js');

QUnit.test('activity simplest layout', async function (assert) {
    assert.expect(12);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        note: 'There is no good or bad note',
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    const today = new Date();
    const fiveDaysFromNow = new Date();
    fiveDaysFromNow.setDate(today.getDate() + 5);
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        date_deadline: date_to_str(fiveDaysFromNow),
        res_id: resPartnerId1,
        res_model: 'res.partner',
        state: 'planned',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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
        document.querySelector('.o_Activity_dueDateText').classList.contains('text-success'),
        "activity delay should have the right color modifier class (text-success)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "Due in 5 days:",
        "activity delay should have 'Due in 5 days:' as label"
    );
});

QUnit.test('activity info layout when planned tomorrow', async function (assert) {
    assert.expect(4);

    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        date_deadline: date_to_str(tomorrow),
        res_id: resPartnerId1,
        res_model: 'res.partner',
        state: 'planned',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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
        document.querySelector('.o_Activity_dueDateText').classList.contains('text-success'),
        "activity delay should have the right color modifier class (text-success)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        'Tomorrow:',
        "activity delay should have 'Tomorrow:' as label"
    );
});

QUnit.test('activity info layout when planned today', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        date_deadline: date_to_str(new Date()),
        res_id: resPartnerId1,
        res_model: 'res.partner',
        state: 'today',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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
        document.querySelector('.o_Activity_dueDateText').classList.contains('text-warning'),
        "activity delay should have the right color modifier class (text-warning)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "Today:",
        "activity delay should have 'Today:' as label"
    );
});

QUnit.test('activity info layout when planned yesterday', async function (assert) {
    assert.expect(4);

    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        date_deadline: date_to_str(yesterday),
        res_id: resPartnerId1,
        res_model: 'res.partner',
        state: 'overdue',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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
        document.querySelector('.o_Activity_dueDateText').classList.contains('text-danger'),
        "activity delay should have the right color modifier class (text-danger)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "Yesterday:",
        "activity delay should have 'Yesterday:' as label"
    );
});

QUnit.test('activity info layout when planned before yesterday', async function (assert) {
    assert.expect(4);

    const today = new Date();
    const fiveDaysBeforeNow = new Date();
    fiveDaysBeforeNow.setDate(today.getDate() - 5);
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        date_deadline: date_to_str(fiveDaysBeforeNow),
        res_id: resPartnerId1,
        res_model: 'res.partner',
        state: 'overdue',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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
        document.querySelector('.o_Activity_dueDateText').classList.contains('text-danger'),
        "activity delay should have the right color modifier class (text-danger)"
    );
    assert.strictEqual(
        document.querySelector('.o_Activity_dueDateText').textContent,
        "5 days overdue:",
        "activity delay should have '5 days overdue:' as label"
    );
});

QUnit.test('activity with a summary layout', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        summary: 'test summary',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        activity_type_id: 1,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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
        "Email",
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

    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const resUsersId1 = pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    pyEnv['mail.activity'].create({
        create_date: date_to_str(today),
        create_uid: resUsersId1,
        date_deadline: date_to_str(tomorrow),
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    await click('.o_Activity_detailsButton');
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        1,
        "activity details should be visible after clicking on details button"
    );

    await click('.o_Activity_detailsButton');
    assert.strictEqual(
        document.querySelectorAll('.o_Activity_details').length,
        0,
        "activity details should no longer be visible after clicking again on details button"
    );
});

QUnit.test('activity details layout', async function (assert) {
    assert.expect(11);

    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    const pyEnv = await startServer();
    const resUsersId1 = pyEnv['res.users'].create({ name: 'Pauvre pomme' });
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_type_id: emailActivityTypeId,
        create_date: date_to_str(today),
        create_uid: resUsersId1,
        date_deadline: date_to_str(tomorrow),
        res_id: resPartnerId1,
        res_model: 'res.partner',
        state: 'planned',
        user_id: resUsersId1,
    });
    const { click, openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    await click('.o_Activity_detailsButton');
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
        "Email",
        "activity details type should be 'Email'"
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailTemplateId1 = pyEnv['mail.template'].create({ name: "Dummy mail template" });
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_type_id: emailActivityTypeId,
        mail_template_ids: [mailTemplateId1],
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailTemplateId1 = pyEnv['mail.template'].create({ name: "Dummy mail template" });
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_type_id: emailActivityTypeId,
        mail_template_ids: [mailTemplateId1],
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { env, openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('do_action');
            assert.strictEqual(
                action.context.default_res_id,
                resPartnerId1,
                'Action should have the activity res id as default res id in context'
            );
            assert.strictEqual(
                action.context.default_model,
                'res.partner',
                'Action should have the activity res model as default model in context'
            );
            assert.ok(
                action.context.default_use_template,
                'Action should have true as default use_template in context'
            );
            assert.strictEqual(
                action.context.default_template_id,
                mailTemplateId1,
                'Action should have the selected mail template id as default template id in context'
            );
            assert.strictEqual(
                action.type,
                "ir.actions.act_window",
                'Action should be of type "ir.actions.act_window"'
            );
            assert.strictEqual(
                action.res_model,
                "mail.compose.message",
                'Action should have "mail.compose.message" as res_model'
            );
        },
    });
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailTemplateId1 = pyEnv['mail.template'].create({ name: "Dummy mail template" });
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_type_id: emailActivityTypeId,
        mail_template_ids: [mailTemplateId1],
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'activity_send_mail') {
                assert.step('activity_send_mail');
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], resPartnerId1);
                assert.strictEqual(args.args[1], mailTemplateId1);
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const uploadActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Upload Document']])[0];
    pyEnv['mail.activity'].create({
        activity_category: 'upload_file',
        activity_type_id: uploadActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { messaging, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
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
    assert.ok(
        messaging.models['Chatter'].all()[0].activityBoxView.activityViews[0].fileUploader,
        "should have a file uploader"
    );
});

QUnit.test('activity click on mark as done', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_category: 'default',
        activity_type_id: emailActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
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

    await click('.o_Activity_markDoneButton');
    assert.strictEqual(
        document.querySelectorAll('.o_ActivityMarkDonePopoverContent').length,
        1,
        "should have opened the mark done popover"
    );

    await click('.o_Activity_markDoneButton');
    assert.strictEqual(
        document.querySelectorAll('.o_ActivityMarkDonePopoverContent').length,
        0,
        "should have closed the mark done popover"
    );
});

QUnit.test('activity mark as done popover should focus feedback input on open [REQUIRE FOCUS]', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_category: 'default',
        activity_type_id: emailActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_markDoneButton',
        "should have activity Mark as Done button"
    );

    await click('.o_Activity_markDoneButton');
    assert.strictEqual(
        document.querySelector('.o_ActivityMarkDonePopoverContent_feedback'),
        document.activeElement,
        "the popover textarea should have the focus"
    );
});

QUnit.test('activity click on edit', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailTemplateId1 = pyEnv['mail.template'].create({ name: "Dummy mail template" });
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    const mailActivityId1 = pyEnv['mail.activity'].create({
        activity_type_id: emailActivityTypeId,
        can_write: true,
        mail_template_ids: [mailTemplateId1],
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, env, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('do_action');
            assert.strictEqual(
                action.context.default_res_id,
                resPartnerId1,
                'Action should have the activity res id as default res id in context'
            );
            assert.strictEqual(
                action.context.default_res_model,
                'res.partner',
                'Action should have the activity res model as default res model in context'
            );
            assert.strictEqual(
                action.type,
                "ir.actions.act_window",
                'Action should be of type "ir.actions.act_window"'
            );
            assert.strictEqual(
                action.res_model,
                "mail.activity",
                'Action should have "mail.activity" as res_model'
            );
            assert.strictEqual(
                action.res_id,
                mailActivityId1,
                'Action should have activity id as res_id'
            );
            return this._super(...arguments);
        },
    });
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

    await click('.o_Activity_editButton');
    assert.verifySteps(
        ['do_action'],
        "should have called 'schedule activity' action correctly"
    );
});

QUnit.test('activity edition', async function (assert) {
    assert.expect(14);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailActivityId1 = pyEnv['mail.activity'].create({
        can_write: true,
        icon: 'fa-times',
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, env, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step('do_action');
            assert.strictEqual(
                action.context.default_res_id,
                resPartnerId1,
                'Action should have the activity res id as default res id in context'
            );
            assert.strictEqual(
                action.context.default_res_model,
                'res.partner',
                'Action should have the activity res model as default res model in context'
            );
            assert.strictEqual(
                action.type,
                'ir.actions.act_window',
                'Action should be of type "ir.actions.act_window"'
            );
            assert.strictEqual(
                action.res_model,
                'mail.activity',
                'Action should have "mail.activity" as res_model'
            );
            assert.strictEqual(
                action.res_id,
                mailActivityId1,
                'Action should have activity id as res_id'
            );
            pyEnv['mail.activity'].write([mailActivityId1], { icon: 'fa-check' });
            options.onClose();
        },
    });
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

    await click('.o_Activity_editButton');
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    const mailActivityId1 = pyEnv['mail.activity'].create({
        activity_type_id: emailActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                assert.step('unlink');
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], mailActivityId1);
            }
        },
    });
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
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

    await click('.o_Activity_cancelButton');
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

QUnit.test('activity mark done popover close on ESCAPE', async function (assert) {
    // This test is not in activity_mark_done_popover_tests.js as it requires the activity mark done
    // component to have a parent in order to allow testing interactions the popover.
    assert.expect(2);
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_category: 'default',
        activity_type_id: emailActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    await click('.o_Activity_markDoneButton');
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent',
        "Popover component should be present"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ActivityMarkDonePopoverContent`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_ActivityMarkDonePopoverContent',
        "ESCAPE pressed should have closed the mark done popover"
    );
});

QUnit.test('activity mark done popover click on discard', async function (assert) {
    // This test is not in activity_mark_done_popover_tests.js as it requires the activity mark done
    // component to have a parent in order to allow testing interactions the popover.
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_category: 'default',
        activity_type_id: emailActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    await click('.o_Activity_markDoneButton');
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent',
        "Popover component should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_discardButton',
        "Popover component should contain the discard button"
    );
    await click('.o_ActivityMarkDonePopoverContent_discardButton');
    assert.containsNone(
        document.body,
        '.o_ActivityMarkDonePopoverContent',
        "Discard button clicked should have closed the mark done popover"
    );
});

QUnit.test('data-oe-id & data-oe-model link redirection on click', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    pyEnv['mail.activity'].create({
        activity_category: 'default',
        activity_type_id: emailActivityTypeId,
        can_write: true,
        note: `<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>`,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { env, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(
                action.type,
                'ir.actions.act_window',
                "action should open view"
            );
            assert.strictEqual(
                action.res_model,
                'some.model',
                "action should open view on 'some.model' model"
            );
            assert.strictEqual(
                action.res_id,
                250,
                "action should open view on 250"
            );
            assert.step('do-action:openFormView_some.model_250');
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Activity_note',
        "activity should have a note"
    );
    assert.containsOnce(
        document.querySelector('.o_Activity_note'),
        'a',
        "activity note should have a link"
    );

    document.querySelector(`.o_Activity_note a`).click();
    assert.verifySteps(
        ['do-action:openFormView_some.model_250'],
        "should have open form view on related record after click on link"
    );
});

QUnit.test('button related to file uploading is replaced when updating activity type from "Upload Document" to "Email"', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const uploadActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Upload document']])[0];
    const emailActivityTypeId = pyEnv['mail.activity.type'].search([['name', '=', 'Email']])[0];
    const mailActivityId1 = pyEnv['mail.activity'].create({
        activity_category: 'upload_file',
        activity_type_id: uploadActivityTypeId,
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { messaging, openView } = await start();
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    // Update the record server side then fetch updated data in order to
    // emulate what happens when using the form view.
    pyEnv['mail.activity'].write([mailActivityId1], {
        activity_category: 'default',
        activity_type_id: emailActivityTypeId,
    });
    await afterNextRender(async () => {
        const activity = messaging.models['Activity'].findFromIdentifyingData({ id: mailActivityId1 });
        await activity.fetchAndUpdate();
    });
    assert.containsOnce(
        document.body,
        '.o_Activity_markDoneButton',
        "should have a mark done button when changing activity type from 'Upload Document' to 'Email'"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_uploadButton',
        "should not have an upload button after changing the activity type from 'Upload Document' to 'Email'"
    );
});

});
});
