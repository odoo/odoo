odoo.define('mail.chatter_mobile_tests', function (require) {
"use strict";

const mailTestUtils = require('mail.testUtils');

const FormView = require('web.FormView');
const testUtils = require('web.test_utils');
const createView = testUtils.createView;

QUnit.module('mail mobile', {}, function () {

QUnit.module('Chatter', {
    beforeEach: function () {

        this.services = mailTestUtils.getMailServices();
        this.data = {
            'res.partner': {
                fields: {
                    im_status: {
                        string: "im_status",
                        type: "char",
                    }
                },
                records: [{
                    id: 1,
                    im_status: 'online',
                }]
            },
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
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
                    activity_ids: {
                        string: 'Activities',
                        type: 'one2many',
                        relation: 'mail.activity',
                        relation_field: 'res_id',
                    },
                    activity_exception_decoration: {
                        string: 'Decoration',
                        type: 'selection',
                        selection: [['warning', 'Alert'], ['danger', 'Error']],
                    },
                    activity_exception_icon: {
                        string: 'icon',
                        type: 'char',
                    },
                    activity_state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    message_attachment_count: {
                        string: 'Attachment count',
                        type: 'integer',
                    },
                },
                records: [{
                    id: 2,
                    message_attachment_count: 3,
                    display_name: "first partner",
                    foo: "HELLO",
                    message_follower_ids: [],
                    message_ids: [],
                    activity_ids: [],
                }]
            },
            'mail.activity': {
                fields: {
                    activity_type_id: { string: "Activity type", type: "many2one", relation: "mail.activity.type" },
                    create_uid: { string: "Created By", type: "many2one", relation: 'partner' },
                    can_write: { string: "Can write", type: "boolean" },
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    activity_category: {
                        string: 'Category',
                        type: 'selection',
                        selection: [['default', 'Other'], ['upload_file', 'Upload File']],
                    },
                    note : { string: "Note", type: "char" },
                },
            },
            'mail.activity.type': {
                fields: {
                    name: { string: "Name", type: "char" },
                    category: {
                        string: 'Category',
                        type: 'selection',
                        selection: [['default', 'Other'], ['upload_file', 'Upload File']],
                    },
                    decoration_type: { string: "Decoration Type", type: "selection", selection: [['warning', 'Alert'], ['danger', 'Error']]},
                    icon: {string: 'icon', type:"char"},
                },
                records: [
                    { id: 1, name: "Type 1" },
                ],
            },
            'mail.message': {
                fields: {
                    attachment_ids: {
                        string: "Attachments",
                        type: 'many2many',
                        relation: 'ir.attachment',
                        default: [],
                    },
                    author_id: {
                        string: "Author",
                        relation: 'res.partner',
                    },
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    date: {
                        string: "Date",
                        type: 'datetime',
                    },
                    is_note: {
                        string: "Note",
                        type: 'boolean',
                    },
                    is_discussion: {
                        string: "Discussion",
                        type: 'boolean',
                    },
                    is_notification: {
                        string: "Notification",
                        type: 'boolean',
                    },
                    is_starred: {
                        string: "Starred",
                        type: 'boolean',
                    },
                    model: {
                        string: "Related Document Model",
                        type: 'char',
                    },
                    res_id: {
                        string: "Related Document ID",
                        type: 'integer',
                    }
                },
                records: [],
            },
            'ir.attachment': {
                fields:{
                    name:{type:'char', string:"attachment name", required:true},
                    res_model:{type:'char', string:"res model"},
                    res_id:{type:'integer', string:"res id"},
                    url:{type:'char', string:'url'},
                    type:{ type:'selection', selection:[['url',"URL"],['binary',"BINARY"]]},
                    mimetype:{type:'char', string:"mimetype"},
                },
                records:[],
            },
        };
    },
});

QUnit.test('form activity widget: open activity creation dialog in fullscreen for mobile', async function (assert) {
    assert.expect(1);

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        intercepts: {
            do_action: function (ev) {
                assert.ok(ev.data.options.fullscreen, "'fullscreen' options should be there with true value set");
                ev.data.options.on_close();
            },
        },
    });
    // schedule an activity (this triggers a do_action)
    await testUtils.dom.click(form.$('.o_chatter_button_schedule_activity'));

    form.destroy();
});

});
});
