odoo.define('mail.chatter_tests', function (require) {
"use strict";

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

var FormView = require('web.FormView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('Chatter', {
    beforeEach: function () {
        beforeEach(this);

        this.data['res.partner'].records.push({ id: 11, im_status: 'online' });
        this.data['mail.activity.type'].records.push(
            { id: 1, name: "Type 1" },
            { id: 2, name: "Type 2" },
            { id: 3, name: "Type 3", category: 'upload_file' },
            { id: 4, name: "Exception", decoration_type: "warning", icon: "fa-warning" }
        );
        this.data['ir.attachment'].records.push(
            {
                id: 1,
                mimetype: 'image/png',
                name: 'filename.jpg',
                res_id: 7,
                res_model: 'res.users',
                type: 'url',
            },
            {
                id: 2,
                mimetype: "application/x-msdos-program",
                name: "file2.txt",
                res_id: 7,
                res_model: 'res.users',
                type: 'binary',
            },
            {
                id: 3,
                mimetype: "application/x-msdos-program",
                name: "file3.txt",
                res_id: 5,
                res_model: 'res.users',
                type: 'binary',
            },
        );
        Object.assign(this.data['res.users'].fields, {
            activity_exception_decoration: {
                string: 'Decoration',
                type: 'selection',
                selection: [['warning', 'Alert'], ['danger', 'Error']],
            },
            activity_exception_icon: {
                string: 'icon',
                type: 'char',
            },
            activity_ids: {
                string: 'Activities',
                type: 'one2many',
                relation: 'mail.activity',
                relation_field: 'res_id',
            },
            activity_state: {
                string: 'State',
                type: 'selection',
                selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
            },
            activity_summary: {
                string: "Next Activity Summary",
                type: 'char',
            },
            activity_type_icon: {
                string: "Activity Type Icon",
                type: 'char',
            },
            activity_type_id: {
                string: "Activity type",
                type: "many2one",
                relation: "mail.activity.type",
            },
            foo: { string: "Foo", type: "char", default: "My little Foo Value" },
            message_attachment_count: {
                string: 'Attachment count',
                type: 'integer',
            },
            message_follower_ids: {
                string: "Followers",
                type: "one2many",
                relation: 'mail.followers',
                relation_field: "res_id",
            },
            message_ids: {
                string: "messages",
                type: "one2many",
                relation: 'mail.message',
                relation_field: "res_id",
            },
        });
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('list activity widget with no activity', async function (assert) {
    assert.expect(5);

    const { widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: '<list><field name="activity_ids" widget="list_activity"/></list>',
        mockRPC: function (route) {
            assert.step(route);
            return this._super(...arguments);
        },
        session: { uid: 2 },
    });

    assert.containsOnce(list, '.o_mail_activity .o_activity_color_default');
    assert.strictEqual(list.$('.o_activity_summary').text(), '');

    assert.verifySteps([
        '/web/dataset/search_read',
        '/mail/init_messaging',
    ]);

    list.destroy();
});

QUnit.test('list activity widget with activities', async function (assert) {
    assert.expect(7);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    Object.assign(currentUser, {
        activity_ids: [1, 4],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: 3,
        activity_type_icon: 'fa-phone',
    });

    this.data['res.users'].records.push({
        id: 44,
        activity_ids: [2],
        activity_state: 'planned',
        activity_summary: false,
        activity_type_id: 2,
    });

    const { widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: '<list><field name="activity_ids" widget="list_activity"/></list>',
        mockRPC: function (route) {
            assert.step(route);
            return this._super(...arguments);
        },
    });

    const $firstRow = list.$('.o_data_row:first');
    assert.containsOnce($firstRow, '.o_mail_activity .o_activity_color_today.fa-phone');
    assert.strictEqual($firstRow.find('.o_activity_summary').text(), 'Call with Al');

    const $secondRow = list.$('.o_data_row:nth(1)');
    assert.containsOnce($secondRow, '.o_mail_activity .o_activity_color_planned.fa-clock-o');
    assert.strictEqual($secondRow.find('.o_activity_summary').text(), 'Type 2');

    assert.verifySteps([
        '/web/dataset/search_read',
        '/mail/init_messaging',
    ]);

    list.destroy();
});

QUnit.test('list activity widget with exception', async function (assert) {
    assert.expect(5);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    Object.assign(currentUser, {
        activity_ids: [1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: 3,
        activity_exception_decoration: 'warning',
        activity_exception_icon: 'fa-warning',
    });

    const { widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: '<list><field name="activity_ids" widget="list_activity"/></list>',
        mockRPC: function (route) {
            assert.step(route);
            return this._super(...arguments);
        },
    });

    assert.containsOnce(list, '.o_activity_color_today.text-warning.fa-warning');
    assert.strictEqual(list.$('.o_activity_summary').text(), 'Warning');

    assert.verifySteps([
        '/web/dataset/search_read',
        '/mail/init_messaging',
    ]);

    list.destroy();
});

QUnit.test('list activity widget: open dropdown', async function (assert) {
    assert.expect(10);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    Object.assign(currentUser, {
        activity_ids: [1, 4],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: 3,
    });
    this.data['mail.activity'].records.push(
        {
            id: 1,
            display_name: "Call with Al",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: this.data.currentUserId,
            create_uid: this.data.currentUserId,
            activity_type_id: 3,
        },
        {
            id: 4,
            display_name: "Meet FP",
            date_deadline: moment().add(1, 'day').format("YYYY-MM-DD"), // tomorrow
            can_write: true,
            state: "planned",
            user_id: this.data.currentUserId,
            create_uid: this.data.currentUserId,
            activity_type_id: 1,
        }
    );

    const { env, widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: `
            <list>
                <field name="foo"/>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
        mockRPC: function (route, args) {
            assert.step(args.method || route);
            if (args.method === 'action_feedback') {
                const currentUser = this.data['res.users'].records.find(user =>
                    user.id === env.messaging.currentUser.id
                );
                Object.assign(currentUser, {
                    activity_ids: [4],
                    activity_state: 'planned',
                    activity_summary: 'Meet FP',
                    activity_type_id: 1,
                });
                return Promise.resolve();
            }
            return this._super(route, args);
        },
        intercepts: {
            switch_view: () => assert.step('switch_view'),
        },
    });

    assert.strictEqual(list.$('.o_activity_summary').text(), 'Call with Al');

    // click on the first record to open it, to ensure that the 'switch_view'
    // assertion is relevant (it won't be opened as there is no action manager,
    // but we'll log the 'switch_view' event)
    await testUtils.dom.click(list.$('.o_data_cell:first'));

    // from this point, no 'switch_view' event should be triggered, as we
    // interact with the activity widget
    assert.step('open dropdown');
    await testUtils.dom.click(list.$('.o_activity_btn span')); // open the popover
    await testUtils.dom.click(list.$('.o_mark_as_done:first')); // mark the first activity as done
    await testUtils.dom.click(list.$('.o_activity_popover_done')); // confirm

    assert.strictEqual(list.$('.o_activity_summary').text(), 'Meet FP');

    assert.verifySteps([
        '/web/dataset/search_read',
        '/mail/init_messaging',
        'switch_view',
        'open dropdown',
        'activity_format',
        'action_feedback',
        'read',
    ]);

    list.destroy();
});

QUnit.test('list activity exception widget with activity', async function (assert) {
    assert.expect(3);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    currentUser.activity_ids = [1];
    this.data['res.users'].records.push({
        id: 13,
        message_attachment_count: 3,
        display_name: "second partner",
        foo: "Tommy",
        message_follower_ids: [],
        message_ids: [],
        activity_ids: [2],
        activity_exception_decoration: 'warning',
        activity_exception_icon: 'fa-warning',
    });
    this.data['mail.activity'].records.push(
        {
            id: 1,
            display_name: "An activity",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: 2,
            create_uid: 2,
            activity_type_id: 1,
        },
        {
            id: 2,
            display_name: "An exception activity",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: 2,
            create_uid: 2,
            activity_type_id: 4,
        }
    );

    const { widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: '<tree>' +
                '<field name="foo"/>' +
                '<field name="activity_exception_decoration" widget="activity_exception"/> ' +
            '</tree>',
    });

    assert.containsN(list, '.o_data_row', 2, "should have two records");
    assert.doesNotHaveClass(list.$('.o_data_row:eq(0) .o_activity_exception_cell div'), 'fa-warning',
        "there is no any exception activity on record");
    assert.hasClass(list.$('.o_data_row:eq(1) .o_activity_exception_cell div'), 'fa-warning',
        "there is an exception on a record");

    list.destroy();
});

QUnit.module('FieldMany2ManyTagsEmail', {
    beforeEach() {
        beforeEach(this);

        Object.assign(this.data['res.users'].fields, {
            timmy: { string: "pokemon", type: "many2many", relation: 'partner_type' },
        });
        this.data['res.users'].records.push({
            id: 11,
            display_name: "first record",
            timmy: [],
        });
        Object.assign(this.data, {
            partner_type: {
                fields: {
                    name: { string: "Partner Type", type: "char" },
                    email: { string: "Email", type: "char" },
                },
                records: [],
            },
        });
        this.data['partner_type'].records.push(
            { id: 12, display_name: "gold", email: 'coucou@petite.perruche' },
            { id: 14, display_name: "silver", email: '' }
        );
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('fieldmany2many tags email', function (assert) {
    assert.expect(13);
    var done = assert.async();

    const user11 = this.data['res.users'].records.find(user => user.id === 11);
    user11.timmy = [12, 14];

    // the modals need to be closed before the form view rendering
    start({
        hasView: true,
        View: FormView,
        model: 'res.users',
        data: this.data,
        res_id: 11,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags_email"/>' +
                '</sheet>' +
            '</form>',
        viewOptions: {
            mode: 'edit',
        },
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'partner_type') {
                assert.step(JSON.stringify(args.args[0]));
                assert.deepEqual(args.args[1], ['display_name', 'email'], "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner_type,false,form': '<form string="Types"><field name="display_name"/><field name="email"/></form>',
        },
    }).then(async function ({ widget: form }) {
        // should read it 3 times (1 with the form view, one with the form dialog and one after save)
        assert.verifySteps(['[12,14]', '[14]', '[14]']);
        await testUtils.nextTick();
        assert.containsN(form, '.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0', 2,
            "two tags should be present");
        var firstTag = form.$('.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0').first();
        assert.strictEqual(firstTag.find('.o_badge_text').text(), "gold",
            "tag should only show display_name");
        assert.hasAttrValue(firstTag.find('.o_badge_text'), 'title', "coucou@petite.perruche",
            "tag should show email address on mouse hover");
        form.destroy();
        done();
    });
    testUtils.nextTick().then(function () {
        assert.strictEqual($('.modal-body.o_act_window').length, 1,
            "there should be one modal opened to edit the empty email");
        assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
            "the opened modal should be a form view dialog with the partner_type 14");
        assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
            "there should be an email field in the modal");

        // set the email and save the modal (will render the form view)
        testUtils.fields.editInput($('.modal-body.o_act_window input[name="email"]'), 'coucou@petite.perruche');
        testUtils.dom.click($('.modal-footer .btn-primary'));
    });

});

QUnit.test('fieldmany2many tags email (edition)', async function (assert) {
    assert.expect(15);

    const user11 = this.data['res.users'].records.find(user => user.id === 11);
    user11.timmy = [12];

    var { widget: form } = await start({
        hasView: true,
        View: FormView,
        model: 'res.users',
        data: this.data,
        res_id: 11,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags_email"/>' +
                '</sheet>' +
            '</form>',
        viewOptions: {
            mode: 'edit',
        },
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'partner_type') {
                assert.step(JSON.stringify(args.args[0]));
                assert.deepEqual(args.args[1], ['display_name', 'email'], "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner_type,false,form': '<form string="Types"><field name="display_name"/><field name="email"/></form>',
        },
    });

    assert.verifySteps(['[12]']);
    assert.containsOnce(form, '.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0',
        "should contain one tag");

    // add an other existing tag
    await testUtils.fields.many2one.clickOpenDropdown('timmy');
    await testUtils.fields.many2one.clickHighlightedItem('timmy');

    assert.strictEqual($('.modal-body.o_act_window').length, 1,
        "there should be one modal opened to edit the empty email");
    assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
        "the opened modal in edit mode should be a form view dialog with the partner_type 14");
    assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
        "there should be an email field in the modal");

    // set the email and save the modal (will rerender the form view)
    await testUtils.fields.editInput($('.modal-body.o_act_window input[name="email"]'), 'coucou@petite.perruche');
    await testUtils.dom.click($('.modal-footer .btn-primary'));

    assert.containsN(form, '.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0', 2,
        "should contain the second tag");
    // should have read [14] three times: when opening the dropdown, when opening the modal, and
    // after the save
    assert.verifySteps(['[14]', '[14]', '[14]']);

    form.destroy();
});

QUnit.test('many2many_tags_email widget can load more than 40 records', async function (assert) {
    assert.expect(3);

    const user11 = this.data['res.users'].records.find(user => user.id === 11);
    this.data['res.users'].fields.partner_ids = { string: "Partner", type: "many2many", relation: 'res.users' };
    user11.partner_ids = [];
    for (let i = 100; i < 200; i++) {
        this.data['res.users'].records.push({ id: i, display_name: `partner${i}` });
        user11.partner_ids.push(i);
    }

    const { widget: form } = await start({
        hasView: true,
        View: FormView,
        model: 'res.users',
        data: this.data,
        arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
        res_id: 11,
    });

    assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge').length, 100);

    await testUtils.form.clickEdit(form);

    assert.hasClass(form.$('.o_form_view'), 'o_form_editable');

    // add a record to the relation
    await testUtils.fields.many2one.clickOpenDropdown('partner_ids');
    await testUtils.fields.many2one.clickHighlightedItem('partner_ids');

    assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge').length, 101);

    form.destroy();
});

});

});
