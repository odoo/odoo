/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import FormView from 'web.FormView';
import ListView from 'web.ListView';
import testUtils from 'web.test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('Chatter');

QUnit.test('list activity widget with no activity', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const { target: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        arch: '<list><field name="activity_ids" widget="list_activity"/></list>',
        mockRPC: function (route) {
            if (!['/mail/init_messaging', '/mail/load_message_failures'].includes(route)) {
                assert.step(route);
            }
            return this._super(...arguments);
        },
        session: { uid: pyEnv.currentUserId },
    });

    assert.containsOnce(list, '.o_mail_activity .o_activity_color_default');
    assert.strictEqual(list.querySelector('.o_activity_summary').innerText, '');

    assert.verifySteps(['/web/dataset/search_read']);
});

QUnit.test('list activity widget with activities', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [mailActivityId1, mailActivityId2] = pyEnv['mail.activity'].create([{}, {}]);
    const [mailActivityTypeId1, mailActivityTypeId2] = pyEnv['mail.activity.type'].create(
        [{ name: 'Type 1' }, { name: 'Type 2' }],
    );
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_ids: [mailActivityId1, mailActivityId2],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: mailActivityTypeId1,
        activity_type_icon: 'fa-phone',
    });

    pyEnv['res.users'].create({
        activity_ids: [mailActivityId2],
        activity_state: 'planned',
        activity_summary: false,
        activity_type_id: mailActivityTypeId2,
    });

    const { target: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        arch: '<list><field name="activity_ids" widget="list_activity"/></list>',
        mockRPC: function (route) {
            if (!['/mail/init_messaging', '/mail/load_message_failures'].includes(route)) {
                assert.step(route);
            }
            return this._super(...arguments);
        },
    });

    const firstRow = list.querySelector('.o_data_row');
    assert.containsOnce(firstRow, '.o_mail_activity .o_activity_color_today.fa-phone');
    assert.strictEqual(firstRow.querySelector('.o_activity_summary').innerText, 'Call with Al');

    const secondRow = list.querySelectorAll('.o_data_row')[1];
    assert.containsOnce(secondRow, '.o_mail_activity .o_activity_color_planned.fa-clock-o');
    assert.strictEqual(secondRow.querySelector('.o_activity_summary').innerText, 'Type 2');

    assert.verifySteps(['/web/dataset/search_read']);
});

QUnit.test('list activity widget with exception', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailActivityId1 = pyEnv['mail.activity'].create();
    const mailActivityTypeId1 = pyEnv['mail.activity.type'].create();
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_ids: [mailActivityId1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: mailActivityTypeId1,
        activity_exception_decoration: 'warning',
        activity_exception_icon: 'fa-warning',
    });

    const { target: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        arch: '<list><field name="activity_ids" widget="list_activity"/></list>',
        mockRPC: function (route) {
            if (!['/mail/init_messaging', '/mail/load_message_failures'].includes(route)) {
                assert.step(route);
            }
            return this._super(...arguments);
        },
    });

    assert.containsOnce(list, '.o_activity_color_today.text-warning.fa-warning');
    assert.strictEqual(list.querySelector('.o_activity_summary').innerText, 'Warning');

    assert.verifySteps(['/web/dataset/search_read']);
});

