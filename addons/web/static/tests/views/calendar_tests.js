odoo.define('web.calendar_tests', function (require) {
"use strict";

const AbstractField = require('web.AbstractField');
const fieldRegistry = require('web.field_registry');
var AbstractStorageService = require('web.AbstractStorageService');
var CalendarView = require('web.CalendarView');
var CalendarRenderer = require('web.CalendarRenderer');
var Dialog = require('web.Dialog');
var ViewDialogs = require('web.view_dialogs');
var fieldUtils = require('web.field_utils');
var mixins = require('web.mixins');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');
var session = require('web.session');

var createActionManager = testUtils.createActionManager;

CalendarRenderer.include({
    getAvatars: function () {
        var res = this._super.apply(this, arguments);
        for (var k in res) {
            res[k] = res[k].replace(/src="([^"]+)"/, 'data-src="\$1"');
        }
        return res;
    }
});


var createCalendarView = testUtils.createCalendarView;

// 2016-12-12 08:00:00
var initialDate = new Date(2016, 11, 12, 8, 0, 0);
initialDate = new Date(initialDate.getTime() - initialDate.getTimezoneOffset()*60*1000);

function _preventScroll(ev) {
    ev.stopImmediatePropagation();
}

QUnit.module('Views', {
    beforeEach: function () {
        window.addEventListener('scroll', _preventScroll, true);
        session.uid = -1; // TO CHECK
        this.data = {
            event: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'user', default: session.uid},
                    partner_id: {string: "user", type: "many2one", relation: 'partner', related: 'user_id.partner_id', default: 1},
                    name: {string: "name", type: "char"},
                    start_date: {string: "start date", type: "date"},
                    stop_date: {string: "stop date", type: "date"},
                    start: {string: "start datetime", type: "datetime"},
                    stop: {string: "stop datetime", type: "datetime"},
                    delay: {string: "delay", type: "float"},
                    allday: {string: "allday", type: "boolean"},
                    partner_ids: {string: "attendees", type: "one2many", relation: 'partner', default: [[6, 0, [1]]]},
                    type: {string: "type", type: "integer"},
                    event_type_id: {string: "Event_Type", type: "many2one", relation: 'event_type'},
                    color:  {string: "Color", type: "integer", related: 'event_type_id.color'},
                },
                records: [
                    {id: 1, user_id: session.uid, partner_id: 1, name: "event 1", start: "2016-12-11 00:00:00", stop: "2016-12-11 00:00:00", allday: false, partner_ids: [1,2,3], type: 1},
                    {id: 2, user_id: session.uid, partner_id: 1, name: "event 2", start: "2016-12-12 10:55:05", stop: "2016-12-12 14:55:05", allday: false, partner_ids: [1,2], type: 3},
                    {id: 3, user_id: 4, partner_id: 4, name: "event 3", start: "2016-12-12 15:55:05", stop: "2016-12-12 16:55:05", allday: false, partner_ids: [1], type: 2},
                    {id: 4, user_id: session.uid, partner_id: 1, name: "event 4", start: "2016-12-14 15:55:05", stop: "2016-12-14 18:55:05", allday: true, partner_ids: [1], type: 2},
                    {id: 5, user_id: 4, partner_id: 4, name: "event 5", start: "2016-12-13 15:55:05", stop: "2016-12-20 18:55:05", allday: false, partner_ids: [2,3], type: 2},
                    {id: 6, user_id: session.uid, partner_id: 1, name: "event 6", start: "2016-12-18 08:00:00", stop: "2016-12-18 09:00:00", allday: false, partner_ids: [3], type: 3},
                    {id: 7, user_id: session.uid, partner_id: 1, name: "event 7", start: "2016-11-14 08:00:00", stop: "2016-11-16 17:00:00", allday: false, partner_ids: [2], type: 1},
                ],
                check_access_rights: function () {
                    return Promise.resolve(true);
                }
            },
            user: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                    image: {string: "image", type: "integer"},
                },
                records: [
                    {id: session.uid, display_name: "user 1", partner_id: 1},
                    {id: 4, display_name: "user 4", partner_id: 4},
                ]
            },
            partner: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    image: {string: "image", type: "integer"},
                },
                records: [
                    {id: 1, display_name: "partner 1", image: 'AAA'},
                    {id: 2, display_name: "partner 2", image: 'BBB'},
                    {id: 3, display_name: "partner 3", image: 'CCC'},
                    {id: 4, display_name: "partner 4", image: 'DDD'}
                ]
            },
            event_type: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    color: {string: "Color", type: "integer"},
                },
                records: [
                    {id: 1, display_name: "Event Type 1", color: 1},
                    {id: 2, display_name: "Event Type 2", color: 2},
                    {id: 3, display_name: "Event Type 3 (color 4)", color: 4},
                ]
            },
            filter_partner: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'user'},
                    partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                },
                records: [
                    {id: 1, user_id: session.uid, partner_id: 1},
                    {id: 2, user_id: session.uid, partner_id: 2},
                    {id: 3, user_id: 4, partner_id: 3}
                ]
            },
        };
    },
    afterEach: function () {
        window.removeEventListener('scroll', _preventScroll, true);
    },
}, function () {

    QUnit.module('CalendarView');

    var archs = {
        "event,false,form":
            '<form>'+
                '<field name="name"/>'+
                '<field name="allday"/>'+
                '<group attrs=\'{"invisible": [["allday","=",True]]}\' >'+
                    '<field name="start"/>'+
                    '<field name="stop"/>'+
                '</group>'+
                '<group attrs=\'{"invisible": [["allday","=",False]]}\' >'+
                    '<field name="start_date"/>'+
                    '<field name="stop_date"/>'+
                '</group>'+
            '</form>',
        "event,1,form":
            '<form>' +
                '<field name="allday" invisible="1"/>' +
                '<field name="start" attrs=\'{"invisible": [["allday","=",false]]}\'/>' +
                '<field name="stop" attrs=\'{"invisible": [["allday","=",true]]}\'/>' +
            '</form>',
    };

    QUnit.test('simple calendar rendering', async function (assert) {
        assert.expect(24);

        this.data.event.records.push({
            id: 8,
            user_id: session.uid,
            partner_id: false,
            name: "event 7",
            start: "2016-12-18 09:00:00",
            stop: "2016-12-18 10:00:00",
            allday: false,
            partner_ids: [2],
            type: 1
        });

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                    '<field name="partner_id" filters="1" invisible="1"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.ok(calendar.$('.o_calendar_view').find('.fc-view-container').length,
            "should instance of fullcalendar");

        var $sidebar = calendar.$('.o_calendar_sidebar');

        // test view scales
        assert.containsN(calendar, '.fc-event', 9,
            "should display 9 events on the week (4 event + 5 days event)");
        assert.containsN($sidebar, 'tr:has(.ui-state-active) td', 7,
            "week scale should highlight 7 days in mini calendar");

        await testUtils.dom.click(calendar.$buttons.find('.o_calendar_button_day')); // display only one day
        assert.containsN(calendar, '.fc-event', 2, "should display 2 events on the day");
        assert.containsOnce($sidebar, '.o_selected_range',
            "should highlight the target day in mini calendar");

        await testUtils.dom.click(calendar.$buttons.find('.o_calendar_button_month')); // display all the month
        assert.containsN(calendar, '.fc-event', 7,
            "should display 7 events on the month (5 events + 2 week event - 1 'event 6' is filtered + 1 'Undefined event')");
        assert.containsN($sidebar, 'td a', 31,
            "month scale should highlight all days in mini calendar");

        // test filters
        assert.containsN($sidebar, '.o_calendar_filter', 2, "should display 2 filters");

        var $typeFilter =  $sidebar.find('.o_calendar_filter:has(h5:contains(user))');
        assert.ok($typeFilter.length, "should display 'user' filter");
        assert.containsN($typeFilter, '.o_calendar_filter_item', 3, "should display 3 filter items for 'user'");

        // filters which has no value should show with string "Undefined", should not have any user image and should show at the last
        assert.strictEqual($typeFilter.find('.o_calendar_filter_item:last').data('value'), false, "filters having false value should be displayed at last in filter items");
        assert.strictEqual($typeFilter.find('.o_calendar_filter_item:last .o_cw_filter_title').text(), "Undefined", "filters having false value should display 'Undefined' string");
        assert.strictEqual($typeFilter.find('.o_calendar_filter_item:last label img').length, 0, "filters having false value should not have any user image");

        var $attendeesFilter =  $sidebar.find('.o_calendar_filter:has(h5:contains(attendees))');
        assert.ok($attendeesFilter.length, "should display 'attendees' filter");
        assert.containsN($attendeesFilter, '.o_calendar_filter_item', 3, "should display 3 filter items for 'attendees' who use write_model (2 saved + Everything)");
        assert.ok($attendeesFilter.find('.o_field_many2one').length, "should display one2many search bar for 'attendees' filter");

        assert.containsN(calendar, '.fc-event', 7,
            "should display 7 events ('event 5' counts for 2 because it spans two weeks and thus generate two fc-event elements)");
        await testUtils.dom.click(calendar.$('.o_calendar_filter input[type="checkbox"]').first());
        assert.containsN(calendar, '.fc-event', 4, "should now only display 4 event");
        await testUtils.dom.click(calendar.$('.o_calendar_filter input[type="checkbox"]').eq(1));
        assert.containsNone(calendar, '.fc-event', "should not display any event anymore");

        // test search bar in filter
        await testUtils.dom.click($sidebar.find('input[type="text"]'));
        assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').length, 2,"should display 2 choices in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
        await testUtils.dom.click($('ul.ui-autocomplete li:first'));
        assert.containsN($sidebar, '.o_calendar_filter:has(h5:contains(attendees)) .o_calendar_filter_item', 4, "should display 4 filter items for 'attendees'");
        await testUtils.dom.click($sidebar.find('input[type="text"]'));
        assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').text(), "partner 4", "should display the last choice in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
        await testUtils.dom.click($sidebar.find('.o_calendar_filter_item .o_remove').first(), {allowInvisible: true});
        assert.ok($('.modal-footer button.btn:contains(Ok)').length, "should display the confirm message");
        await testUtils.dom.click($('.modal-footer button.btn:contains(Ok)'));
        assert.containsN($sidebar, '.o_calendar_filter:has(h5:contains(attendees)) .o_calendar_filter_item', 3, "click on remove then should display 3 filter items for 'attendees'");
        calendar.destroy();
    });

    QUnit.test('delete attribute on calendar doesn\'t show delete button in popover', async function (assert) {
        assert.expect(2);

        const calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
                '<calendar class="o_calendar_test" ' +
                'string="Events" ' +
                'event_open_popup="true" ' +
                'date_start="start" ' +
                'date_stop="stop" ' +
                'all_day="allday" ' +
                'delete="0" ' +
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click(calendar.$('.fc-event:contains(event 4) .fc-content'));

        assert.containsOnce(calendar, '.o_cw_popover',
            "should open a popover clicking on event");
        assert.containsNone(calendar, '.o_cw_popover .o_cw_popover_delete',
            "should not have the 'Delete' Button");

        calendar.destroy();
    });

    QUnit.test('breadcrumbs are updated with the displayed period', async function (assert) {
        assert.expect(4);

        var archs = {
            'event,1,calendar': '<calendar date_start="start" date_stop="stop" all_day="allday"/>',
            'event,false,search': '<search></search>',
        };

        var actions = [{
            id: 1,
            flags: {
                initialDate: initialDate,
            },
            name: 'Meetings Test',
            res_model: 'event',
            type: 'ir.actions.act_window',
            views: [[1, 'calendar']],
        }];

        var actionManager = await createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        await testUtils.nextTick();

        // displays month mode by default
        assert.strictEqual($('.o_control_panel .breadcrumb-item').text(),
            'Meetings Test (Dec 11 – 17, 2016)', "should display the current week");

        // switch to day mode
        await testUtils.dom.click($('.o_control_panel .o_calendar_button_day'));
        assert.strictEqual($('.o_control_panel .breadcrumb-item').text(),
            'Meetings Test (December 12, 2016)', "should display the current day");

        // switch to month mode
        await testUtils.dom.click($('.o_control_panel .o_calendar_button_month'));
        assert.strictEqual($('.o_control_panel .breadcrumb-item').text(),
            'Meetings Test (December 2016)', "should display the current month");

        // switch to year mode
        await testUtils.dom.click($('.o_control_panel .o_calendar_button_year'));
        assert.strictEqual($('.o_control_panel .breadcrumb-item').text(),
            'Meetings Test (2016)', "should display the current year");

        actionManager.destroy();
    });

    QUnit.test('create and change events', async function (assert) {
        assert.expect(28);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month"/>',
            archs: archs,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {name: 'event 4 modified'}, "should update the record");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.ok(calendar.$('.fc-dayGridMonth-view').length, "should display in month mode");

        // click on an existing event to open the formViewDialog

        await testUtils.dom.click(calendar.$('.fc-event:contains(event 4) .fc-content'));

        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.ok(calendar.$('.o_cw_popover .o_cw_popover_edit').length, "popover should have an edit button");
        assert.ok(calendar.$('.o_cw_popover .o_cw_popover_delete').length, "popover should have a delete button");
        assert.ok(calendar.$('.o_cw_popover .o_cw_popover_close').length, "popover should have a close button");

        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_edit'));

        assert.ok($('.modal-body').length, "should open the form view in dialog when click on event");

        await testUtils.fields.editInput($('.modal-body input:first'), 'event 4 modified');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Save)'));

        assert.notOk($('.modal-body').length, "save button should close the modal");

        // create a new event, quick create only

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');

        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.ok($('.modal-sm').length, "should open the quick create dialog");

        await testUtils.fields.editInput($('.modal-body input:first'), 'new event in quick create');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Create)'));

        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create)').length, 1, "should display the new record after quick create");
        assert.containsN(calendar, 'td.fc-event-container[colspan]', 2, "should the new record have only one day");

        // create a new event, quick create only (validated by pressing enter key)

        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.ok($('.modal-sm').length, "should open the quick create dialog");

        await testUtils.fields.editInput($('.modal-body input:first'),
            'new event in quick create validated by pressing enter key.');
        $('.modal-body input:first')
            .val('new event in quick create validated by pressing enter key.')
            .trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}))
            .trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}));
        await testUtils.nextTick();
        assert.containsOnce(calendar, '.fc-event:contains(new event in quick create validated by pressing enter key.)',
            "should display the new record by pressing enter key");


        // create a new event and edit it

        $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');

        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.strictEqual($('.modal-sm').length, 1, "should open the quick create dialog");

        testUtils.fields.editInput($('.modal-body input:first'), 'coucou');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Edit)'));

        assert.strictEqual($('.modal-lg .o_form_view').length, 1, "should open the slow create dialog");
        assert.strictEqual($('.modal-lg .modal-title').text(), "Create: Events",
            "should use the string attribute as modal title");
        assert.strictEqual($('.modal-lg .o_form_view input[name="name"]').val(), "coucou",
            "should have set the name from the quick create dialog");

        await testUtils.dom.click($('.modal-lg button.btn:contains(Save)'));

        assert.strictEqual(calendar.$('.fc-event:contains(coucou)').length, 1,
            "should display the new record with string attribute");

        // create a new event with 2 days

        $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');

        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell.next(), "mousemove");
        testUtils.dom.triggerMouseEvent($cell.next(), "mouseup");
        await testUtils.nextTick();

        testUtils.fields.editInput($('.modal-dialog input:first'), 'new event in quick create 2');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Edit)'));

        assert.strictEqual($('.modal-lg input:first').val(),'new event in quick create 2',
            "should open the formViewDialog with default values");

        await testUtils.dom.click($('.modal-lg button.btn:contains(Save)'));

        assert.notOk($('.modal').length, "should close dialogs");
        var $newevent2 = calendar.$('.fc-event:contains(new event in quick create 2)');
        assert.ok($newevent2.length, "should display the 2 days new record");
        assert.hasAttrValue($newevent2.closest('.fc-event-container'),
            'colspan', "2","the new record should have 2 days");

        await testUtils.dom.click(calendar.$('.fc-event:contains(new event in quick create 2) .fc-content'));
        var $popover_description = calendar.$('.o_cw_popover .o_cw_body .list-group-item');
        assert.strictEqual($popover_description.children()[1].textContent,'December 20-21, 2016',
            "The popover description should indicate the correct range");
        assert.strictEqual($popover_description.children()[2].textContent,'(2 days)',
            "The popover description should indicate 2 days");
        await testUtils.dom.click(calendar.$('.o_cw_popover .fa-close'));

        // delete the a record

        await testUtils.dom.click(calendar.$('.fc-event:contains(event 4) .fc-content'));
        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_delete'));
        assert.ok($('.modal-footer button.btn:contains(Ok)').length, "should display the confirm message");
        await testUtils.dom.click($('.modal-footer button.btn:contains(Ok)'));
        assert.notOk(calendar.$('.fc-event:contains(event 4) .fc-content').length, "the record should be deleted");

        assert.containsN(calendar, '.fc-event-container .fc-event', 10, "should display 10 events");
        // move to next month
        await testUtils.dom.click(calendar.$buttons.find('.o_calendar_button_next'));

        assert.containsNone(calendar, '.fc-event-container .fc-event', "should display 0 events");

        calendar.destroy();
    });

    QUnit.test('quickcreate switching to actual create for required fields', async function (assert) {
        assert.expect(4);

        var event = $.Event();
        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: event
                    });
                }
                return this._super(route, args);
            },
        });

        // create a new event
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.strictEqual($('.modal-sm .modal-title').text(), 'Create: Events',
            "should open the quick create dialog");

        await testUtils.fields.editInput($('.modal-body input:first'), 'new event in quick create');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Create)'));
        await testUtils.nextTick();

        // If the event is not default-prevented, a traceback will be raised, which we do not want
        assert.ok(event.isDefaultPrevented(), "fail deferred event should have been default-prevented");

        assert.strictEqual($('.modal-lg .modal-title').text(), 'Create: Events',
            "should have switched to a bigger modal for an actual create rather than quickcreate");
        assert.strictEqual($('.modal-lg main .o_form_view.o_form_editable').length, 1,
            "should open the full event form view in a dialog");

        calendar.destroy();
    });

    QUnit.test('open multiple event form at the same time', async function (assert) {
        assert.expect(2);

        var prom = testUtils.makeTestPromise();
        var counter = 0;
        testUtils.mock.patch(ViewDialogs.FormViewDialog, {
            open: function () {
                counter++;
                this.options = _.omit(this.options, 'fields_view');  // force loadFieldView
                return this._super.apply(this, arguments);
            },
            loadFieldView: function () {
                var self = this;
                var args = arguments;
                var _super = this._super;
                return prom.then(function () {
                    return _super.apply(self, args);
                });
            },
        });

        var event = $.Event();
        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'event_open_popup="true" '+
                'date_start="start" '+
                'quick_add="False" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        for (var i = 0; i < 5; i++) {
            await testUtils.dom.triggerMouseEvent($cell, "mousedown");
            await testUtils.dom.triggerMouseEvent($cell, "mouseup");
        }
        prom.resolve();
        await testUtils.nextTick();
        assert.equal(counter, 5, "there should had been 5 attemps to open a modal");
        assert.containsOnce($('body'), '.modal', "there should be only one open modal");

        calendar.destroy();
        testUtils.mock.unpatch(ViewDialogs.FormViewDialog);
    });

    QUnit.test('create event with timezone in week mode European locale', async function (assert) {
        assert.expect(5);

        this.data.event.records = [];

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                    '<field name="name"/>'+
                    '<field name="start"/>'+
                    '<field name="allday"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
            translateParameters: { // Avoid issues due to localization formats
                time_format: "%H:%M:%S",
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.kwargs.context, {
                        "default_start": "2016-12-13 06:00:00",
                        "default_stop": "2016-12-13 08:00:00",
                        "default_allday": null
                    },
                    "should send the context to create events");
                }
                return this._super(route, args);
            },
        }, {positionalClicks: true});

        var top = calendar.$('.fc-axis:contains(8:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }

        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mousemove");

        assert.strictEqual(calendar.$('.fc-content .fc-time').text(), "8:00 - 10:00",
            "should display the time in the calendar sticker");

        await testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        await testUtils.nextTick();
        await testUtils.fields.editInput($('.modal input:first'), 'new event');
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.find('.o_event_title').text(), "new event",
            "should display the new event with title");

        assert.deepEqual($newevent[0].fcSeg.eventRange.def.extendedProps.record,
            {
                display_name: "new event",
                start: fieldUtils.parse.datetime("2016-12-13 06:00:00", this.data.event.fields.start, {isUTC: true}),
                stop: fieldUtils.parse.datetime("2016-12-13 08:00:00", this.data.event.fields.stop, {isUTC: true}),
                allday: false,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (quickCreate)");

        // delete record

        await testUtils.dom.click($newevent);
        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_delete'));
        await testUtils.dom.click($('.modal button.btn-primary:contains(Ok)'));
        assert.containsNone(calendar, '.fc-content', "should delete the record");

        calendar.destroy();
    });

    QUnit.test('default week start (US)', function (assert) {
        // if not given any option, default week start is on Sunday
        assert.expect(3);
        var done = assert.async();

        createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start","<=","2016-12-17 23:59:59"],
                        ["stop",">=","2016-12-11 00:00:00"]
                    ],
                    'The domain to search events in should be correct');
                }
                return this._super.apply(this, arguments);
            }
        }).then(function (calendar) {
            assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Sun 11",
                "The first day of the week should be Sunday");
            assert.strictEqual(calendar.$('.fc-day-header').last().text(), "Sat 17",
                "The last day of the week should be Saturday");
            calendar.destroy();
            done();
        });
    });

    QUnit.test('European week start', function (assert) {
        // the week start depends on the locale
        assert.expect(3);
        var done = assert.async();

        createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initialDate,
            },
            translateParameters: {
                week_start: 1,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start","<=","2016-12-18 23:59:59"],
                        ["stop",">=","2016-12-12 00:00:00"]
                    ],
                    'The domain to search events in should be correct');
                }
                return this._super.apply(this, arguments);
            }
        }).then(function (calendar) {
            assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Mon 12",
                "The first day of the week should be Monday");
            assert.strictEqual(calendar.$('.fc-day-header').last().text(), "Sun 18",
                "The last day of the week should be Sunday");
            calendar.destroy();
            done();
        });
    });

    QUnit.test('week numbering', function (assert) {
        // week number depends on the week start, which depends on the locale
        // the calendar library uses numbers [0 .. 6], while Odoo uses [1 .. 7]
        // so if the modulo is not done, the week number is incorrect
        assert.expect(1);
        var done = assert.async();

        createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initialDate,
            },
            translateParameters: {
                week_start: 7,
            },
        }).then(function (calendar) {
            assert.strictEqual(calendar.$('.fc-week-number').text(), "Week 51",
                "We should be on the 51st week");
            calendar.destroy();
            done();
        });
    });

    QUnit.test('render popover', async function (assert) {
        assert.expect(14);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                    '<field name="name" string="Custom Name"/>'+
                    '<field name="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click($('.fc-event:contains(event 4)'));

        assert.containsOnce(calendar, '.o_cw_popover', "should open a popover clicking on event");
        assert.strictEqual(calendar.$('.o_cw_popover .popover-header').text(), 'event 4', "popover should have a title 'event 4'");
        assert.containsOnce(calendar, '.o_cw_popover .o_cw_popover_edit', "popover should have an edit button");
        assert.containsOnce(calendar, '.o_cw_popover .o_cw_popover_delete', "popover should have a delete button");
        assert.containsOnce(calendar, '.o_cw_popover .o_cw_popover_close', "popover should have a close button");

        assert.strictEqual(calendar.$('.o_cw_popover .list-group-item:first b.text-capitalize').text(), 'Wednesday, December 14, 2016', "should display date 'Wednesday, December 14, 2016'");
        assert.containsN(calendar, '.o_cw_popover .o_cw_popover_fields_secondary .list-group-item', 2, "popover should have a two fields");

        assert.containsOnce(calendar, '.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:first .o_field_char', "should apply char widget");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:first strong').text(), 'Custom Name : ', "label should be a 'Custom Name'");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:first .o_field_char').text(), 'event 4', "value should be a 'event 4'");

        assert.containsOnce(calendar, '.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:last .o_form_uri', "should apply m20 widget");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:last strong').text(), 'user : ', "label should be a 'user'");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:last .o_form_uri').text(), 'partner 1', "value should be a 'partner 1'");

        await testUtils.dom.click($('.o_cw_popover .o_cw_popover_close'));
        assert.containsNone(calendar, '.o_cw_popover', "should close a popover");

        calendar.destroy();
    });

    QUnit.test('render popover with modifiers', async function (assert) {
        assert.expect(3);

        this.data.event.fields.priority = {string: "Priority", type: "selection", selection: [['0', 'Normal'], ['1', 'Important']],};

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                '<field name="priority" widget="priority" readonly="1"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click($('.fc-event:contains(event 4)'));

        assert.containsOnce(calendar, '.o_cw_popover', "should open a popover clicking on event");
        assert.containsOnce(calendar, '.o_cw_popover .o_priority span.o_priority_star', "priority field should not be editable");

        await testUtils.dom.click($('.o_cw_popover .o_cw_popover_close'));
        assert.containsNone(calendar, '.o_cw_popover', "should close a popover");

        calendar.destroy();
    });

    QUnit.test('attributes hide_date and hide_time', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'hide_date="true" '+
                'hide_time="true" '+
                'mode="month">'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click($('.fc-event:contains(event 4)'));
        assert.containsNone(calendar, '.o_cw_popover .list-group-item', "popover should not contain date/time");

        calendar.destroy();
    });

    QUnit.test('create event with timezone in week mode with formViewDialog European locale', async function (assert) {
        assert.expect(8);

        this.data.event.records = [];
        this.data.event.onchanges = {
            allday: function (obj) {
                if (obj.allday) {
                    obj.start_date = obj.start && obj.start.split(' ')[0] || obj.start_date;
                    obj.stop_date = obj.stop && obj.stop.split(' ')[0] || obj.stop_date || obj.start_date;
                } else {
                    obj.start = obj.start_date && (obj.start_date + ' 00:00:00') || obj.start;
                    obj.stop = obj.stop_date && (obj.stop_date + ' 00:00:00') || obj.stop || obj.start;
                }
            }
        };

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
            translateParameters: { // Avoid issues due to localization formats
                time_format: "%H:%M:%S",
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.kwargs.context, {
                        "default_name": "new event",
                        "default_start": "2016-12-13 06:00:00",
                        "default_stop": "2016-12-13 08:00:00",
                        "default_allday": null
                    },
                    "should send the context to create events");
                }
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], expectedEvent,
                        "should move the event");
                }
                return this._super(route, args);
            },
        }, {positionalClicks: true});

        var top = calendar.$('.fc-axis:contains(8:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        await testUtils.nextTick();
        await testUtils.fields.editInput($('.modal input:first'), 'new event');
        await testUtils.dom.click($('.modal button.btn:contains(Edit)'));

        assert.strictEqual($('.o_field_widget[name="start"] input').val(),
            "12/13/2016 08:00:00", "should display the datetime");

        await testUtils.dom.click($('.modal-lg .o_field_boolean[name="allday"] input'));
        await testUtils.nextTick();
        assert.strictEqual($('input[name="start_date"]').val(),
            "12/13/2016", "should display the date");

        await testUtils.dom.click($('.modal-lg .o_field_boolean[name="allday"] input'));

        assert.strictEqual($('.o_field_widget[name="start"] input').val(),
            "12/13/2016 02:00:00", "should display the datetime from the date with the timezone");

        // use datepicker to enter a date: 12/13/2016 08:00:00
        testUtils.dom.openDatepicker($('.o_field_widget[name="start"].o_datepicker'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(08)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]'));

        // use datepicker to enter a date: 12/13/2016 10:00:00
        testUtils.dom.openDatepicker($('.o_field_widget[name="stop"].o_datepicker'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(10)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]'));

        await testUtils.dom.click($('.modal-lg button.btn:contains(Save)'));
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.find('.o_event_title').text(), "new event",
            "should display the new event with title");

        assert.deepEqual($newevent[0].fcSeg.eventRange.def.extendedProps.record,
            {
                display_name: "new event",
                start: fieldUtils.parse.datetime("2016-12-13 06:00:00", this.data.event.fields.start, {isUTC: true}),
                stop: fieldUtils.parse.datetime("2016-12-13 08:00:00", this.data.event.fields.stop, {isUTC: true}),
                allday: false,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (formViewDialog)");

        var pos = calendar.$('.fc-content').offset();
        left = pos.left + 5;
        top = pos.top + 5;

        // Mode this event to another day
        var expectedEvent = {
          "allday": false,
          "start": "2016-12-12 06:00:00",
          "stop": "2016-12-12 08:00:00"
        };
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        left = calendar.$('.fc-day:eq(1)').offset().left + 15;
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
        await testUtils.nextTick();

        // Move to "All day"
        expectedEvent = {
          "allday": true,
          "start": "2016-12-12 00:00:00",
          "stop": "2016-12-12 00:00:00"
        };
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        top = calendar.$('.fc-day:eq(1)').offset().top + 15;
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
        await testUtils.nextTick();

        calendar.destroy();
    });

    QUnit.test('create event with timezone in week mode American locale', async function (assert) {
        assert.expect(5);

        this.data.event.records = [];

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                    '<field name="name"/>'+
                    '<field name="start"/>'+
                    '<field name="allday"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
            translateParameters: { // Avoid issues due to localization formats
                time_format: "%I:%M:%S",
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.kwargs.context, {
                        "default_start": "2016-12-13 06:00:00",
                        "default_stop": "2016-12-13 08:00:00",
                        "default_allday": null
                    },
                    "should send the context to create events");
                }
                return this._super(route, args);
            },
        }, {positionalClicks: true});

        var top = calendar.$('.fc-axis:contains(8am)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }

        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mousemove");

        assert.strictEqual(calendar.$('.fc-content .fc-time').text(), "8:00 - 10:00",
            "should display the time in the calendar sticker");

        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        await testUtils.nextTick();
        testUtils.fields.editInput($('.modal input:first'), 'new event');
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.find('.o_event_title').text(), "new event",
            "should display the new event with title");

        assert.deepEqual($newevent[0].fcSeg.eventRange.def.extendedProps.record,
            {
                display_name: "new event",
                start: fieldUtils.parse.datetime("2016-12-13 06:00:00", this.data.event.fields.start, {isUTC: true}),
                stop: fieldUtils.parse.datetime("2016-12-13 08:00:00", this.data.event.fields.stop, {isUTC: true}),
                allday: false,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (quickCreate)");

        // delete record

        await testUtils.dom.click($newevent);
        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_delete'));
        await testUtils.dom.click($('.modal button.btn-primary:contains(Ok)'));
        assert.containsNone(calendar, '.fc-content', "should delete the record");

        calendar.destroy();
    });

    QUnit.test('fetch event when being in timezone', async function (assert) {
        assert.expect(3);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week" >'+
                    '<field name="name"/>'+
                    '<field name="start"/>'+
                    '<field name="allday"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 660;
                },
            },

            mockRPC: async function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start", "<=", "2016-12-17 12:59:59"], // in UTC. which is 2016-12-17 23:59:59 in TZ Sydney 11 hours later
                        ["stop", ">=", "2016-12-10 13:00:00"]   // in UTC. which is 2016-12-11 00:00:00 in TZ Sydney 11 hours later
                    ], 'The domain should contain the right range');
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(calendar.$('.fc-day-header:first').text(), 'Sun 11',
            'The calendar start date should be 2016-12-11');
        assert.strictEqual(calendar.$('.fc-day-header:last()').text(), 'Sat 17',
            'The calendar start date should be 2016-12-17');

        calendar.destroy();
    });

    QUnit.test('create event with timezone in week mode with formViewDialog American locale', async function (assert) {
        assert.expect(8);

        this.data.event.records = [];
        this.data.event.onchanges = {
            allday: function (obj) {
                if (obj.allday) {
                    obj.start_date = obj.start && obj.start.split(' ')[0] || obj.start_date;
                    obj.stop_date = obj.stop && obj.stop.split(' ')[0] || obj.stop_date || obj.start_date;
                } else {
                    obj.start = obj.start_date && (obj.start_date + ' 00:00:00') || obj.start;
                    obj.stop = obj.stop_date && (obj.stop_date + ' 00:00:00') || obj.stop || obj.start;
                }
            }
        };

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
            translateParameters: { // Avoid issues due to localization formats
                time_format: "%I:%M:%S",
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.kwargs.context, {
                        "default_name": "new event",
                        "default_start": "2016-12-13 06:00:00",
                        "default_stop": "2016-12-13 08:00:00",
                        "default_allday": null
                    },
                    "should send the context to create events");
                }
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], expectedEvent,
                        "should move the event");
                }
                return this._super(route, args);
            },
        }, {positionalClicks: true});

        var top = calendar.$('.fc-axis:contains(8am)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        await testUtils.nextTick();
        testUtils.fields.editInput($('.modal input:first'), 'new event');
        await testUtils.dom.click($('.modal button.btn:contains(Edit)'));

        assert.strictEqual($('.o_field_widget[name="start"] input').val(), "12/13/2016 08:00:00",
            "should display the datetime");

        await testUtils.dom.click($('.modal-lg .o_field_boolean[name="allday"] input'));

        assert.strictEqual($('.o_field_widget[name="start_date"] input').val(), "12/13/2016",
            "should display the date");

        await testUtils.dom.click($('.modal-lg .o_field_boolean[name="allday"] input'));

        assert.strictEqual($('.o_field_widget[name="start"] input').val(), "12/13/2016 02:00:00",
            "should display the datetime from the date with the timezone");

        // use datepicker to enter a date: 12/13/2016 08:00:00
        testUtils.dom.openDatepicker($('.o_field_widget[name="start"].o_datepicker'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(08)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]'));

        // use datepicker to enter a date: 12/13/2016 10:00:00
        testUtils.dom.openDatepicker($('.o_field_widget[name="stop"].o_datepicker'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(10)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]'));

        await testUtils.dom.click($('.modal-lg button.btn:contains(Save)'));
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.find('.o_event_title').text(), "new event",
            "should display the new event with title");

        assert.deepEqual($newevent[0].fcSeg.eventRange.def.extendedProps.record,
            {
                display_name: "new event",
                start: fieldUtils.parse.datetime("2016-12-13 06:00:00", this.data.event.fields.start, {isUTC: true}),
                stop: fieldUtils.parse.datetime("2016-12-13 08:00:00", this.data.event.fields.stop, {isUTC: true}),
                allday: false,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (formViewDialog)");

        var pos = calendar.$('.fc-content').offset();
        left = pos.left + 5;
        top = pos.top + 5;

        // Mode this event to another day
        var expectedEvent = {
          "allday": false,
          "start": "2016-12-12 06:00:00",
          "stop": "2016-12-12 08:00:00"
        };
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        left = calendar.$('.fc-day:eq(1)').offset().left + 15;
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
        await testUtils.nextTick();

        // Move to "All day"
        expectedEvent = {
          "allday": true,
          "start": "2016-12-12 00:00:00",
          "stop": "2016-12-12 00:00:00"
        };
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        top = calendar.$('.fc-day:eq(1)').offset().top + 15;
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
        await testUtils.nextTick();

        calendar.destroy();
    });

    QUnit.test('check calendar week column timeformat', async function (assert) {
        assert.expect(2);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            translateParameters: {
                time_format: "%I:%M:%S",
            },
        });

        assert.strictEqual(calendar.$('.fc-axis:contains(8am)').length, 1, "calendar should show according to timeformat");
        assert.strictEqual(calendar.$('.fc-axis:contains(11pm)').length, 1,
            "event time format should 12 hour");

        calendar.destroy();
    });

    QUnit.test('create all day event in week mode', async function (assert) {
        assert.expect(3);

        this.data.event.records = [];

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        }, {positionalClicks: true});

        var pos = calendar.$('.fc-bg td:eq(4)').offset();
        try {
            testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(5)').offset();
        testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");
        await testUtils.nextTick();

        testUtils.fields.editInput($('.modal input:first'), 'new event');
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "newevent",
            "should display the new event with time and title");
        assert.hasAttrValue($newevent.parent(), 'colspan', "2",
            "should appear over two days.");

        assert.deepEqual($newevent[0].fcSeg.eventRange.def.extendedProps.record,
            {
                display_name: "new event",
                start: fieldUtils.parse.datetime("2016-12-14 00:00:00", this.data.event.fields.start, {isUTC: true}),
                stop: fieldUtils.parse.datetime("2016-12-15 00:00:00", this.data.event.fields.stop, {isUTC: true}),
                allday: true,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (quickCreate)");

        calendar.destroy();
    });

    QUnit.test('create event with default context (no quickCreate)', async function (assert) {
        assert.expect(3);

        this.data.event.records = [];

        const calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            `<calendar
                class="o_calendar_test"
                date_start="start"
                date_stop="stop"
                mode="week"
                all_day="allday"
                quick_add="False"/>`,
            archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset() {
                    return 120;
                },
            },
            context: {
                default_name: 'New',
            },
            intercepts: {
                do_action(ev) {
                    assert.step('do_action');
                    assert.deepEqual(ev.data.action.context, {
                        default_name: "New",
                        default_start: "2016-12-14 00:00:00",
                        default_stop: "2016-12-15 00:00:00",
                        default_allday: true,
                    },
                    "should send the correct data to create events");
                },
            },
        }, { positionalClicks: true });

        var pos = calendar.$('.fc-bg td:eq(4)').offset();
        try {
            testUtils.dom.triggerPositionalMouseEvent(pos.left + 15, pos.top + 15, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(5)').offset();
        testUtils.dom.triggerPositionalMouseEvent(pos.left + 15, pos.top + 15, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(pos.left + 15, pos.top + 15, "mouseup");
        assert.verifySteps(['do_action']);

        calendar.destroy();
    });

    QUnit.test('create all day event in week mode (no quickCreate)', async function (assert) {
        assert.expect(1);

        this.data.event.records = [];

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week" '+
                'all_day="allday" '+
                'quick_add="False"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action.context, {
                            default_start: "2016-12-14 00:00:00",
                            default_stop: "2016-12-15 00:00:00",
                            default_allday: true,
                    },
                    "should send the correct data to create events");
                },
            },
        }, {positionalClicks: true});

        var pos = calendar.$('.fc-bg td:eq(4)').offset();
        try {
            testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(5)').offset();
        testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");

        calendar.destroy();
    });

    QUnit.test('create event in month mode', async function (assert) {
        assert.expect(4);

        this.data.event.records = [];

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], {
                        "name": "new event",
                        "start": "2016-12-14 05:00:00",
                        "stop": "2016-12-15 17:00:00",
                    },
                    "should send the correct data to create events");
                }
                return this._super(route, args);
            },
        }, {positionalClicks: true});

        var pos = calendar.$('.fc-bg td:eq(17)').offset();
        try {
            testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(18)').offset();
        testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");
        await testUtils.nextTick();

        testUtils.fields.editInput($('.modal input:first'), 'new event');
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "newevent",
            "should display the new event with time and title");
        assert.hasAttrValue($newevent.parent(), 'colspan', "2",
            "should appear over two days.");

        assert.deepEqual($newevent[0].fcSeg.eventRange.def.extendedProps.record, {
            display_name: "new event",
            start: fieldUtils.parse.datetime("2016-12-14 05:00:00", this.data.event.fields.start, {isUTC: true}),
            stop: fieldUtils.parse.datetime("2016-12-15 17:00:00", this.data.event.fields.stop, {isUTC: true}),
            name: "new event",
            id: 1
        }, "the new record should have the utc datetime (quickCreate)");

        calendar.destroy();
    });

    QUnit.test('use mini calendar', async function (assert) {
        assert.expect(12);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        assert.containsOnce(calendar, '.fc-timeGridWeek-view', "should be in week mode");
        assert.containsN(calendar, '.fc-event', 9, "should display 9 events on the week (4 event + 5 days event)");
        await testUtils.dom.click(calendar.$('.o_calendar_mini a:contains(19)'));
        // Clicking on a day in another week should switch to the other week view
        assert.containsOnce(calendar, '.fc-timeGridWeek-view', "should be in week mode");
        assert.containsN(calendar, '.fc-event', 4, "should display 4 events on the week (1 event + 3 days event)");
        // Clicking on a day in the same week should switch to that particular day view
        await testUtils.dom.click(calendar.$('.o_calendar_mini a:contains(18)'));
        assert.containsOnce(calendar, '.fc-timeGridDay-view', "should be in day mode");
        assert.containsN(calendar, '.fc-event', 2, "should display 2 events on the day");
        // Clicking on the same day should toggle between day, month and week views
        await testUtils.dom.click(calendar.$('.o_calendar_mini a:contains(18)'));
        assert.containsOnce(calendar, '.fc-dayGridMonth-view', "should be in month mode");
        assert.containsN(calendar, '.fc-event', 7, "should display 7 events on the month (event 5 is on multiple weeks and generates to .fc-event)");
        await testUtils.dom.click(calendar.$('.o_calendar_mini a:contains(18)'));
        assert.containsOnce(calendar, '.fc-timeGridWeek-view', "should be in week mode");
        assert.containsN(calendar, '.fc-event', 4, "should display 4 events on the week (1 event + 3 days event)");
        await testUtils.dom.click(calendar.$('.o_calendar_mini a:contains(18)'));
        assert.containsOnce(calendar, '.fc-timeGridDay-view', "should be in day mode");
        assert.containsN(calendar, '.fc-event', 2, "should display 2 events on the day");

        calendar.destroy();
    });

    QUnit.test('rendering, with many2many', async function (assert) {
        assert.expect(5);

        this.data.event.fields.partner_ids.type = 'many2many';
        this.data.event.records[0].partner_ids = [1,2,3,4,5];
        this.data.partner.records.push({id: 5, display_name: "partner 5", image: 'EEE'});

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday"> '+
                    '<field name="partner_ids" widget="many2many_tags_avatar" avatar_field="image" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.containsN(calendar, '.o_calendar_filter_items .o_cw_filter_avatar', 3,
            "should have 3 avatars in the side bar");

        // Event 1
        await testUtils.dom.click(calendar.$('.fc-event:first'));
        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.strictEqual(calendar.$('.o_cw_popover').find('img').length, 1, "should have 1 avatar");

        // Event 2
        await testUtils.dom.click(calendar.$('.fc-event:eq(1)'));
        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.strictEqual(calendar.$('.o_cw_popover').find('img').length, 5, "should have 5 avatar");

        calendar.destroy();
    });

    QUnit.test('open form view', async function (assert) {
        assert.expect(3);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve('A view');
                }
                return this._super(route, args);
            },
        });

        // click on an existing event to open the form view

        testUtils.mock.intercept(calendar, 'do_action', function (event) {
            assert.deepEqual(event.data.action,
                {
                    type: "ir.actions.act_window",
                    res_id: 4,
                    res_model: "event",
                    views: [['A view', "form"]],
                    target: "current",
                    context: {}
                },
                "should open the form view");
        });
        await testUtils.dom.click(calendar.$('.fc-event:contains(event 4) .fc-content'));
        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_edit'));

        // create a new event and edit it

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        testUtils.fields.editInput($('.modal-body input:first'), 'coucou');

        testUtils.mock.intercept(calendar, 'do_action', function (event) {
            assert.deepEqual(event.data.action,
                {
                    type: "ir.actions.act_window",
                    res_model: "event",
                    views: [[false, "form"]],
                    target: "current",
                    context: {
                        "default_name": "coucou",
                        "default_start": "2016-12-27 00:00:00",
                        "default_stop": "2016-12-27 00:00:00",
                        "default_allday": true
                    }
                },
                "should open the form view with the context default values");
        });

        testUtils.dom.click($('.modal button.btn:contains(Edit)'));

        calendar.destroy();

        assert.strictEqual($('#ui-datepicker-div:empty').length, 0, "should have a clean body");
    });

    QUnit.test('create and edit event in month mode (all_day: false)', async function (assert) {
        assert.expect(2);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
        });

        // create a new event and edit it
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        await testUtils.fields.editInput($('.modal-body input:first'), 'coucou');

        testUtils.mock.intercept(calendar, 'do_action', function (event) {
            assert.deepEqual(event.data.action,
                {
                    type: "ir.actions.act_window",
                    res_model: "event",
                    views: [[false, "form"]],
                    target: "current",
                    context: {
                        "default_name": "coucou",
                        "default_start": "2016-12-27 11:00:00", // 7:00 + 4h
                        "default_stop": "2016-12-27 23:00:00", // 19:00 + 4h
                    }
                },
                "should open the form view with the context default values");
        });

        await testUtils.dom.click($('.modal button.btn:contains(Edit)'));

        calendar.destroy();
        assert.strictEqual($('#ui-datepicker-div:empty').length, 0, "should have a clean body");
    });

    QUnit.test('show start time of single day event for month mode', async function (assert) {
        assert.expect(4);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" ' +
                'string="Events" ' +
                'date_start="start" ' +
                'date_stop="stop" ' +
                'all_day="allday" ' +
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
        });

        assert.strictEqual(calendar.$('.fc-event:contains(event 2) .fc-content .fc-time').text(), "06:55",
            "should have a correct time 06:55 AM in month mode");
        assert.strictEqual(calendar.$('.fc-event:contains(event 4) .fc-content .fc-time').text(), "",
            "should not display a time for all day event");
        assert.strictEqual(calendar.$('.fc-event:contains(event 5) .fc-content .fc-time').text(), "",
            "should not display a time for multiple days event");
        // switch to week mode
        await testUtils.dom.click(calendar.$('.o_calendar_button_week'));
        assert.strictEqual(calendar.$('.fc-event:contains(event 2) .fc-content .fc-time').text(), "",
            "should not show time in week mode as week mode already have time on y-axis");

        calendar.destroy();
    });

    QUnit.test('start time should not shown for date type field', async function (assert) {
        assert.expect(1);

        this.data.event.fields.start.type = "date";

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" ' +
                'string="Events" ' +
                'date_start="start" ' +
                'date_stop="stop" ' +
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
        });

        assert.strictEqual(calendar.$('.fc-event:contains(event 2) .fc-content .fc-time').text(), "",
            "should not show time for date type field");

        calendar.destroy();
    });

    QUnit.test('start time should not shown in month mode if hide_time is true', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" ' +
                'string="Events" ' +
                'date_start="start" ' +
                'date_stop="stop" ' +
                'hide_time="True" ' +
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
        });

        assert.strictEqual(calendar.$('.fc-event:contains(event 2) .fc-content .fc-time').text(), "",
            "should not show time for hide_time attribute");

        calendar.destroy();
    });

    QUnit.test('readonly date_start field', async function (assert) {
        assert.expect(4);

        this.data.event.fields.start.readonly = true;

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
        });

        assert.containsNone(calendar, '.fc-resizer', "should not have resize button");

        // click on an existing event to open the form view

        testUtils.mock.intercept(calendar, 'do_action', function (event) {
            assert.deepEqual(event.data.action,
                {
                    type: "ir.actions.act_window",
                    res_id: 4,
                    res_model: "event",
                    views: [[false, "form"]],
                    target: "current",
                    context: {}
                },
                "should open the form view");
        });
        await testUtils.dom.click(calendar.$('.fc-event:contains(event 4) .fc-content'));
        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_edit'));

        // create a new event and edit it

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        await testUtils.fields.editInput($('.modal-body input:first'), 'coucou');

        testUtils.mock.intercept(calendar, 'do_action', function (event) {
            assert.deepEqual(event.data.action,
                {
                    type: "ir.actions.act_window",
                    res_model: "event",
                    views: [[false, "form"]],
                    target: "current",
                    context: {
                        "default_name": "coucou",
                        "default_start": "2016-12-27 00:00:00",
                        "default_stop": "2016-12-27 00:00:00",
                        "default_allday": true
                    }
                },
                "should open the form view with the context default values");
        });

        await testUtils.dom.click($('.modal button.btn:contains(Edit)'));

        calendar.destroy();

        assert.strictEqual($('#ui-datepicker-div:empty').length, 0, "should have a clean body");
    });

    QUnit.test('"all" filter', async function (assert) {
        assert.expect(6);

        var interval = [
            ["start", "<=", "2016-12-17 23:59:59"],
            ["stop", ">=", "2016-12-11 00:00:00"],
        ];

        var domains = [
            interval.concat([["partner_ids", "in", [2,1]]]),
            interval.concat([["partner_ids", "in", [1]]]),
            interval,
        ];

        var i = 0;

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, domains[i]);
                    i++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(calendar, '.fc-event', 9,
            "should display 9 events on the week");

        // Select the events only associated with partner 2
        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-id=2] input'));
        assert.containsN(calendar, '.fc-event', 4,
            "should display 4 events on the week");

        // Click on the 'all' filter to reload all events
        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input'));
        assert.containsN(calendar, '.fc-event', 9,
            "should display 9 events on the week");

        calendar.destroy();
    });

    QUnit.test('Add filters and specific color', async function (assert) {
        assert.expect(5);

        this.data.event.records.push(
            {id: 8, user_id: 4, partner_id: 1, name: "event 8", start: "2016-12-11 09:00:00", stop: "2016-12-11 10:00:00", allday: false, partner_ids: [1,2,3], event_type_id: 3, color: 4},
            {id: 9, user_id: 4, partner_id: 1, name: "event 9", start: "2016-12-11 19:00:00", stop: "2016-12-11 20:00:00", allday: false, partner_ids: [1,2,3], event_type_id: 1, color: 1},
        );

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'color="color">'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                    '<field name="event_type_id" filters="1" color="color"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.containsN(calendar, '.o_calendar_filter', 2, "should display 2 filters");

        var $typeFilter =  calendar.$('.o_calendar_filter:has(h5:contains(Event_Type))');
        assert.ok($typeFilter.length, "should display 'Event Type' filter");
        assert.containsN($typeFilter, '.o_calendar_filter_item', 3, "should display 3 filter items for 'Event Type'");

        assert.containsOnce($typeFilter, '.o_calendar_filter_item[data-value=3].o_cw_filter_color_4', "Filter for event type 3 must have the color 4");

        assert.containsOnce(calendar, '.fc-event[data-event-id=8].o_calendar_color_4', "Event of event type 3 must have the color 4");

        calendar.destroy();
    });

    QUnit.test('create event with filters', async function (assert) {
        assert.expect(7);

        this.data.event.fields.user_id.default = 5;
        this.data.event.fields.partner_id.default = 3;
        this.data.user.records.push({id: 5, display_name: "user 5", partner_id: 3});

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                    '<field name="partner_id" filters="1" invisible="1"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
        }, {positionalClicks: true});

        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=4] input'));

        assert.containsN(calendar, '.o_calendar_filter_item', 5, "should display 5 filter items");
        assert.containsN(calendar, '.fc-event', 3, "should display 3 events");

        // quick create a record
        var left = calendar.$('.fc-bg td:eq(4)').offset().left+15;
        var top = calendar.$('.fc-slats tr:eq(12) td:first').offset().top+15;
        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        testUtils.dom.triggerPositionalMouseEvent(left, top + 200, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top + 200, "mouseup");
        await testUtils.nextTick();

        await testUtils.fields.editInput($('.modal-body input:first'), 'coucou');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Create)'));

        assert.containsN(calendar, '.o_calendar_filter_item', 6, "should add the missing filter (active)");
        assert.containsN(calendar, '.fc-event', 4, "should display the created item");
        await testUtils.nextTick();

        // change default value for quick create an hide record
        this.data.event.fields.user_id.default = 4;
        this.data.event.fields.partner_id.default = 4;

        // quick create and other record
        left = calendar.$('.fc-bg td:eq(3)').offset().left+15;
        top = calendar.$('.fc-slats tr:eq(12) td:first').offset().top+15;
        testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        testUtils.dom.triggerPositionalMouseEvent(left, top + 200, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top + 200, "mouseup");
        await testUtils.nextTick();

        testUtils.fields.editInput($('.modal-body input:first'), 'coucou 2');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Create)'));

        assert.containsN(calendar, '.o_calendar_filter_item', 6, "should have the same filters");
        assert.containsN(calendar, '.fc-event', 4, "should not display the created item");

        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=4] input'));

        assert.containsN(calendar, '.fc-event', 11, "should display all records");

        calendar.destroy();
    });

    QUnit.test('create event with filters (no quickCreate)', async function (assert) {
        assert.expect(4);

        this.data.event.fields.user_id.default = 5;
        this.data.event.fields.partner_id.default = 3;
        this.data.user.records.push({
            id: 5,
            display_name: "user 5",
            partner_id: 3
        });

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                    '<field name="partner_id" filters="1" invisible="1"/>'+
            '</calendar>',
            archs: {
                "event,false,form":
                    '<form>'+
                        '<group>'+
                            '<field name="name"/>'+
                            '<field name="start"/>'+
                            '<field name="stop"/>'+
                            '<field name="user_id"/>'+
                            '<field name="partner_id" invisible="1"/>'+
                        '</group>'+
                    '</form>',
            },
            viewOptions: {
                initialDate: initialDate,
            },
        }, {positionalClicks: true});

        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=4] input'));

        assert.containsN(calendar, '.o_calendar_filter_item', 5, "should display 5 filter items");
        assert.containsN(calendar, '.fc-event', 3, "should display 3 events");
        await testUtils.nextTick();

        // quick create a record
        var left = calendar.$('.fc-bg td:eq(4)').offset().left+15;
        var top = calendar.$('.fc-slats tr:eq(12) td:first').offset().top+15;
        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        testUtils.dom.triggerPositionalMouseEvent(left, top + 200, "mousemove");
        testUtils.dom.triggerPositionalMouseEvent(left, top + 200, "mouseup");
        await testUtils.nextTick();

        await testUtils.fields.editInput($('.modal-body input:first'), 'coucou');

        await testUtils.dom.click($('.modal-footer button.btn:contains(Edit)'));
        await testUtils.dom.click($('.modal-footer button.btn:contains(Save)'));

        assert.containsN(calendar, '.o_calendar_filter_item', 6, "should add the missing filter (active)");
        assert.containsN(calendar, '.fc-event', 4, "should display the created item");

        calendar.destroy();
    });

    QUnit.test('Update event with filters', async function (assert) {
        assert.expect(6);

        var records = this.data.user.records;
        records.push({
            id: 5,
            display_name: "user 5",
            partner_id: 3
        });

        this.data.event.onchanges = {
            user_id: function (obj) {
                obj.partner_id = _.findWhere(records, {id:obj.user_id}).partner_id;
            }
        };

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                    '<field name="partner_id" filters="1" invisible="1"/>'+
            '</calendar>',
            archs: {
                "event,false,form":
                    '<form>'+
                        '<group>'+
                            '<field name="name"/>'+
                            '<field name="start"/>'+
                            '<field name="stop"/>'+
                            '<field name="user_id"/>'+
                            '<field name="partner_ids" widget="many2many_tags"/>'+
                        '</group>'+
                    '</form>',
            },
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=4] input'));

        assert.containsN(calendar, '.o_calendar_filter_item', 5, "should display 5 filter items");
        assert.containsN(calendar, '.fc-event', 3, "should display 3 events");

        await testUtils.dom.click(calendar.$('.fc-event:contains(event 2) .fc-content'));
        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_edit'));
        assert.strictEqual($('.modal .modal-title').text(), 'Open: event 2', "dialog should have a valid title");
        await testUtils.dom.click($('.modal .o_field_widget[name="user_id"] input'));
        await testUtils.dom.click($('.ui-menu-item a:contains(user 5)').trigger('mouseenter'));
        await testUtils.dom.click($('.modal button.btn:contains(Save)'));

        assert.containsN(calendar, '.o_calendar_filter_item', 6, "should add the missing filter (active)");
        assert.containsN(calendar, '.fc-event', 3, "should display the updated item");

        calendar.destroy();
    });

    QUnit.test('change pager with filters', async function (assert) {
        assert.expect(3);

        this.data.user.records.push({
            id: 5,
            display_name: "user 5",
            partner_id: 3
        });
        this.data.event.records.push({
            id: 8,
            user_id: 5,
            partner_id: 3,
            name: "event 8",
            start: "2016-12-06 04:00:00",
            stop: "2016-12-06 08:00:00",
            allday: false,
            partner_ids: [1,2,3],
            type: 1
        }, {
            id: 9,
            user_id: session.uid,
            partner_id: 1,
            name: "event 9",
            start: "2016-12-07 04:00:00",
            stop: "2016-12-07 08:00:00",
            allday: false,
            partner_ids: [1,2,3],
            type: 1
        },{
            id: 10,
            user_id: 4,
            partner_id: 4,
            name: "event 10",
            start: "2016-12-08 04:00:00",
            stop: "2016-12-08 08:00:00",
            allday: false,
            partner_ids: [1,2,3],
            type: 1
        });

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                    '<field name="partner_id" filters="1" invisible="1"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=4] input'));
        await testUtils.dom.click($('.o_calendar_button_prev'));

        assert.containsN(calendar, '.o_calendar_filter_item', 6, "should display 6 filter items");
        assert.containsN(calendar, '.fc-event', 2, "should display 2 events");
        assert.strictEqual(calendar.$('.fc-event .o_event_title').text().replace(/\s/g, ''), "event8event9",
            "should display 2 events");

        calendar.destroy();
    });

    QUnit.test('ensure events are still shown if filters give an empty domain', async function (assert) {
        assert.expect(2);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar mode="week" date_start="start">' +
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>' +
                '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.containsN(calendar, '.fc-event', 5,
            "should display 5 events");
        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input[type=checkbox]'));
        assert.containsN(calendar, '.fc-event', 5,
            "should display 5 events");
        calendar.destroy();
    });

    QUnit.test('events starting at midnight', async function (assert) {
        assert.expect(3);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar mode="week" date_start="start"/>',
            viewOptions: {
                initialDate: initialDate,
            },
            translateParameters: { // Avoid issues due to localization formats
                time_format: "%H:%M:%S",
            },
        }, {positionalClicks: true});

        // Reset the scroll to 0 as we want to create an event from midnight
        assert.ok(calendar.$('.fc-scroller')[0].scrollTop > 0,
            "should scroll to 6:00 by default (this is true at least for resolutions up to 1900x1600)");
        calendar.$('.fc-scroller')[0].scrollTop = 0;

        // Click on Tuesday 12am
        var top = calendar.$('.fc-axis:contains(0:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;
        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mouseup");
            await testUtils.nextTick();
        } catch (e) {
            calendar.destroy();
            throw new Error('The test failed to simulate a click on the screen.' +
                'Your screen is probably too small or your dev tools are open.');
        }
        assert.ok($('.modal-dialog.modal-sm').length,
            "should open the quick create dialog");

        // Creating the event
        testUtils.fields.editInput($('.modal-body input:first'), 'new event in quick create');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Create)'));
        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create)').length, 1,
            "should display the new record after quick create dialog");

        calendar.destroy();
    });

    QUnit.test('set event as all day when field is date', async function (assert) {
        assert.expect(2);

        this.data.event.records[0].start_date = "2016-12-14";

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start_date" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return -480;
                }
            },
        });
        assert.containsOnce(calendar, '.fc-day-grid .fc-event-container',
            "should be one event in the all day row");
        assert.strictEqual(moment(calendar.model.data.data[0].r_start).date(), 14,
            "the date should be 14");
        calendar.destroy();
    });

    QUnit.test('set event as all day when field is date (without all_day mapping)', async function (assert) {
        assert.expect(1);

        this.data.event.records[0].start_date = "2016-12-14";

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: `<calendar date_start="start_date" mode="week"></calendar>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });
        assert.containsOnce(calendar, '.fc-day-grid .fc-event-container',
            "should be one event in the all day row");
        calendar.destroy();
    });

    QUnit.test('quickcreate avoid double event creation', async function (assert) {
        assert.expect(1);
        var createCount = 0;
        var prom = testUtils.makeTestPromise();
        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                var result = this._super(route, args);
                if (args.method === "create") {
                    createCount++;
                    return prom.then(_.constant(result));
                }
                return result;
            },
        });

        // create a new event
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        var $input = $('.modal input:first');
        await testUtils.fields.editInput($input, 'new event in quick create');
        // Simulate ENTER pressed on Create button (after a TAB)
        $input.trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();
        await testUtils.dom.click($('.modal-footer button:first'));
        prom.resolve();
        await testUtils.nextTick();
        assert.strictEqual(createCount, 1,
            "should create only one event");

        calendar.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', async function (assert) {
        assert.expect(2);

        var instanceNumber = 0;
        testUtils.mock.patch(mixins.ParentedMixin, {
            init: function () {
                instanceNumber++;
                return this._super.apply(this, arguments);
            },
            destroy: function () {
                if (!this.isDestroyed()) {
                    instanceNumber--;
                }
                return this._super.apply(this, arguments);
            }
        });

        var params = {
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start_date" '+
                'all_day="allday" '+
                'mode="week" '+
                'attendee="partner_ids" '+
                'color="partner_id">'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        };

        var calendar = await createCalendarView(params);
        assert.ok(instanceNumber > 0);

        calendar.destroy();
        assert.strictEqual(instanceNumber, 0);

        testUtils.mock.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('create an event (async dialog) [REQUIRE FOCUS]', async function (assert) {
        assert.expect(3);

        var prom = testUtils.makeTestPromise();
        testUtils.mock.patch(Dialog, {
            open: function () {
                var _super = this._super.bind(this);
                prom.then(_super);
                return this;
            },
        });
        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        // create an event
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.strictEqual($('.modal').length, 0,
            "should not have opened the dialog yet");

        prom.resolve();
        await testUtils.nextTick();

        assert.strictEqual($('.modal').length, 1,
            "should have opened the dialog");
        assert.strictEqual($('.modal input')[0], document.activeElement,
            "should focus the input in the dialog");

        calendar.destroy();
        testUtils.mock.unpatch(Dialog);
    });

    QUnit.test('calendar is configured to have no groupBy menu', async function (assert) {
        assert.expect(1);

        var archs = {
            'event,1,calendar': '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday"/>',
            'event,false,search': '<search></search>',
        };

        var actions = [{
            id: 1,
            name: 'some action',
            res_model: 'event',
            type: 'ir.actions.act_window',
            views: [[1, 'calendar']]
        }];

        var actionManager = await createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        assert.containsNone(actionManager.$('.o_control_panel .o_search_options span.fa.fa-bars'),
            "the control panel has no groupBy menu");
        actionManager.destroy();
    });

    QUnit.test('timezone does not affect current day', async function (assert) {
        assert.expect(2);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start_date"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                getTZOffset: function () {
                    return -2400; // 40 hours timezone
                },
            },

        });

        var $sidebar = calendar.$('.o_calendar_sidebar');

        assert.strictEqual($sidebar.find('.ui-datepicker-current-day').text(), "12", "should highlight the target day");

        // go to previous day
        await testUtils.dom.click($sidebar.find('.ui-datepicker-current-day').prev());

        assert.strictEqual($sidebar.find('.ui-datepicker-current-day').text(), "11", "should highlight the selected day");

        calendar.destroy();
    });

    QUnit.test('timezone does not affect drag and drop', async function (assert) {
        assert.expect(10);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start" mode="month">'+
                '<field name="name"/>'+
                '<field name="start"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[0], [6], "event 6 is moved")
                    assert.deepEqual(args.args[1].start, "2016-11-29 08:00:00",
                        "event moved to 27th nov 16h00 +40 hours timezone")
                }
                return this._super(route, args);
            },
            session: {
                getTZOffset: function () {
                    return -2400; // 40 hours timezone
                },
            },
        });

        assert.strictEqual(calendar.$('.fc-event:eq(0)').text().replace(/\s/g, ''), "08:00event1");
        await testUtils.dom.click(calendar.$('.fc-event:eq(0)'));
        assert.strictEqual(calendar.$('.o_field_widget[name="start"]').text(), "12/09/2016 08:00:00");

        assert.strictEqual(calendar.$('.fc-event:eq(5)').text().replace(/\s/g, ''), "16:00event6");
        await testUtils.dom.click(calendar.$('.fc-event:eq(5)'));
        assert.strictEqual(calendar.$('.o_field_widget[name="start"]').text(), "12/16/2016 16:00:00");

        // Move event 6 as on first day of month view (27th november 2016)
        await testUtils.dragAndDrop(
            calendar.$('.fc-event').eq(5),
            calendar.$('.fc-day-top').first()
        );
        await testUtils.nextTick();

        assert.strictEqual(calendar.$('.fc-event:eq(0)').text().replace(/\s/g, ''), "16:00event6");
        await testUtils.dom.click(calendar.$('.fc-event:eq(0)'));
        assert.strictEqual(calendar.$('.o_field_widget[name="start"]').text(), "11/27/2016 16:00:00");

        assert.strictEqual(calendar.$('.fc-event:eq(1)').text().replace(/\s/g, ''), "08:00event1");
        await testUtils.dom.click(calendar.$('.fc-event:eq(1)'));
        assert.strictEqual(calendar.$('.o_field_widget[name="start"]').text(), "12/09/2016 08:00:00");

        calendar.destroy();
    });

    QUnit.test('timzeone does not affect calendar with date field', async function (assert) {
        assert.expect(11);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start_date" mode="month">'+
                '<field name="name"/>'+
                '<field name="start_date"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.strictEqual(args.args[0].start_date, "2016-12-20 00:00:00");
                }
                if (args.method === "write") {
                    assert.step(args.args[1].start_date);
                }
                return this._super(route, args);
            },
            session: {
                getTZOffset: function () {
                    return 120; // 2 hours timezone
                },
            },
        });

        // Create event (on 20 december)
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');
        await testUtils.triggerMouseEvent($cell, "mousedown");
        await testUtils.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        var $input = $('.modal-body input:first');
        await testUtils.fields.editInput($input, "An event");
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        await testUtils.nextTick();

        await testUtils.dom.click(calendar.$('.fc-event:contains(An event)'));
        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:last .o_field_date').text(), '12/20/2016', "should have correct start date");

        // Move event to another day (on 27 november)
        await testUtils.dragAndDrop(
            calendar.$('.fc-event').first(),
            calendar.$('.fc-day-top').first()
        );
        await testUtils.nextTick();
        assert.verifySteps(["2016-11-27 00:00:00"]);
        await testUtils.dom.click(calendar.$('.fc-event:contains(An event)'));
        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:last .o_field_date').text(), '11/27/2016', "should have correct start date");

        // Move event to last day (on 7 january)
        await testUtils.dragAndDrop(
            calendar.$('.fc-event').first(),
            calendar.$('.fc-day-top').last()
        );
        await testUtils.nextTick();
        assert.verifySteps(["2017-01-07 00:00:00"]);
        await testUtils.dom.click(calendar.$('.fc-event:contains(An event)'));
        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.strictEqual(calendar.$('.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:last .o_field_date').text(), '01/07/2017', "should have correct start date");
        calendar.destroy();
    });

    QUnit.test("drag and drop on month mode", async function (assert) {
        assert.expect(3);

        const calendar = await createCalendarView({
            arch:
                `<calendar date_start="start" date_stop="stop" mode="month" event_open_popup="true" quick_add="False">
                    <field name="name"/>
                    <field name="partner_id"/>
                </calendar>`,
            archs: archs,
            data: this.data,
            model: 'event',
            View: CalendarView,
            viewOptions: { initialDate: initialDate },
        });

        // Create event (on 20 december)
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        var $input = $('.modal-body input:first');
        await testUtils.fields.editInput($input, "An event");
        await testUtils.dom.click($('.modal button.btn-primary'));
        await testUtils.nextTick();

        await testUtils.dragAndDrop(
            calendar.$('.fc-event:contains("event 1")'),
            calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day-top:eq(1)'),
            { disableDrop: true },
        );
        assert.hasClass(calendar.$('.o_calendar_widget > [data-event-id="1"]'), 'dayGridMonth',
            "should have dayGridMonth class");

        // Move event to another day (on 19 december)
        await testUtils.dragAndDrop(
            calendar.$('.fc-event:contains("An event")'),
            calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day-top:eq(1)')
        );
        await testUtils.nextTick();
        await testUtils.dom.click(calendar.$('.fc-event:contains("An event")'));

        assert.containsOnce(calendar, '.popover:contains("07:00")',
            "start hour shouldn't have been changed");
        assert.containsOnce(calendar, '.popover:contains("19:00")',
            "end hour shouldn't have been changed");

        calendar.destroy();
    });

    QUnit.test("drag and drop on month mode with all_day mapping", async function (assert) {
        // Same test as before but in calendarEventToRecord (calendar_model.js) there is
        // different condition branching with all_day mapping or not
        assert.expect(2);

        const calendar = await createCalendarView({
            arch:
                `<calendar date_start="start" date_stop="stop" mode="month" event_open_popup="true" quick_add="False" all_day="allday">
                    <field name="name"/>
                    <field name="partner_id"/>
                </calendar>`,
            archs: archs,
            data: this.data,
            model: 'event',
            View: CalendarView,
            viewOptions: { initialDate: initialDate },
        });

        // Create event (on 20 december)
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        var $input = $('.modal-body input:first');
        await testUtils.fields.editInput($input, "An event");
        await testUtils.dom.click($('.o_field_widget[name="allday"] input'));
        await testUtils.nextTick();

        // use datepicker to enter a date: 12/20/2016 07:00:00
        testUtils.dom.openDatepicker($('.o_field_widget[name="start"].o_datepicker'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(07)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]'));

        // use datepicker to enter a date: 12/20/2016 19:00:00
        testUtils.dom.openDatepicker($('.o_field_widget[name="stop"].o_datepicker'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(19)'));
        await testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]'));

        await testUtils.dom.click($('.modal button.btn-primary'));
        await testUtils.nextTick();

        // Move event to another day (on 19 december)
        await testUtils.dom.dragAndDrop(
            calendar.$('.fc-event:contains("An event")'),
            calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day-top:eq(1)')
        );
        await testUtils.nextTick();
        await testUtils.dom.click(calendar.$('.fc-event:contains("An event")'));

        assert.containsOnce(calendar, '.popover:contains("07:00")',
            "start hour shouldn't have been changed");
        assert.containsOnce(calendar, '.popover:contains("19:00")',
            "end hour shouldn't have been changed");

        calendar.destroy();
    });

    QUnit.test('drag and drop on month mode with date_start and date_delay', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start" date_delay="delay" mode="month">'+
                '<field name="name"/>'+
                '<field name="start"/>'+
                '<field name="delay"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    // delay should not be written at drag and drop
                    assert.equal(args.args[1].delay, undefined)
                }
                return this._super(route, args);
            },
        });

        // Create event (on 20 december)
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');
        await testUtils.triggerMouseEvent($cell, "mousedown");
        await testUtils.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        var $input = $('.modal-body input:first');
        await testUtils.fields.editInput($input, "An event");
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        await testUtils.nextTick();

        // Move event to another day (on 27 november)
        await testUtils.dragAndDrop(
            calendar.$('.fc-event').first(),
            calendar.$('.fc-day-top').first()
        );
        await testUtils.nextTick();

        calendar.destroy();
    });

    QUnit.test('form_view_id attribute works (for creating events)', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month" '+
                'form_view_id="42"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    // we simulate here the case where a create call with just
                    // the field name fails.  This is a normal flow, the server
                    // reject the create rpc (quick create), then the web client
                    // fall back to a form view. This happens typically when a
                    // model has required fields
                    return Promise.reject('None shall pass!');
                }
                return this._super(route, args);
            },
            intercepts: {
                do_action: function (event) {
                    assert.strictEqual(event.data.action.views[0][0], 42,
                        "should do a do_action with view id 42");
                },
            },
        });

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        await testUtils.dom.triggerMouseEvent($cell, "mousedown");
        await testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        var $input = $('.modal-body input:first');
        await testUtils.fields.editInput($input, "It's just a fleshwound");
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        await testUtils.nextTick(); // wait a little before to finish the test
        calendar.destroy();
    });

    QUnit.test('form_view_id attribute works with popup (for creating events)', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month" '+
                'event_open_popup="true" ' +
                'quick_add="false" ' +
                'form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (args.method === "load_views") {
                    assert.strictEqual(args.kwargs.views[0][0], 1,
                        "should load view with id 1");
                }
                return this._super(route, args);
            },
        });

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        await testUtils.dom.triggerMouseEvent($cell, "mousedown");
        await testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();
        calendar.destroy();
    });

    QUnit.test('calendar fallback to form view id in action if necessary', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
                action: {views: [{viewID: 1, type: 'kanban'}, {viewID: 43, type: 'form'}]}
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    // we simulate here the case where a create call with just
                    // the field name fails.  This is a normal flow, the server
                    // reject the create rpc (quick create), then the web client
                    // fall back to a form view. This happens typically when a
                    // model has required fields
                    return Promise.reject('None shall pass!');
                }
                return this._super(route, args);
            },
            intercepts: {
                do_action: function (event) {
                    assert.strictEqual(event.data.action.views[0][0], 43,
                        "should do a do_action with view id 43");
                },
            },
        });

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        var $input = $('.modal-body input:first');
        await testUtils.fields.editInput($input, "It's just a fleshwound");
        await testUtils.dom.click($('.modal button.btn:contains(Create)'));
        calendar.destroy();
    });

    QUnit.test('fullcalendar initializes with right locale', async function (assert) {
        assert.expect(1);

        var initialLocale = moment.locale();
        // This will set the locale to zz
        moment.defineLocale('zz', {
            longDateFormat: {
                L: 'DD/MM/YYYY'
            },
            weekdaysShort: ["zz1.", "zz2.", "zz3.", "zz4.", "zz5.", "zz6.", "zz7."],
        });

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
                action: {views: [{viewID: 1, type: 'kanban'}, {viewID: 43, type: 'form'}]}
            },

        });

        assert.strictEqual(calendar.$('.fc-day-header:first').text(), "zz1. 11",
            'The day should be in the given locale specific format');

        moment.locale(initialLocale);

        calendar.destroy();
    });

    QUnit.test('default week start (US) month mode', async function (assert) {
        // if not given any option, default week start is on Sunday
        assert.expect(8);

        // 2019-09-12 08:00:00
        var initDate = new Date(2019, 8, 12, 8, 0, 0);
        initDate = new Date(initDate.getTime() - initDate.getTimezoneOffset()*60*1000);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initDate,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start","<=","2019-10-12 23:59:59"],
                        ["stop",">=","2019-09-01 00:00:00"]
                    ],
                    'The domain to search events in should be correct');
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Sunday",
            "The first day of the week should be Sunday");
        assert.strictEqual(calendar.$('.fc-day-header').last().text(), "Saturday",
            "The last day of the week should be Saturday");

        var $firstDay = calendar.$('.fc-day-top').first();

        assert.strictEqual($firstDay.find('.fc-week-number').text(), "36",
            "The number of the week should be correct");
        assert.strictEqual($firstDay.find('.fc-day-number').text(), "1",
            "The first day of the week should be 2019-09-01");
        assert.strictEqual($firstDay.data('date'), "2019-09-01",
            "The first day of the week should be 2019-09-01");

        var $lastDay = calendar.$('.fc-day-top').last();
        assert.strictEqual($lastDay.text(), "12",
            "The last day of the week should be 2019-10-12");
        assert.strictEqual($lastDay.data('date'), "2019-10-12",
            "The last day of the week should be 2019-10-12");

        calendar.destroy();
    });

    QUnit.test('European week start month mode', async function (assert) {
        assert.expect(8);

        // 2019-09-12 08:00:00
        var initDate = new Date(2019, 8, 15, 8, 0, 0);
        initDate = new Date(initDate.getTime() - initDate.getTimezoneOffset()*60*1000);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initDate,
            },
            translateParameters: {
                week_start: 1,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start","<=","2019-10-06 23:59:59"],
                        ["stop",">=","2019-08-26 00:00:00"]
                    ],
                    'The domain to search events in should be correct');
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Monday",
            "The first day of the week should be Monday");
        assert.strictEqual(calendar.$('.fc-day-header').last().text(), "Sunday",
            "The last day of the week should be Sunday");

        var $firstDay = calendar.$('.fc-day-top').first();
        assert.strictEqual($firstDay.find('.fc-week-number').text(), "35",
            "The number of the week should be correct");
        assert.strictEqual($firstDay.find('.fc-day-number').text(), "26",
            "The first day of the week should be 2019-09-01");
        assert.strictEqual($firstDay.data('date'), "2019-08-26",
            "The first day of the week should be 2019-08-26");

        var $lastDay = calendar.$('.fc-day-top').last();
        assert.strictEqual($lastDay.text(), "6",
            "The last day of the week should be 2019-10-06");
        assert.strictEqual($lastDay.data('date'), "2019-10-06",
            "The last day of the week should be 2019-10-06");

        calendar.destroy();
    });

    QUnit.test('Monday week start week mode', async function (assert) {
        assert.expect(3);

        // 2019-09-12 08:00:00
        var initDate = new Date(2019, 8, 15, 8, 0, 0);
        initDate = new Date(initDate.getTime() - initDate.getTimezoneOffset()*60*1000);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initDate,
            },
            translateParameters: {
                week_start: 1,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start","<=","2019-09-15 23:59:59"],
                        ["stop",">=","2019-09-09 00:00:00"]
                    ],
                    'The domain to search events in should be correct');
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Mon 9",
            "The first day of the week should be Monday the 9th");
        assert.strictEqual(calendar.$('.fc-day-header').last().text(), "Sun 15",
            "The last day of the week should be Sunday the 15th");

        calendar.destroy();
    });

    QUnit.test('Saturday week start week mode', async function (assert) {
        assert.expect(3);

        // 2019-09-12 08:00:00
        var initDate = new Date(2019, 8, 12, 8, 0, 0);
        initDate = new Date(initDate.getTime() - initDate.getTimezoneOffset()*60*1000);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week">'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initDate,
            },
            translateParameters: {
                week_start: 6,
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'event') {
                    assert.deepEqual(args.kwargs.domain, [
                        ["start","<=","2019-09-13 23:59:59"],
                        ["stop",">=","2019-09-07 00:00:00"]
                    ],
                    'The domain to search events in should be correct');
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Sat 7",
            "The first day of the week should be Saturday the 7th");
        assert.strictEqual(calendar.$('.fc-day-header').last().text(), "Fri 13",
            "The last day of the week should be Friday the 13th");

        calendar.destroy();
    });

    QUnit.test('edit record and attempt to create a record with "create" attribute set to false', async function (assert) {
        assert.expect(8);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" '+
                'event_open_popup="true" '+
                'create="false" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month"/>',
            archs: archs,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {name: 'event 4 modified'}, "should update the record");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                initialDate: initialDate,
            },
        });

        // editing existing events should still be possible
        // click on an existing event to open the formViewDialog

        await testUtils.dom.click(calendar.$('.fc-event:contains(event 4) .fc-content'));

        assert.ok(calendar.$('.o_cw_popover').length, "should open a popover clicking on event");
        assert.ok(calendar.$('.o_cw_popover .o_cw_popover_edit').length, "popover should have an edit button");
        assert.ok(calendar.$('.o_cw_popover .o_cw_popover_delete').length, "popover should have a delete button");
        assert.ok(calendar.$('.o_cw_popover .o_cw_popover_close').length, "popover should have a close button");

        await testUtils.dom.click(calendar.$('.o_cw_popover .o_cw_popover_edit'));

        assert.ok($('.modal-body').length, "should open the form view in dialog when click on edit");

        await testUtils.fields.editInput($('.modal-body input:first'), 'event 4 modified');
        await testUtils.dom.click($('.modal-footer button.btn:contains(Save)'));

        assert.notOk($('.modal-body').length, "save button should close the modal");

        // creating an event should not be possible
        // attempt to create a new event with create set to false

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');

        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.notOk($('.modal-sm').length, "shouldn't open a quick create dialog for creating a new event with create attribute set to false");

        calendar.destroy();
    });


    QUnit.test('attempt to create record with "create" and "quick_add" attributes set to false', async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" '+
                'create="false" '+
                'event_open_popup="true" '+
                'quick_add="false" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month"/>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        // attempt to create a new event with create set to false

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(5) .fc-day:eq(2)');

        testUtils.dom.triggerMouseEvent($cell, "mousedown");
        testUtils.dom.triggerMouseEvent($cell, "mouseup");
        await testUtils.nextTick();

        assert.strictEqual($('.modal').length, 0, "shouldn't open a form view for creating a new event with create attribute set to false");

        calendar.destroy();
    });

    QUnit.test('attempt to create multiples events and the same day and check the ordering on month view', async function (assert) {
        assert.expect(3);
        /*
         This test aims to verify that the order of the event in month view is coherent with their start date.
         */
        var initDate = new Date(2020, 2, 12, 8, 0, 0); //12 of March
        this.data.event.records = [
            {id: 1, name: "Second event", start: "2020-03-12 05:00:00", stop: "2020-03-12 07:00:00", allday: false},
            {id: 2, name: "First event", start: "2020-03-12 02:00:00", stop: "2020-03-12 03:00:00", allday: false},
            {id: 3, name: "Third event", start: "2020-03-12 08:00:00", stop: "2020-03-12 09:00:00", allday: false},
        ];
        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: `<calendar date_start="start" date_stop="stop" all_day="allday" mode="month" />`,
            archs: archs,
            viewOptions: {
                initialDate: initDate,
            },
        });
        assert.ok(calendar.$('.o_calendar_view').find('.fc-view-container').length, "should display in the calendar"); // OK
        // Testing the order of the events: by start date
        assert.strictEqual(calendar.$('.o_event_title').length, 3, "3 events should be available"); // OK
        assert.strictEqual(calendar.$('.o_event_title').first().text(), 'First event', "First event should be on top");
        calendar.destroy();
    });

    QUnit.test("drag and drop 24h event on week mode", async function (assert) {
        assert.expect(1);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: `
                <calendar
                    event_open_popup="true"
                    quick_add="False"
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"
                    mode="week"
                 />
            `,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        }, {positionalClicks: true});

        var top = calendar.$('.fc-axis:contains(8:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.dom.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }

        top = calendar.$('.fc-axis:contains(8:00)').offset().top - 5;
        var leftNextDay = calendar.$('.fc-day:eq(3)').offset().left + 5;
        testUtils.dom.triggerPositionalMouseEvent(leftNextDay, top, "mousemove");
        await testUtils.dom.triggerPositionalMouseEvent(leftNextDay, top, "mouseup");
        await testUtils.nextTick();
        assert.equal($('.o_field_boolean.o_field_widget[name=allday] input').is(':checked'), false,
            "The event must not have the all_day active");
        await testUtils.dom.click($('.modal button.btn:contains(Discard)'));

        calendar.destroy();
    });

    QUnit.test('correctly display year view', async function (assert) {
        assert.expect(27);

        const calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: `
                <calendar
                    create="false"
                    event_open_popup="true"
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"
                    mode="year"
                    attendee="partner_ids"
                    color="partner_id"
                >
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
                    <field name="partner_id" filters="1" invisible="1"/>
                </calendar>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        }, {positionalClicks: true});

        // Check view
        assert.containsN(calendar, '.fc-month', 12);
        assert.strictEqual(
            calendar.el.querySelector('.fc-month:first-child .fc-header-toolbar').textContent,
            'Jan 2016'
        );
        assert.containsN(calendar.el, '.fc-bgevent', 7,
            'There should be 6 events displayed but there is 1 split on 2 weeks');

        async function clickDate(date) {
            const el = calendar.el.querySelector(`.fc-day-top[data-date="${date}"]`);
            el.scrollIntoView(); // scroll to it as the calendar could be too small

            testUtils.dom.triggerMouseEvent(el, "mousedown");
            testUtils.dom.triggerMouseEvent(el, "mouseup");

            await testUtils.nextTick();
        }

        assert.notOk(calendar.el.querySelector('.fc-day-top[data-date="2016-11-17"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-11-17');
        assert.containsNone(calendar, '.o_cw_popover');

        assert.ok(calendar.el.querySelector('.fc-day-top[data-date="2016-11-16"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-11-16');
        assert.containsOnce(calendar, '.o_cw_popover');
        let popoverText = calendar.el.querySelector('.o_cw_popover')
            .textContent.replace(/\s{2,}/g, ' ').trim();
        assert.strictEqual(popoverText, 'November 14-16, 2016 event 7');
        await testUtils.dom.click(calendar.el.querySelector('.o_cw_popover_close'));
        assert.containsNone(calendar, '.o_cw_popover');

        assert.ok(calendar.el.querySelector('.fc-day-top[data-date="2016-11-14"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-11-14');
        assert.containsOnce(calendar, '.o_cw_popover');
        popoverText = calendar.el.querySelector('.o_cw_popover')
            .textContent.replace(/\s{2,}/g, ' ').trim();
        assert.strictEqual(popoverText, 'November 14-16, 2016 event 7');
        await testUtils.dom.click(calendar.el.querySelector('.o_cw_popover_close'));
        assert.containsNone(calendar, '.o_cw_popover');

        assert.notOk(calendar.el.querySelector('.fc-day-top[data-date="2016-11-13"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-11-13');
        assert.containsNone(calendar, '.o_cw_popover');

        assert.notOk(calendar.el.querySelector('.fc-day-top[data-date="2016-12-10"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-12-10');
        assert.containsNone(calendar, '.o_cw_popover');

        assert.ok(calendar.el.querySelector('.fc-day-top[data-date="2016-12-12"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-12-12');
        assert.containsOnce(calendar, '.o_cw_popover');
        popoverText = calendar.el.querySelector('.o_cw_popover')
            .textContent.replace(/\s{2,}/g, ' ').trim();
        assert.strictEqual(popoverText, 'December 12, 2016 event 2 event 3');
        await testUtils.dom.click(calendar.el.querySelector('.o_cw_popover_close'));
        assert.containsNone(calendar, '.o_cw_popover');

        assert.ok(calendar.el.querySelector('.fc-day-top[data-date="2016-12-14"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-12-14');
        assert.containsOnce(calendar, '.o_cw_popover');
        popoverText = calendar.el.querySelector('.o_cw_popover')
            .textContent.replace(/\s{2,}/g, ' ').trim();
        assert.strictEqual(popoverText,
            'December 14, 2016 event 4 December 13-20, 2016 event 5');
        await testUtils.dom.click(calendar.el.querySelector('.o_cw_popover_close'));
        assert.containsNone(calendar, '.o_cw_popover');

        assert.notOk(calendar.el.querySelector('.fc-day-top[data-date="2016-12-21"]')
            .classList.contains('fc-has-event'));
        await clickDate('2016-12-21');
        assert.containsNone(calendar, '.o_cw_popover');

        calendar.destroy();
    });

    QUnit.test('toggle filters in year view', async function (assert) {
        assert.expect(42);

        const calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: `
                <calendar
                    event_open_popup="true"
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"
                    mode="year"
                    attendee="partner_ids"
                    color="partner_id"
                >
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
                    <field name="partner_id" filters="1" invisible="1"/>
                '</calendar>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        function checkEvents(countMap) {
            for (const [id, count] of Object.entries(countMap)) {
                assert.containsN(calendar, `.fc-bgevent[data-event-id="${id}"]`, count);
            }
        }

        checkEvents({ 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 7: 1, });
        await testUtils.dom.click(calendar.el.querySelector(
            '#o_cw_filter_collapse_attendees .o_calendar_filter_item[data-value="2"] label'));
        checkEvents({ 1: 1, 2: 1, 3: 1, 4: 1, 5: 0, 7: 0, });
        await testUtils.dom.click(calendar.el.querySelector(
            '#o_cw_filter_collapse_user .o_calendar_filter_item[data-value="1"] label'));
        checkEvents({ 1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 7: 0, });
        await testUtils.dom.click(calendar.el.querySelector(
            '#o_cw_filter_collapse_user .o_calendar_filter_item[data-value="4"] label'));
        checkEvents({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, });
        await testUtils.dom.click(calendar.el.querySelector(
            '#o_cw_filter_collapse_attendees .o_calendar_filter_item[data-value="1"] label'));
        checkEvents({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, });
        await testUtils.dom.click(calendar.el.querySelector(
            '#o_cw_filter_collapse_attendees .o_calendar_filter_item[data-value="2"] label'));
        checkEvents({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, });
        await testUtils.dom.click(calendar.el.querySelector(
            '#o_cw_filter_collapse_user .o_calendar_filter_item[data-value="4"] label'));
        checkEvents({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 2, 7: 0, });

        calendar.destroy();
    });

    QUnit.test('allowed scales', async function (assert) {
        assert.expect(8);

        let calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
                `<calendar
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"/>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.containsOnce(calendar, '.o_calendar_scale_buttons .o_calendar_button_day');
        assert.containsOnce(calendar, '.o_calendar_scale_buttons .o_calendar_button_week');
        assert.containsOnce(calendar, '.o_calendar_scale_buttons .o_calendar_button_month');
        assert.containsOnce(calendar, '.o_calendar_scale_buttons .o_calendar_button_year');

        calendar.destroy();

        calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
                `<calendar
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"
                    scales="day,week"/>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.containsOnce(calendar, '.o_calendar_scale_buttons .o_calendar_button_day');
        assert.containsOnce(calendar, '.o_calendar_scale_buttons .o_calendar_button_week');
        assert.containsNone(calendar, '.o_calendar_scale_buttons .o_calendar_button_month');
        assert.containsNone(calendar, '.o_calendar_scale_buttons .o_calendar_button_year');

        calendar.destroy();
    });

    QUnit.test('click outside the popup should close it', async function (assert) {
        assert.expect(4);

        var calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
                `<calendar
                    create="false"
                    event_open_popup="true"
                    quick_add="false"
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"
                    mode="month"/>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.containsNone(calendar, '.o_cw_popover');

        await testUtils.dom.click(calendar.el.querySelector('.fc-event .fc-content'));
        assert.containsOnce(calendar, '.o_cw_popover',
            'open popup when click on event');

        await testUtils.dom.click(calendar.el.querySelector('.o_cw_body'));
        assert.containsOnce(calendar, '.o_cw_popover',
            'keep popup openned when click inside popup');

        await testUtils.dom.click(calendar.el.querySelector('.o_content'));
        assert.containsNone(calendar, '.o_cw_popover',
            'close popup when click outside popup');

        calendar.destroy();
    });

    QUnit.test("fields are added in the right order in popover", async function (assert) {
        assert.expect(3);

        const def = testUtils.makeTestPromise();
        const DeferredWidget = AbstractField.extend({
            async start() {
                await this._super(...arguments);
                await def;
            }
        });
        fieldRegistry.add("deferred_widget", DeferredWidget);

        const calendar = await createCalendarView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
                `<calendar
                    date_start="start"
                    date_stop="stop"
                    all_day="allday"
                    mode="month"
                >
                    <field name="user_id" widget="deferred_widget" />
                    <field name="name" />
                </calendar>`,
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        await testUtils.dom.click(calendar.$(`[data-event-id="4"]`));
        assert.containsNone(calendar, ".o_cw_popover");

        def.resolve();
        await testUtils.nextTick();
        assert.containsOnce(calendar, ".o_cw_popover");

        assert.strictEqual(
            calendar.$(".o_cw_popover .o_cw_popover_fields_secondary").text(),
            "user : name : event 4"
        );

        calendar.destroy();
        delete fieldRegistry.map.deferred_widget;
    });

});

});
