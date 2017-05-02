odoo.define('web.calendar_tests', function (require) {
"use strict";

var CalendarView = require('web.CalendarView');
var CalendarRenderer = require('web.CalendarRenderer');
var testUtils = require('web.test_utils');
var session = require('web.session');


CalendarRenderer.include({
    getAvatars: function () {
        var res = this._super.apply(this, arguments);
        for (var k in res) {
            res[k] = res[k].replace(/src="([^"]+)"/, 'src="#test:\$1"');
        }
        return res;
    }
});


var createView = testUtils.createView;

var initialDate = new Date("2016-12-12T08:00:00Z");


QUnit.module('Views', {
    beforeEach: function () {
        session.uid = -1; // TO CHECK
        this.data = {
            event: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'user'},
                    parnter_id: {string: "user", type: "many2one", relation: 'partner', related: 'user_id.parnter_id'},
                    name: {string: "name", type: "char"},
                    start_date: {string: "start date", type: "date"},
                    stop_date: {string: "stop date", type: "date"},
                    start: {string: "start datetime", type: "datetime"},
                    stop: {string: "stop datetime", type: "datetime"},
                    allday: {string: "allday", type: "boolean"},
                    partner_ids: {string: "attendees", type: "one2many", relation: 'partner'},
                    type: {string: "type", type: "integer"},
                },
                records: [
                    {id: 1, user_id: session.uid, partner_id: 1, name: "event 1", start: "2016-12-11 00:00:00", stop: "2016-12-11 00:00:00", allday: false, partner_ids: [1,2,3], type: 1},
                    {id: 2, user_id: session.uid, partner_id: 1, name: "event 2", start: "2016-12-12 10:55:05", stop: "2016-12-12 14:55:05", allday: false, partner_ids: [1,2], type: 3},
                    {id: 3, user_id: 4, partner_id: 4, name: "event 3", start: "2016-12-12 15:55:05", stop: "2016-12-12 16:55:05", allday: false, partner_ids: [1], type: 2},
                    {id: 4, user_id: session.uid, partner_id: 1, name: "event 4", start: "2016-12-14 15:55:05", stop: "2016-12-14 18:55:05", allday: true, partner_ids: [1], type: 2},
                    {id: 5, user_id: 4, partner_id: 4, name: "event 5", start: "2016-12-13 15:55:05", stop: "2016-12-20 18:55:05", allday: false, partner_ids: [2,3], type: 2},
                    {id: 6, user_id: session.uid, partner_id: 1, name: "event 6", start: "2016-12-18 08:00:00", stop: "2016-12-18 09:00:00", allday: false, partner_ids: [3], type: 3}
                ],
                check_access_rights: function () {
                    return $.when(true);
                }
            },
            user: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    parnter_id: {string: "partner", type: "many2one", relation: 'partner'},
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
    }
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
        "event,1,form": {
            attrs: {},
            children: [
                {
                    attrs: {
                        modifiers: '{"invisible": true}',
                        name: "allday"
                    },
                    children: [],
                    tag: 'field'
                },
                {
                    attrs: {
                        modifiers: '{"invisible": [["allday","=",false]]}',
                        name: "start"
                    },
                    children: [],
                    tag: 'field'
                },
                {
                    attrs: {
                        modifiers: '{"invisible": [["allday","=",true]]}',
                        name: "stop"
                    },
                    children: [],
                    tag: 'field'
                }
            ],
            tag: "form"
        }
    };

    QUnit.test('simple calendar rendering', function (assert) {
        assert.expect(19);

        var calendar = createView({
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
                'color="parnter_id">'+
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.ok(calendar.$('.o_calendar_view').find('.fc-view-container').length, "should instance of fullcalendar");

        var $sidebar = calendar.$('.o_calendar_sidebar');

        assert.strictEqual($sidebar.find('.ui-state-active').text(), "12", "should highlight the target day");

        // test view scales

        assert.strictEqual(calendar.$('.fc-event').length, 9, "should display 9 events on the week (4 event + 5 days event)");
        assert.strictEqual($sidebar.find('.o_selected_range').length, 7, "week scale should highlight 7 days in mini calendar");

        calendar.$buttons.find('.o_calendar_button_day').trigger('click'); // display only one day
        assert.strictEqual(calendar.$('.fc-event').length, 2, "should display 2 events on the day");
        assert.strictEqual($sidebar.find('.o_selected_range').length, 1, "should highlight the target day in mini calendar");

        calendar.$buttons.find('.o_calendar_button_month').trigger('click'); // display all the month
        assert.strictEqual(calendar.$('.fc-event').length, 6, "should display 6 events on the month (5 events + 2 week event - 1 'event 6' is filtered)");
        assert.strictEqual($sidebar.find('.o_selected_range').length, 31, "month scale should highlight all days in mini calendar");

        // test filters

        assert.strictEqual($sidebar.find('.o_calendar_filter').length, 2, "should display 3 filters");

        var $typeFilter =  $sidebar.find('.o_calendar_filter:has(h3:contains(user))');
        assert.ok($typeFilter.length, "should display 'user' filter");
        assert.strictEqual($typeFilter.find('.o_calendar_filter_item').length, 1, "should display 1 filter items for 'user'");

        var $attendeesFilter =  $sidebar.find('.o_calendar_filter:has(h3:contains(attendees))');
        assert.ok($attendeesFilter.length, "should display 'attendees' filter");
        assert.strictEqual($attendeesFilter.find('.o_calendar_filter_item').length, 3, "should display 3 filter items for 'attendees' who use write_model (2 saved + Everything)");
        assert.ok($attendeesFilter.find('.o_field_many2one').length, "should display one2many search bar for 'attendees' filter");

        // test search bar in filter

        $sidebar.find('input[type="text"]').trigger('click');
        assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').length, 2, "should display 2 choices in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
        $('ul.ui-autocomplete li:first').trigger('click');
        assert.strictEqual($sidebar.find('.o_calendar_filter:has(h3:contains(attendees)) .o_calendar_filter_item').length, 4, "should display 4 filter items for 'attendees'");
        $sidebar.find('input[type="text"]').trigger('click');
        assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').text(), "partner 4", "should display the last choice in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
        $sidebar.find('.o_calendar_filter_item[data-id="1"] .o_remove').trigger('click');
        assert.ok($('.modal button.btn:contains(Ok)').length, "should display the confirm message");
        $('.modal button.btn:contains(Ok)').trigger('click');
        assert.strictEqual($sidebar.find('.o_calendar_filter:has(h3:contains(attendees)) .o_calendar_filter_item').length, 3, "click on remove then should display 3 filter items for 'attendees'");
        calendar.destroy();
    });

    QUnit.test('create and change events', function (assert) {
        assert.expect(26);

        var calendar = createView({
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
                'mode="month" '+
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.ok(calendar.$('.fc-month-view').length, "should display in month mode");

        // click on an existing event to open the formViewDialog

        calendar.$('.fc-event:contains(event 4) .fc-content').trigger('click');

        assert.ok($('.modal-body').length, "should open the form view in dialog when click on event");
        assert.ok($('.modal button.btn:contains(Edit)').length, "formViewDialog should be in readonly mode");
        assert.ok($('.modal button.btn:contains(Delete)').length, "formViewDialog should have a delete button");

        $('.modal button.btn:contains(Edit)').trigger('click');

        assert.ok($('.modal-body').length, "should switch the modal in edit mode");
        assert.notOk($('.modal button.btn:contains(Delete)').length, "formViewDialog should not have a delete button in edit mode");

        $('.modal-body input:first').val('event 4 modified').trigger('input');
        $('.modal button.btn:contains(Save)').trigger('click');

        assert.notOk($('.modal-body').length, "save button should close the modal");
        assert.ok(calendar.$('.fc-event:contains(event 4 modified)').length, "should display the updated records");

        // create a new event, quick create only

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.ok($('.modal-dialog.modal-sm').length, "should open the quick create dialog");

        $('.modal-body input:first').val('new event in quick create').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click').trigger('click');

        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create)').length, 1, "should display the new record");
        assert.strictEqual(calendar.$('td.fc-event-container[colspan]').length, 2, "should the new record have only one day");

        // create a new event, quick create only (validated by pressing enter key)

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.ok($('.modal-dialog.modal-sm').length, "should open the quick create dialog");

        $('.modal-body input:first')
            .val('new event in quick create validated by pressing enter key.')
            .trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}))
            .trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}));

        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create validated by pressing enter key.)').length, 1, "should display the new record by pressing enter key");


        // create a new event and edit it

        $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.strictEqual($('.modal-dialog.modal-sm').length, 1, "should open the quick create dialog");

        $('.modal-body input:first').val('coucou').trigger('input');
        $('.modal button.btn:contains(Edit)').trigger('click');

        assert.strictEqual($('.modal-dialog.modal-lg .o_form_view').length, 1, "should open the slow create dialog");
        assert.strictEqual($('.modal-dialog.modal-lg .modal-title').text(), "Create: Events",
            "should use the string attribute as modal title");
        assert.strictEqual($('.modal-dialog.modal-lg .o_form_view input[name="name"]').val(), "coucou",
            "should have set the name from the quick create dialog");

        $('.modal-lg button.btn:contains(Save)').trigger('click');

        assert.strictEqual(calendar.$('.fc-event:contains(coucou)').length, 1, "should display the new record");

        // create a new event with 2 days

        $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell.next(), "mousemove");
        testUtils.triggerMouseEvent($cell.next(), "mouseup");

        $('.modal input:first').val('new event in quick create 2').trigger('input');
        $('.modal button.btn:contains(Edit)').trigger('click');

        assert.strictEqual($('.modal-lg input:first').val(), 'new event in quick create 2', "should open the formViewDialog with default values");

        $('.modal-lg button.btn:contains(Save)').trigger('click');

        assert.notOk($('.modal').length, "should close dialogs");
        var $newevent2 = calendar.$('.fc-event:contains(new event in quick create 2)');
        assert.ok($newevent2.length, "should display the 2 days new record");
        assert.strictEqual($newevent2.closest('.fc-event-container').attr('colspan'), "2", "the new record should have 2 days");

        // delete the a record

        calendar.$('.fc-event:contains(event 4) .fc-content').trigger('click');
        $('.modal button.btn:contains(Delete)').trigger('click');
        assert.ok($('.modal button.btn:contains(Ok)').length, "should display the confirm message");
        $('.modal button.btn:contains(Ok)').trigger('click');
        assert.notOk(calendar.$('.fc-event:contains(event 4) .fc-content').length, "the record should be deleted");

        assert.strictEqual(calendar.$('.fc-event-container .fc-event').length, 10, "should display 10 events");
        // move to next month
        calendar.$buttons.find('.o_calendar_button_next').click();

        assert.strictEqual(calendar.$('.fc-event-container .fc-event').length, 0, "should display 0 events");

        calendar.destroy();
    });

    QUnit.test('create event with timezone in week mode', function (assert) {
        assert.expect(5);

        this.data.event.records = [];

        var calendar = createView({
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
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                tzOffset: 120
            },
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.kwargs.context, {
                        "default_name": null,
                        "default_start": "2016-12-13 06:00:00",
                        "default_stop": "2016-12-13 08:00:00",
                        "default_allday": null
                    },
                    "should send the context to create events");
                }
                return this._super(route, args);
            },
        });


        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        var top = calendar.$('.fc-axis:contains(8am)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        testUtils.triggerPositionalMouseEvent(left, top + 60, "mousemove");

        assert.strictEqual(calendar.$('.fc-content .fc-time').text(), "08:00 - 10:00",
            "should display the time in the calendar sticker");

        testUtils.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "08:00-10:00newevent",
            "should display the new event with time and title");

        assert.deepEqual($newevent.data('fcSeg').event.record,
            {
                display_name: "new event",
                start: "2016-12-13 06:00:00",
                stop: "2016-12-13 08:00:00",
                allday: false,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (quickCreate)");

        // delete record

        $newevent.trigger('click');
        $('.modal button.btn-default:contains(Delete)').trigger('click');
        $('.modal button.btn-primary:contains(Ok)').trigger('click');
        assert.strictEqual(calendar.$('.fc-content').length, 0, "should delete the record");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('create event with timezone in week mode with formViewDialog', function (assert) {
        assert.expect(7);

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

        var calendar = createView({
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
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                tzOffset: 120
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
                    assert.deepEqual(args.args[1], {
                          "allday": false,
                          "start": "2016-12-12 06:00:00",
                          "stop": "2016-12-12 08:00:00"
                        },
                    "should move the event");
                }
                return this._super(route, args);
            },
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        var top = calendar.$('.fc-axis:contains(8am)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        testUtils.triggerPositionalMouseEvent(left, top + 60, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Edit)').trigger('click');

        assert.strictEqual($('.o_field_widget[name="start"] input').val(), "12/13/2016 08:00:00",
            "should display the datetime");

        $('.modal-lg .o_field_boolean[name="allday"] input').trigger('click');

        assert.strictEqual($('.o_field_widget[name="start_date"] input').val(), "12/13/2016",
            "should display the date");

        $('.modal-lg .o_field_boolean[name="allday"] input').trigger('click');

        assert.strictEqual($('.o_field_widget[name="start"] input').val(), "12/13/2016 02:00:00",
            "should display the datetime from the date with the timezone");

        // use datepicker to enter a date: 12/13/2016 08:00:00
        $('.o_field_widget[name="start"] input').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(08)').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]').trigger('click');

        // use datepicker to enter a date: 12/13/2016 10:00:00
        $('.o_field_widget[name="stop"] input').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(10)').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]').trigger('click');

        $('.modal-lg button.btn:contains(Save)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "08:00-10:00newevent",
            "should display the new event with time and title");

        assert.deepEqual($newevent.data('fcSeg').event.record,
            {
                display_name: "new event",
                start: "2016-12-13 06:00:00",
                stop: "2016-12-13 08:00:00",
                allday: false,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (formViewDialog)");

        var pos = calendar.$('.fc-content').offset();
        left = pos.left + 5;
        top = pos.top + 5;

        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        left = calendar.$('.fc-day:eq(1)').offset().left + 5;
        testUtils.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top, "mouseup");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('create all day event', function (assert) {
        assert.expect(2);

        this.data.event.records = [];

        var calendar = createView({
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
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                tzOffset: 120
            },
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position


        var pos = calendar.$('.fc-bg td:eq(4)').offset();
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        pos = calendar.$('.fc-bg td:eq(5)').offset();
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");

        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "newevent",
            "should display the new event with time and title");

        assert.deepEqual($newevent.data('fcSeg').event.record,
            {
                display_name: "new event",
                start: "2016-12-14 00:00:00",
                stop: "2016-12-15 00:00:00",
                allday: true,
                name: "new event",
                id: 1
            },
            "the new record should have the utc datetime (quickCreate)");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('use mini calendar', function (assert) {
        assert.expect(2);

        var calendar = createView({
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
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            session: {
                tzOffset: 120
            },
        });

        assert.strictEqual(calendar.$('.fc-event').length, 9, "should display 9 events on the week (4 event + 5 days event)");
        $('.o_calendar_mini a:contains(19)').click();
        assert.strictEqual(calendar.$('.fc-event').length, 4, "should display 4 events on the week (1 event + 3 days event)");

        calendar.destroy();
    });

    QUnit.test('rendering, with many2many', function (assert) {
        assert.expect(1);

        this.data.event.fields.partner_ids.type = 'many2many';

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'event_open_popup="true" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday"> '+
                    '<field name="partner_ids" avatar_field="image" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        assert.strictEqual(calendar.$('.o_calendar_filter_items .o_cal_avatar').length, 3,
            "should have 3 avatars in the side bar");

        calendar.destroy();
    });

    QUnit.test('open form view', function (assert) {
        assert.expect(2);

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'string="Events" ' +
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month" '+
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        });

        // click on an existing event to open the form view

        testUtils.intercept(calendar, 'do_action', function (event) {
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
        calendar.$('.fc-event:contains(event 4) .fc-content').trigger('click');

        // create a new event and edit it

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");
        $('.modal-body input:first').val('coucou').trigger('input');

        testUtils.intercept(calendar, 'do_action', function (event) {
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

        $('.modal button.btn:contains(Edit)').trigger('click');

        calendar.destroy();
    });
});

});