QUnit.test('list activity widget: open dropdown', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const [mailActivityTypeId1, mailActivityTypeId2] = pyEnv['mail.activity.type'].create([{}, {}]);
    const [mailActivityId1, mailActivityId2] = pyEnv['mail.activity'].create([
        {
            display_name: "Call with Al",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: mailActivityTypeId1,
        },
        {
            display_name: "Meet FP",
            date_deadline: moment().add(1, 'day').format("YYYY-MM-DD"), // tomorrow
            can_write: true,
            state: "planned",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: mailActivityTypeId2,
        }
    ]);
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_ids: [mailActivityId1, mailActivityId2],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: mailActivityTypeId2,
    });

    const { target: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        arch: `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
        mockRPC: function (route, args) {
            if (!['/mail/init_messaging', '/mail/load_message_failures'].includes(route)) {
                assert.step(args.method || route);
            }
            if (args.method === 'action_feedback') {
                pyEnv['res.users'].write([pyEnv.currentUserId], {
                    activity_ids: [mailActivityId2],
                    activity_state: 'planned',
                    activity_summary: 'Meet FP',
                    activity_type_id: mailActivityTypeId1,
                });
                return Promise.resolve();
            }
            return this._super(route, args);
        },
        intercepts: {
            switch_view: () => assert.step('switch_view'),
        },
    });

    assert.strictEqual(list.querySelector('.o_activity_summary').innerText, 'Call with Al');

    // click on the first record to open it, to ensure that the 'switch_view'
    // assertion is relevant (it won't be opened as there is no action manager,
    // but we'll log the 'switch_view' event)
    await testUtils.dom.click(list.querySelector('.o_data_cell'));

    // from this point, no 'switch_view' event should be triggered, as we
    // interact with the activity widget
    assert.step('open dropdown');
    await testUtils.dom.click(list.querySelector('.o_activity_btn span')); // open the popover
    await testUtils.dom.click(list.querySelector('.o_mark_as_done')); // mark the first activity as done
    await testUtils.dom.click(list.querySelector('.o_activity_popover_done')); // confirm

    assert.strictEqual(list.querySelector('.o_activity_summary').innerText, 'Meet FP');

    assert.verifySteps([
        '/web/dataset/search_read',
        'switch_view',
        'open dropdown',
        'activity_format',
        'action_feedback',
        'read',
    ]);
});

QUnit.test('list activity exception widget with activity', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const [mailActivityTypeId1, mailActivityTypeId2] = pyEnv['mail.activity.type'].create([{}, {}]);
    const [mailActivityId1, mailActivityId2] = pyEnv['mail.activity'].create([
        {
            display_name: "An activity",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: mailActivityTypeId1,
        },
        {
            display_name: "An exception activity",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: mailActivityTypeId2,
        }
    ]);

    pyEnv['res.users'].write([pyEnv.currentUserId], { activity_ids: [mailActivityId1] });
    pyEnv['res.users'].create({
        message_attachment_count: 3,
        display_name: "second partner",
        message_follower_ids: [],
        message_ids: [],
        activity_ids: [mailActivityId2],
        activity_exception_decoration: 'warning',
        activity_exception_icon: 'fa-warning',
    });
    const { target: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        arch: '<tree>' +
                '<field name="activity_exception_decoration" widget="activity_exception"/> ' +
            '</tree>',
    });

    assert.containsN(list, '.o_data_row', 2, "should have two records");
    assert.doesNotHaveClass(list.querySelector('.o_data_row .o_activity_exception_cell div'), 'fa-warning',
        "there is no any exception activity on record");
    assert.hasClass(list.querySelectorAll('.o_data_row .o_activity_exception_cell div')[1], 'fa-warning',
        "there is an exception on a record");
});

QUnit.module('FieldMany2ManyTagsEmail');

QUnit.test('fieldmany2many tags email (edition)', async function (assert) {
    assert.expect(17);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([
        { name: "gold", email: 'coucou@petite.perruche' },
        { name: "silver", email: '' },
    ]);
    const mailMessageId1 = pyEnv['mail.message'].create({
        partner_ids: [resPartnerId1],
    });

    var { target: form } = await start({
        hasView: true,
        View: FormView,
        model: 'mail.message',
        res_id: mailMessageId1,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="body"/>' +
                    '<field name="partner_ids" widget="many2many_tags_email"/>' +
                '</sheet>' +
            '</form>',
        viewOptions: {
            mode: 'edit',
        },
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'res.partner') {
                assert.step(JSON.stringify(args.args[0]));
                assert.ok(args.args[1].includes('email'), "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'res.partner,false,form': '<form string="Types"><field name="name"/><field name="email"/></form>',
        },
    });

    assert.verifySteps([`[${resPartnerId1}]`]);
    assert.containsOnce(form, '.o_field_many2manytags[name="partner_ids"] .badge.o_tag_color_0',
        "should contain one tag");

    // add an other existing tag
    await testUtils.fields.many2one.clickOpenDropdown('partner_ids');
    await testUtils.fields.many2one.searchAndClickItem('partner_ids', { search: 'silver' });

    assert.strictEqual($('.modal-body.o_act_window').length, 1,
        "there should be one modal opened to edit the empty email");
    assert.strictEqual($('.modal-body.o_act_window input[name="name"]').val(), "silver",
        "the opened modal in edit mode should be a form view dialog with the res.partner 14");
    assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
        "there should be an email field in the modal");

    // set the email and save the modal (will rerender the form view)
    await testUtils.fields.editInput($('.modal-body.o_act_window input[name="email"]'), 'coucou@petite.perruche');
    await testUtils.dom.click($('.modal-footer .btn-primary'));

    assert.containsN(form, '.o_field_many2manytags[name="partner_ids"] .badge.o_tag_color_0', 2,
        "should contain the second tag");
    const firstTag = form.querySelector('.o_field_many2manytags[name="partner_ids"] .badge.o_tag_color_0');
    assert.strictEqual(firstTag.querySelector('.o_badge_text').innerText, "gold",
        "tag should only show name");
    assert.hasAttrValue(firstTag.querySelector('.o_badge_text'), 'title', "coucou@petite.perruche",
        "tag should show email address on mouse hover");
    // should have read resPartnerId2 three times: when opening the dropdown, when opening the modal, and
    // after the save
    assert.verifySteps([`[${resPartnerId2}]`, `[${resPartnerId2}]`, `[${resPartnerId2}]`]);
});

QUnit.test('many2many_tags_email widget can load more than 40 records', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const messagePartnerIds = [];
    for (let i = 100; i < 200; i++) {
        messagePartnerIds.push(pyEnv['res.partner'].create({ display_name: `partner${i}` }));
    }
    const mailMessageId1 = pyEnv['mail.message'].create({
        partner_ids: messagePartnerIds,
    });

    const { click, target: form } = await start({
        hasView: true,
        View: FormView,
        model: 'mail.message',
        arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
        res_id: mailMessageId1,
    });

    assert.strictEqual(form.querySelectorAll('.o_field_widget[name="partner_ids"] .badge').length, 100);

    await click('.o_form_button_edit');

    assert.hasClass(form.querySelector('.o_form_view'), 'o_form_editable');

    // add a record to the relation
    await testUtils.fields.many2one.clickOpenDropdown('partner_ids');
    await testUtils.fields.many2one.clickHighlightedItem('partner_ids');

    assert.strictEqual(form.querySelectorAll('.o_field_widget[name="partner_ids"] .badge').length, 101);
});

});
