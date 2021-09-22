/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';
import { ROUTES_TO_IGNORE } from '@mail/../tests/helpers/webclient_setup';

import testUtils from 'web.test_utils';
import { clickEdit, patchWithCleanup, selectDropdownItem } from '@web/../tests/helpers/utils';
import { ListController } from "@web/views/list/list_controller";

QUnit.module('mail', {}, function () {
QUnit.module('Chatter');

QUnit.test('list activity widget with no activity', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const views = {
        'res.users,false,list': '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== 'get_views' &&
                !['/mail/init_messaging', '/mail/load_message_failures', '/bus/im_status', ...ROUTES_TO_IGNORE].includes(route)
            ) {
                assert.step(route);
            }
        },
        serverData: { views },
        session: { uid: pyEnv.currentUserId },
    });
    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });

    assert.containsOnce(document.body, '.o_mail_activity .o_activity_color_default');
    assert.strictEqual(document.querySelector('.o_activity_summary').innerText, '');

    assert.verifySteps(['/web/dataset/call_kw/res.users/web_search_read']);
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
    const views = {
        'res.users,false,list': '<list><field name="activity_ids" widget="list_activity"/></list>',
    };

    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== 'get_views' &&
                !['/mail/init_messaging', '/mail/load_message_failures', '/bus/im_status', ...ROUTES_TO_IGNORE].includes(route)
            ) {
                assert.step(route);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });

    const firstRow = document.querySelector('.o_data_row');
    assert.containsOnce(firstRow, '.o_mail_activity .o_activity_color_today.fa-phone');
    assert.strictEqual(firstRow.querySelector('.o_activity_summary').innerText, 'Call with Al');

    const secondRow = document.querySelectorAll('.o_data_row')[1];
    assert.containsOnce(secondRow, '.o_mail_activity .o_activity_color_planned.fa-clock-o');
    assert.strictEqual(secondRow.querySelector('.o_activity_summary').innerText, 'Type 2');

    assert.verifySteps(['/web/dataset/call_kw/res.users/web_search_read']);
});

QUnit.test('list activity widget with exception', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailActivityId1 = pyEnv['mail.activity'].create({});
    const mailActivityTypeId1 = pyEnv['mail.activity.type'].create({});
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_ids: [mailActivityId1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: mailActivityTypeId1,
        activity_exception_decoration: 'warning',
        activity_exception_icon: 'fa-warning',
    });

    const views = {
        'res.users,false,list': '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== 'get_views' &&
                !['/mail/init_messaging', '/mail/load_message_failures', '/bus/im_status', ...ROUTES_TO_IGNORE].includes(route)
            ) {
                assert.step(route);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });

    assert.containsOnce(document.body, '.o_activity_color_today.text-warning.fa-warning');
    assert.strictEqual(document.querySelector('.o_activity_summary').innerText, 'Warning');

    assert.verifySteps(['/web/dataset/call_kw/res.users/web_search_read']);
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

    const views = {
        'res.users,false,list': '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== 'get_views' &&
                !['/mail/init_messaging', '/mail/load_message_failures', '/bus/im_status', ...ROUTES_TO_IGNORE].includes(route)
            ) {
                assert.step(args.method || route);
            }
            if (args.method === 'action_feedback') {
                pyEnv['res.users'].write([pyEnv.currentUserId], {
                    activity_ids: [mailActivityId2],
                    activity_state: 'planned',
                    activity_summary: 'Meet FP',
                    activity_type_id: mailActivityTypeId1,
                });
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
        serverData: { views },
    });

    patchWithCleanup(ListController.prototype, {
        setup() {
            this._super();
            const selectRecord = this.props.selectRecord;
            this.props.selectRecord = (...args) => {
                assert.step(`select_record ${JSON.stringify(args)}`);
                return selectRecord(...args);
            }
        }
    });

    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });

    assert.strictEqual(document.querySelector('.o_activity_summary').innerText, 'Call with Al');

    // click on the first record to open it, to ensure that the 'switch_view'
    // assertion is relevant (it won't be opened as there is no action manager,
    // but we'll log the 'switch_view' event)
    await testUtils.dom.click(document.querySelector('.o_data_cell'));

    // from this point, no 'switch_view' event should be triggered, as we
    // interact with the activity widget
    assert.step('open dropdown');
    await testUtils.dom.click(document.querySelector('.o_activity_btn span')); // open the popover
    await testUtils.dom.click(document.querySelector('.o_mark_as_done')); // mark the first activity as done
    await testUtils.dom.click(document.querySelector('.o_activity_popover_done')); // confirm

    assert.strictEqual(document.querySelector('.o_activity_summary').innerText, 'Meet FP');

    assert.verifySteps([
        'web_search_read',
        'select_record [2,{"activeIds":[2]}]',
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
    const views = {
        'res.users,false,list':
            `<tree>
                <field name="activity_exception_decoration" widget="activity_exception"/>
            </tree>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });

    assert.containsN(document.body, '.o_data_row', 2, "should have two records");
    assert.doesNotHaveClass(document.querySelector('.o_data_row .o_activity_exception_cell div div'), 'fa-warning',
        "there is no any exception activity on record");
    assert.hasClass(document.querySelectorAll('.o_data_row .o_activity_exception_cell div div')[1], 'fa-warning',
        "there is an exception on a record");
});

QUnit.test('list activity widget: done the activity with "ENTER" keyboard shortcut', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailActivityTypeId1 = pyEnv['mail.activity.type'].create({});
    const mailActivityId1 = pyEnv['mail.activity'].create([
        {
            display_name: "Call with Al",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: mailActivityTypeId1,
        }
    ]);
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_ids: [mailActivityId1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: mailActivityTypeId1,
    });
    const views = {
        'res.users,false,list':
            `<list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });

    await testUtils.dom.click(document.querySelector('.o_activity_btn span'));
    await testUtils.dom.click(document.querySelector('.o_mark_as_done'));
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_state: '',
    });
    await testUtils.dom.triggerEvent(
        document.querySelector('.o_activity_popover_done'),
        'keydown',
        { key: 'Enter' },
    );

    assert.containsOnce(document.body, '.o_mail_activity .o_activity_color_default');
});

QUnit.test('list activity widget: done and schedule the next activity with "ENTER" keyboard shortcut', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailActivityTypeId1 = pyEnv['mail.activity.type'].create({});
    const mailActivityId1 = pyEnv['mail.activity'].create([
        {
            display_name: "Call with Al",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: mailActivityTypeId1,
        }
    ]);
    pyEnv['res.users'].write([pyEnv.currentUserId], {
        activity_ids: [mailActivityId1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: mailActivityTypeId1,
    });

    const views = {
        'res.users,false,list':
            `<list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { env, openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.users',
        views: [[false, 'list']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(action.name, "Schedule an Activity", 'should do a do_action with correct parameters');
            return this._super(...arguments);
        }
    });

    await testUtils.dom.click(document.querySelector('.o_activity_btn span'));
    await testUtils.dom.click(document.querySelector('.o_mark_as_done'));
    await testUtils.dom.triggerEvent(
        document.querySelector('.o_activity_popover_done_next'),
        'keydown',
        { key: 'Enter' },
    );
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
    const views = {
        'mail.message,false,form':
            '<form string="Partners">' +
                '<sheet>' +
                    '<field name="body"/>' +
                    '<field name="partner_ids" widget="many2many_tags_email"/>' +
                '</sheet>' +
            '</form>',
        'res.partner,false,form': '<form string="Types"><field name="name"/><field name="email"/></form>',
    };
    var { openView } = await start({
        serverData: { views },
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'res.partner') {
                assert.step(JSON.stringify(args.args[0]));
                assert.ok(args.args[1].includes('email'), "should read the email");
            }
        },
    });
    await openView(
        {
            res_id: mailMessageId1,
            res_model: 'mail.message',
            views: [[false, 'form']],
        },
        {
            mode: 'edit',
        },
    );

    assert.verifySteps([`[${resPartnerId1}]`]);
    assert.containsOnce(document.body, '.o_field_many2manytags[name="partner_ids"] .badge.o_tag_color_0',
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

    assert.containsN(document.body, '.o_field_many2manytags[name="partner_ids"] .badge.o_tag_color_0', 2,
        "should contain the second tag");
    const firstTag = document.querySelector('.o_field_many2manytags[name="partner_ids"] .badge.o_tag_color_0');
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
    const views = {
        'mail.message,false,form': '<form><field name="partner_ids" widget="many2many_tags"/></form>',
    };
    var { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_id: mailMessageId1,
        res_model: 'mail.message',
        views: [[false, 'form']],
    });

    assert.strictEqual(document.querySelectorAll('.o_field_widget[name="partner_ids"] .badge').length, 100);

    await clickEdit(document.body);

    assert.containsOnce(document.body, '.o_form_editable');

    // add a record to the relation
    await selectDropdownItem(document.body, 'partner_ids', "Public user");

    assert.strictEqual(document.querySelectorAll('.o_field_widget[name="partner_ids"] .badge').length, 101);
});

});
