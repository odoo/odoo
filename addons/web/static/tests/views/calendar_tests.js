odoo.define('web.calendar_tests', function (require) {
"use strict";

var CalendarView = require('web.CalendarView');
var CalendarRenderer = require('web.CalendarRenderer');
var Dialog = require('web.Dialog');
var fieldUtils = require('web.field_utils');
var mixins = require('web.mixins');
var testUtils = require('web.test_utils');
var time = require('web.time');
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


var createView = testUtils.createView;
var createAsyncView = testUtils.createAsyncView;

var initialDate = new Date(2016, 11, 12, 8, 0, 0);
initialDate = new Date(initialDate.getTime() - initialDate.getTimezoneOffset()*60*1000);


QUnit.module('Views', {
    beforeEach: function () {
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
                    allday: {string: "allday", type: "boolean"},
                    partner_ids: {string: "attendees", type: "one2many", relation: 'partner', default: [[6, 0, [1]]]},
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
        "event,1,form":
            '<form>' +
                '<field name="allday" invisible="1"/>' +
                '<field name="start" attrs=\'{"invisible": [["allday","=",false]]}\'/>' +
                '<field name="stop" attrs=\'{"invisible": [["allday","=",true]]}\'/>' +
            '</form>',
    };

    QUnit.test('simple calendar rendering', function (assert) {
        assert.expect(24);
        var done = assert.async();

        this.data.event.records.push({
            id: 7,
            user_id: session.uid,
            partner_id: false,
            name: "event 7",
            start: "2016-12-18 09:00:00",
            stop: "2016-12-18 10:00:00",
            allday: false,
            partner_ids: [2],
            type: 1
        });

        createAsyncView({
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
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,

            viewOptions: {
                initialDate: initialDate,
            },
        }).then(function (calendar) {

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
            assert.strictEqual(calendar.$('.fc-event').length, 7, "should display 7 events on the month (5 events + 2 week event - 1 'event 6' is filtered + 1 'Undefined event')");
            assert.strictEqual($sidebar.find('.o_selected_range').length, 31, "month scale should highlight all days in mini calendar");

            // test filters

            assert.strictEqual($sidebar.find('.o_calendar_filter').length, 2, "should display 3 filters");

            var $typeFilter =  $sidebar.find('.o_calendar_filter:has(h3:contains(user))');
            assert.ok($typeFilter.length, "should display 'user' filter");
            assert.strictEqual($typeFilter.find('.o_calendar_filter_item').length, 3, "should display 3 filter items for 'user'");

            // filters which has no value should show with string "Undefined" and should show at the last
            assert.strictEqual($typeFilter.find('.o_calendar_filter_item:last').data('value'), false, "filters having false value should be displayed at last in filter items");
            assert.strictEqual($typeFilter.find('.o_calendar_filter_item:last span').text(), "Undefined", "filters having false value should display 'Undefined' string");

            var $attendeesFilter =  $sidebar.find('.o_calendar_filter:has(h3:contains(attendees))');
            assert.ok($attendeesFilter.length, "should display 'attendees' filter");
            assert.strictEqual($attendeesFilter.find('.o_calendar_filter_item').length, 3, "should display 3 filter items for 'attendees' who use write_model (2 saved + Everything)");
            assert.ok($attendeesFilter.find('.o_field_many2one').length, "should display one2many search bar for 'attendees' filter");

            assert.strictEqual(calendar.$('.fc-event').length, 7,
                "should display 7 events ('event 5' counts for 2 because it spans two weeks and thus generate two fc-event elements)");
            calendar.$('.o_calendar_filter .custom-checkbox input').first().click();  // Disable first filter
            assert.strictEqual(calendar.$('.fc-event').length, 4, "should now only display 4 event");
            calendar.$('.o_calendar_filter .custom-checkbox input').eq(1).click();  // Disable second filter
            assert.strictEqual(calendar.$('.fc-event').length, 0, "should not display any event anymore");

            // test search bar in filter
            $sidebar.find('input[type="text"]').trigger('click');
            assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').length, 2, "should display 2 choices in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
            $('ul.ui-autocomplete li:first').trigger('click');
            assert.strictEqual($sidebar.find('.o_calendar_filter:has(h3:contains(attendees)) .o_calendar_filter_item').length, 4, "should display 4 filter items for 'attendees'");
            $sidebar.find('input[type="text"]').trigger('click');
            assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').text(), "partner 4", "should display the last choice in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
            $sidebar.find('.o_calendar_filter_item .o_remove').first().trigger('click');
            assert.ok($('.modal-footer button.btn:contains(Ok)').length, "should display the confirm message");
            $('.modal-footer button.btn:contains(Ok)').trigger('click');
            assert.strictEqual($sidebar.find('.o_calendar_filter:has(h3:contains(attendees)) .o_calendar_filter_item').length, 3, "click on remove then should display 3 filter items for 'attendees'");
            calendar.destroy();
            done();
        });
    });

    QUnit.test('breadcrumbs are updated with the displayed period', function (assert) {
        assert.expect(3);

        var archs = {
            'event,1,calendar': '<calendar date_start="start" date_stop="stop" all_day="allday">' +
                '<field name="name"/>' +
            '</calendar>',
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

        var actionManager = createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
        });

        actionManager.doAction(1);

        // displays month mode by default
        assert.strictEqual(actionManager.controlPanel.$('.breadcrumb-item').text(),
            'Meetings Test (Dec 11 – 17, 2016)', "should display the current week");

        // switch to day mode
        actionManager.controlPanel.$('.o_calendar_button_day').click();
        assert.strictEqual(actionManager.controlPanel.$('.breadcrumb-item').text(),
            'Meetings Test (December 12, 2016)', "should display the current day");

        // switch to month mode
        actionManager.controlPanel.$('.o_calendar_button_month').click();
        assert.strictEqual(actionManager.controlPanel.$('.breadcrumb-item').text(),
            'Meetings Test (December 2016)', "should display the current month");

        actionManager.destroy();
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
        assert.ok($('.modal-footer button.btn:contains(Edit)').length, "formViewDialog should be in readonly mode");
        assert.ok($('.modal-footer button.btn:contains(Delete)').length, "formViewDialog should have a delete button");

        $('.modal-footer button.btn:contains(Edit)').trigger('click');

        assert.ok($('.modal-body').length, "should switch the modal in edit mode");
        assert.notOk($('.modal-footer button.btn:contains(Delete)').length, "formViewDialog should not have a delete button in edit mode");

        $('.modal-body input:first').val('event 4 modified').trigger('input');
        $('.modal-footer button.btn:contains(Save)').trigger('click');

        assert.notOk($('.modal-body').length, "save button should close the modal");
        assert.ok(calendar.$('.fc-event:contains(event 4 modified)').length, "should display the updated records");

        // create a new event, quick create only

        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.ok($('.modal-sm').length, "should open the quick create dialog");

        $('.modal-body input:first').val('new event in quick create').trigger('input');
        $('.modal-footer button.btn:contains(Create)').trigger('click').trigger('click');

        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create)').length, 1, "should display the new record after quick create");
        assert.strictEqual(calendar.$('td.fc-event-container[colspan]').length, 2, "should the new record have only one day");

        // create a new event, quick create only (validated by pressing enter key)

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.ok($('.modal-sm').length, "should open the quick create dialog");

        $('.modal-body input:first')
            .val('new event in quick create validated by pressing enter key.')
            .trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}))
            .trigger($.Event('keyup', {keyCode: $.ui.keyCode.ENTER}));

        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create validated by pressing enter key.)').length, 1, "should display the new record by pressing enter key");


        // create a new event and edit it

        $cell = calendar.$('.fc-day-grid .fc-row:eq(4) .fc-day:eq(2)');

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.strictEqual($('.modal-sm').length, 1, "should open the quick create dialog");

        $('.modal-body input:first').val('coucou').trigger('input');
        $('.modal-footer button.btn:contains(Edit)').trigger('click');

        assert.strictEqual($('.modal-lg .o_form_view').length, 1, "should open the slow create dialog");
        assert.strictEqual($('.modal-lg .modal-title').text(), "Create: Events",
            "should use the string attribute as modal title");
        assert.strictEqual($('.modal-lg .o_form_view input[name="name"]').val(), "coucou",
            "should have set the name from the quick create dialog");

        $('.modal-lg button.btn:contains(Save)').trigger('click');

        assert.strictEqual(calendar.$('.fc-event:contains(coucou)').length, 1, "should display the new record with string attribute");

        // create a new event with 2 days

        $cell = calendar.$('.fc-day-grid .fc-row:eq(3) .fc-day:eq(2)');

        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell.next(), "mousemove");
        testUtils.triggerMouseEvent($cell.next(), "mouseup");

        $('.modal-dialog input:first').val('new event in quick create 2').trigger('input');
        $('.modal-footer button.btn:contains(Edit)').trigger('click');

        assert.strictEqual($('.modal-lg input:first').val(), 'new event in quick create 2', "should open the formViewDialog with default values");

        $('.modal-lg button.btn:contains(Save)').trigger('click');

        assert.notOk($('.modal').length, "should close dialogs");
        var $newevent2 = calendar.$('.fc-event:contains(new event in quick create 2)');
        assert.ok($newevent2.length, "should display the 2 days new record");
        assert.strictEqual($newevent2.closest('.fc-event-container').attr('colspan'), "2", "the new record should have 2 days");

        // delete the a record

        calendar.$('.fc-event:contains(event 4) .fc-content').trigger('click');
        $('.modal-footer button.btn:contains(Delete)').trigger('click');
        assert.ok($('.modal-footer button.btn:contains(Ok)').length, "should display the confirm message");
        $('.modal-footer button.btn:contains(Ok)').trigger('click');
        assert.notOk(calendar.$('.fc-event:contains(event 4) .fc-content').length, "the record should be deleted");

        assert.strictEqual(calendar.$('.fc-event-container .fc-event').length, 10, "should display 10 events");
        // move to next month
        calendar.$buttons.find('.o_calendar_button_next').click();

        assert.strictEqual(calendar.$('.fc-event-container .fc-event').length, 0, "should display 0 events");

        calendar.destroy();
    });

    QUnit.test('quickcreate switching to actual create for required fields', function (assert) {
        assert.expect(4);

        var event = $.Event();
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
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    return $.Deferred().reject({
                        code: 200,
                        data: {},
                        message: "Odoo server error",
                    }, event);
                }
                return this._super(route, args);
            },
        });

        // create a new event
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.strictEqual($('.modal-sm .modal-title').text(), 'Create: Events',
            "should open the quick create dialog");

        $('.modal-body input:first').val('new event in quick create').trigger('input');
        $('.modal-footer button.btn:contains(Create)').trigger('click').trigger('click');

        // If the event is not default-prevented, a traceback will be raised, which we do not want
        assert.ok(event.isDefaultPrevented(), "fail deferred event should have been default-prevented");

        assert.strictEqual($('.modal-lg .modal-title').text(), 'Create: Events',
            "should have switched to a bigger modal for an actual create rather than quickcreate");
        assert.strictEqual($('.modal-lg main .o_form_view.o_form_editable').length, 1,
            "should open the full event form view in a dialog");

        calendar.destroy();
    });

    QUnit.test('create event with timezone in week mode European locale', function (assert) {
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

        var top = calendar.$('.fc-axis:contains(8:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }

        testUtils.triggerPositionalMouseEvent(left, top + 60, "mousemove");

        assert.strictEqual(calendar.$('.fc-content .fc-time').text(), "08:00 - 10:00",
            "should display the time in the calendar sticker");

        testUtils.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "08:00-10:00newevent12/13/201608:00:00False",
            "should display the new event with time, title and additional fields");

        assert.deepEqual($newevent.data('fcSeg').event.record,
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

        $newevent.trigger('click');
        $('.modal button.btn-secondary:contains(Delete)').trigger('click');
        $('.modal button.btn-primary:contains(Ok)').trigger('click');
        assert.strictEqual(calendar.$('.fc-content').length, 0, "should delete the record");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('default week start (US)', function (assert) {
        // if not given any option, default week start is on Sunday
        assert.expect(1);
        var done = assert.async();

        createAsyncView({
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
        }).then(function (calendar) {
            assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Sun 12/11",
                "The first day of the week should be Sunday");
            calendar.destroy();
            done();
        });
    });

    QUnit.test('European week start', function (assert) {
        // the week start depends on the locale
        assert.expect(1);
        var done = assert.async();

        createAsyncView({
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
        }).then(function (calendar) {
            assert.strictEqual(calendar.$('.fc-day-header').first().text(), "Mon 12/12",
                "The first day of the week should be Monday");
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

        createAsyncView({
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
            assert.strictEqual(calendar.$('.fc-week-number').text(), "W51",
                "We should be on the 51st week");
            calendar.destroy();
            done();
        });
    });

    QUnit.test('create event with timezone in week mode with formViewDialog European locale', function (assert) {
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
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        var top = calendar.$('.fc-axis:contains(8:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
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
        testUtils.openDatepicker($('.o_field_widget[name="start"].o_datepicker'));
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(08)').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]').trigger('click');

        // use datepicker to enter a date: 12/13/2016 10:00:00
        testUtils.openDatepicker($('.o_field_widget[name="stop"].o_datepicker'));
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
        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        left = calendar.$('.fc-day:eq(1)').offset().left + 5;
        testUtils.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top, "mouseup");

        // Move to "All day"
        expectedEvent = {
          "allday": true,
          "start": "2016-12-12 00:00:00",
          "stop": "2016-12-12 00:00:00"
        };
        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        top = calendar.$('.fc-day:eq(1)').offset().top + 5;
        testUtils.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top, "mouseup");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('create event with timezone in week mode American locale', function (assert) {
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

        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }

        testUtils.triggerPositionalMouseEvent(left, top + 60, "mousemove");

        assert.strictEqual(calendar.$('.fc-content .fc-time').text(), "8:00am - 10:00am",
            "should display the time in the calendar sticker");

        testUtils.triggerPositionalMouseEvent(left, top + 60, "mouseup");
        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "8:00am-10:00amnewevent12/13/201608:00:00False",
            "should display the new event with time, title and additional fields");

        assert.deepEqual($newevent.data('fcSeg').event.record,
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

        $newevent.trigger('click');
        $('.modal button.btn-secondary:contains(Delete)').trigger('click');
        $('.modal button.btn-primary:contains(Ok)').trigger('click');
        assert.strictEqual(calendar.$('.fc-content').length, 0, "should delete the record");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('create event with timezone in week mode with formViewDialog American locale', function (assert) {
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
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        var top = calendar.$('.fc-axis:contains(8am)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;

        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
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
        testUtils.openDatepicker($('.o_field_widget[name="start"].o_datepicker'));
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(08)').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]').trigger('click');

        // use datepicker to enter a date: 12/13/2016 10:00:00
        testUtils.openDatepicker($('.o_field_widget[name="stop"].o_datepicker'));
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker .timepicker-hour').trigger('click');
        $('.bootstrap-datetimepicker-widget .timepicker-hours td.hour:contains(10)').trigger('click');
        $('.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]').trigger('click');

        $('.modal-lg button.btn:contains(Save)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "8:00am-10:00amnewevent",
            "should display the new event with time and title");

        assert.deepEqual($newevent.data('fcSeg').event.record,
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
        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        left = calendar.$('.fc-day:eq(1)').offset().left + 5;
        testUtils.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top, "mouseup");

        // Move to "All day"
        expectedEvent = {
          "allday": true,
          "start": "2016-12-12 00:00:00",
          "stop": "2016-12-12 00:00:00"
        };
        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        top = calendar.$('.fc-day:eq(1)').offset().top + 5;
        testUtils.triggerPositionalMouseEvent(left, top, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top, "mouseup");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('check calendar week column timeformat and event content timeformat', function (assert) {
        assert.expect(2);

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
            translateParameters: {
                time_format: "%I:%M:%S",
            },
        });

        assert.strictEqual(calendar.$('.fc-axis:contains(8am)').length, 1, "calendar should show according to timeformat");
        assert.strictEqual(calendar.$('.fc-event:first:contains(12:00am)').length, 1,
            "event time format should 12 hour");

        calendar.destroy();
    });

    QUnit.test('create all day event in week mode', function (assert) {
        assert.expect(3);

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
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position


        var pos = calendar.$('.fc-bg td:eq(4)').offset();
        try {
            testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(5)').offset();
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");

        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "newevent",
            "should display the new event with time and title");
        assert.strictEqual($newevent.parent().attr('colspan'), "2",
            "should appear over two days.");

        assert.deepEqual($newevent.data('fcSeg').event.record,
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
        $view.remove();
    });

    QUnit.test('create all day event in week mode (no quickCreate)', function (assert) {
        assert.expect(1);

        this.data.event.records = [];

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week" '+
                'quick_add="False" '+
                'readonly_form_view_id="1">'+
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
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action.context, {
                        "default_name": null,
                        "default_start": "2016-12-14 05:00:00",
                        "default_stop": "2016-12-15 17:00:00",
                    },
                    "should send the correct data to create events");
                },
            },
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position


        var pos = calendar.$('.fc-bg td:eq(4)').offset();
        try {
            testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(5)').offset();
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('create event in month mode', function (assert) {
        assert.expect(4);

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
                'mode="month" '+
                'readonly_form_view_id="1">'+
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
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        var pos = calendar.$('.fc-bg td:eq(20)').offset();
        try {
            testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        pos = calendar.$('.fc-bg td:eq(21)').offset();
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mousemove");
        testUtils.triggerPositionalMouseEvent(pos.left+15, pos.top+15, "mouseup");

        $('.modal input:first').val('new event').trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');
        var $newevent = calendar.$('.fc-event:contains(new event)');

        assert.strictEqual($newevent.text().replace(/[\s\n\r]+/g, ''), "newevent",
            "should display the new event with time and title");
        assert.strictEqual($newevent.parent().attr('colspan'), "2",
            "should appear over two days.");

        assert.deepEqual($newevent.data('fcSeg').event.record, {
            display_name: "new event",
            start: fieldUtils.parse.datetime("2016-12-14 05:00:00", this.data.event.fields.start, {isUTC: true}),
            stop: fieldUtils.parse.datetime("2016-12-15 17:00:00", this.data.event.fields.stop, {isUTC: true}),
            name: "new event",
            id: 1
        }, "the new record should have the utc datetime (quickCreate)");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('use mini calendar', function (assert) {
        assert.expect(12);

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
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        assert.strictEqual(calendar.$('.fc-agendaWeek-view').length, 1, "should be in week mode");
        assert.strictEqual(calendar.$('.fc-event').length, 9, "should display 9 events on the week (4 event + 5 days event)");
        calendar.$('.o_calendar_mini a:contains(19)').click();
        // Clicking on a day in another week should switch to the other week view
        assert.strictEqual(calendar.$('.fc-agendaWeek-view').length, 1, "should be in week mode");
        assert.strictEqual(calendar.$('.fc-event').length, 4, "should display 4 events on the week (1 event + 3 days event)");
        // Clicking on a day in the same week should switch to that particular day view
        calendar.$('.o_calendar_mini a:contains(18)').click();
        assert.strictEqual(calendar.$('.fc-agendaDay-view').length, 1, "should be in day mode");
        assert.strictEqual(calendar.$('.fc-event').length, 2, "should display 2 events on the day");
        // Clicking on the same day should toggle between day, month and week views
        calendar.$('.o_calendar_mini a:contains(18)').click();
        assert.strictEqual(calendar.$('.fc-month-view').length, 1, "should be in month mode");
        assert.strictEqual(calendar.$('.fc-event').length, 7, "should display 7 events on the month (event 5 is on multiple weeks and generates to .fc-event)");
        calendar.$('.o_calendar_mini a:contains(18)').click();
        assert.strictEqual(calendar.$('.fc-agendaWeek-view').length, 1, "should be in week mode");
        assert.strictEqual(calendar.$('.fc-event').length, 4, "should display 4 events on the week (1 event + 3 days event)");
        calendar.$('.o_calendar_mini a:contains(18)').click();
        assert.strictEqual(calendar.$('.fc-agendaDay-view').length, 1, "should be in day mode");
        assert.strictEqual(calendar.$('.fc-event').length, 2, "should display 2 events on the day");

        calendar.destroy();
    });

    QUnit.test('rendering, with many2many', function (assert) {
        assert.expect(5);

        this.data.event.fields.partner_ids.type = 'many2many';
        this.data.event.records[0].partner_ids = [1,2,3,4,5];
        this.data.partner.records.push({id: 5, display_name: "partner 5", image: 'EEE'});

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

        var $event1Avatars = calendar.$('.fc-event .o_calendar_avatars').first();
        assert.strictEqual($event1Avatars.find('img').length, 1, "should have 1 avatar");
        assert.strictEqual($event1Avatars.find('span').length, 0,
            "should not have a span for more attendees since there is only one");

        var $event2Avatars = calendar.$('.fc-event:contains(All day) .o_calendar_avatars');
        assert.strictEqual($event2Avatars.find('img').length, 3, "should have 3 avatars");
        assert.strictEqual($event2Avatars.find('span').text(), '+2',
            "should indicate there are 2 more attendees that we don't show");
        calendar.destroy();
    });

    QUnit.test('open form view', function (assert) {
        assert.expect(3);

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
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return $.Deferred().resolve('A view');
                }
                return this._super(route, args);
            },
        });

        // click on an existing event to open the form view

        testUtils.intercept(calendar, 'do_action', function (event) {
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

        assert.strictEqual($('#ui-datepicker-div:empty').length, 0, "should have a clean body");
    });

    QUnit.test('create and edit event in month mode (all_day: false)', function (assert) {
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
                'mode="month" '+
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
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
                        "default_start": "2016-12-27 11:00:00", // 7:00 + 4h
                        "default_stop": "2016-12-27 23:00:00", // 19:00 + 4h
                    }
                },
                "should open the form view with the context default values");
        });

        $('.modal button.btn:contains(Edit)').trigger('click');

        calendar.destroy();
        assert.strictEqual($('#ui-datepicker-div:empty').length, 0, "should have a clean body");
    });

    QUnit.test('readonly date_start field', function (assert) {
        assert.expect(4);

        this.data.event.fields.start.readonly = true;

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
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return $.when(false);
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(calendar.$('.fc-resizer').length, 0, "should not have resize button");

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

        assert.strictEqual($('#ui-datepicker-div:empty').length, 0, "should have a clean body");
    });

    QUnit.test('"all" filter', function (assert) {
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
                'color="partner_id">'+
                    '<field name="name"/>'+
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

        assert.strictEqual(calendar.$('.fc-event').length, 9,
            "should display 9 events on the week");

        // Select the events only associated with partner 2
        calendar.$('.o_calendar_filter_item[data-id=2] input').click();
        assert.strictEqual(calendar.$('.fc-event').length, 4,
            "should display 4 events on the week");

        // Click on the 'all' filter to reload all events
        calendar.$('.o_calendar_filter_item[data-value=all] input').click();
        assert.strictEqual(calendar.$('.fc-event').length, 9,
            "should display 9 events on the week");

        calendar.destroy();
    });

    QUnit.test('create event with filters', function (assert) {
        assert.expect(7);

        this.data.event.fields.user_id.default = 5;
        this.data.event.fields.partner_id.default = 3;
        this.data.user.records.push({id: 5, display_name: "user 5", partner_id: 3});

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
                'color="partner_id">'+
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        calendar.$('.o_calendar_filter_item[data-value=4] input').click();

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 5, "should display 5 filter items");
        assert.strictEqual(calendar.$('.fc-event').length, 3, "should display 3 events");

        // quick create a record
        var left = calendar.$('.fc-bg td:eq(4)').offset().left+15;
        var top = calendar.$('.fc-slats tr:eq(4) td:first').offset().top+15;
        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        testUtils.triggerPositionalMouseEvent(left, top + 200, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top + 200, "mouseup");

        $('.modal-body input:first').val('coucou').trigger('input');
        $('.modal-footer button.btn:contains(Create)').trigger('click');

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 6, "should add the missing filter (active)");
        assert.strictEqual(calendar.$('.fc-event').length, 4, "should display the created item");

        // change default value for quick create an hide record
        this.data.event.fields.user_id.default = 4;
        this.data.event.fields.partner_id.default = 4;

        // quick create and other record
        left = calendar.$('.fc-bg td:eq(3)').offset().left+15;
        top = calendar.$('.fc-slats tr:eq(4) td:first').offset().top+15;
        testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        testUtils.triggerPositionalMouseEvent(left, top + 200, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top + 200, "mouseup");

        $('.modal-body input:first').val('coucou 2').trigger('input');
        $('.modal-footer button.btn:contains(Create)').trigger('click');

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 6, "should have the same filters");
        assert.strictEqual(calendar.$('.fc-event').length, 4, "should not display the created item");

        calendar.$('.o_calendar_filter_item[data-value=4] input').click();

        assert.strictEqual(calendar.$('.fc-event').length, 11, "should display all records");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('create event with filters (no quickCreate)', function (assert) {
        assert.expect(4);

        this.data.event.fields.user_id.default = 5;
        this.data.event.fields.partner_id.default = 3;
        this.data.user.records.push({
            id: 5,
            display_name: "user 5",
            partner_id: 3
        });

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
                'color="partner_id">'+
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
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
        });

        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body'); // => select with click position

        calendar.$('.o_calendar_filter_item[data-value=4] input').click();

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 5, "should display 5 filter items");
        assert.strictEqual(calendar.$('.fc-event').length, 3, "should display 3 events");

        // quick create a record
        var left = calendar.$('.fc-bg td:eq(4)').offset().left+15;
        var top = calendar.$('.fc-slats tr:eq(4) td:first').offset().top+15;
        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test fails to simulate a click in the screen. Your screen is probably too small or your dev tools is open.');
        }
        testUtils.triggerPositionalMouseEvent(left, top + 200, "mousemove");
        testUtils.triggerPositionalMouseEvent(left, top + 200, "mouseup");

        $('.modal-body input:first').val('coucou').trigger('input');

        $('.modal-footer button.btn:contains(Edit)').trigger('click');
        $('.modal-footer button.btn:contains(Save)').trigger('click');

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 6, "should add the missing filter (active)");
        assert.strictEqual(calendar.$('.fc-event').length, 4, "should display the created item");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('Update event with filters', function (assert) {
        assert.expect(4);

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
                'color="partner_id">'+
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
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

        calendar.$('.o_calendar_filter_item[data-value=4] input').click();

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 5, "should display 5 filter items");
        assert.strictEqual(calendar.$('.fc-event').length, 3, "should display 3 events");

        calendar.$('.fc-event:contains(event 2) .fc-content').trigger('click');
        $('.modal button.btn:contains(Edit)').trigger('click');
        $('.modal .o_field_widget[name="user_id"] input').trigger('click');
        $('.ui-menu-item a:contains(user 5)').trigger('mouseenter').trigger('click');
        $('.modal button.btn:contains(Save)').trigger('click');

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 6, "should add the missing filter (active)");
        assert.strictEqual(calendar.$('.fc-event').length, 3, "should display the updated item");

        calendar.destroy();
    });

    QUnit.test('change pager with filters', function (assert) {
        assert.expect(3);

        this.data.user.records.push({
            id: 5,
            display_name: "user 5",
            partner_id: 3
        });
        this.data.event.records.push({
            id: 7,
            user_id: 5,
            partner_id: 3,
            name: "event 7",
            start: "2016-12-06 04:00:00",
            stop: "2016-12-06 08:00:00",
            allday: false,
            partner_ids: [1,2,3],
            type: 1
        }, {
            id: 8,
            user_id: session.uid,
            partner_id: 1,
            name: "event 8",
            start: "2016-12-07 04:00:00",
            stop: "2016-12-07 08:00:00",
            allday: false,
            partner_ids: [1,2,3],
            type: 1
        },{
            id: 9,
            user_id: 4,
            partner_id: 4,
            name: "event 9",
            start: "2016-12-08 04:00:00",
            stop: "2016-12-08 08:00:00",
            allday: false,
            partner_ids: [1,2,3],
            type: 1
        });

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
                'color="partner_id">'+
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
        });

        calendar.$('.o_calendar_filter_item[data-value=4] input').click();
        $('.o_calendar_button_prev').click();

        assert.strictEqual(calendar.$('.o_calendar_filter_item').length, 6, "should display 6 filter items");
        assert.strictEqual(calendar.$('.fc-event').length, 2, "should display 2 events");
        assert.strictEqual(calendar.$('.fc-event .o_field_name').text().replace(/\s/g, ''), "event7event8",
            "should display 2 events");

        calendar.destroy();
    });

    QUnit.test('ensure events are still shown if filters give an empty domain', function (assert) {
        assert.expect(2);

        var calendar = createView({
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

        assert.strictEqual(calendar.$('.fc-event').length, 5,
            "should display 5 events");
        calendar.$('.o_calendar_filter_item[data-value=all] input[type=checkbox]').click();
        assert.strictEqual(calendar.$('.fc-event').length, 5,
            "should display 5 events");
        calendar.destroy();
    });

    QUnit.test('events starting at midnight', function (assert) {
        assert.expect(2);

        var calendar = createView({
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
        });

        // Click on Tuesday 12am
        var $view = $('#qunit-fixture').contents();
        $view.prependTo('body');
        var top = calendar.$('.fc-axis:contains(0:00)').offset().top + 5;
        var left = calendar.$('.fc-day:eq(2)').offset().left + 5;
        try {
            testUtils.triggerPositionalMouseEvent(left, top, "mousedown");
            testUtils.triggerPositionalMouseEvent(left, top, "mouseup");
        } catch (e) {
            calendar.destroy();
            $view.remove();
            throw new Error('The test failed to simulate a click on the screen.' +
                'Your screen is probably too small or your dev tools are open.');
        }
        assert.ok($('.modal-dialog.modal-sm').length,
            "should open the quick create dialog");

        // Creating the event
        $('.modal-body input:first').val('new event in quick create').trigger('input');
        $('.modal-footer button.btn:contains(Create)').trigger('click').trigger('click');
        assert.strictEqual(calendar.$('.fc-event:contains(new event in quick create)').length, 1,
            "should display the new record after quick create dialog");

        calendar.destroy();
        $view.remove();
    });

    QUnit.test('set event as all day when field is date', function (assert) {
        assert.expect(2);

        this.data.event.records[0].start_date = "2016-12-14";

        var calendar = createView({
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
                    '<field name="name"/>'+
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
        assert.strictEqual(calendar.$('.fc-day-grid .fc-event-container').length, 1,
            "should be one event in the all day row");
        assert.strictEqual(calendar.model.data.data[0].r_start.date(), 14,
            "the date should be 14");
        calendar.destroy();
    });

    QUnit.test('quickcreate avoid double event creation', function (assert) {
        assert.expect(1);
        var createCount = 0;
        var def = $.Deferred();
        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
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
            mockRPC: function (route, args) {
                var result = this._super(route, args);
                if (args.method === "create") {
                    createCount++;
                    return def.then(_.constant(result));
                }
                return result;
            },
        });

        // create a new event
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");
        var $input = $('.modal input:first');
        $input.val('new event in quick create').trigger('input');
        // Simulate ENTER pressed on Create button (after a TAB)
        $input.trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));
        $('.modal-footer button:first').click();
        def.resolve();
        assert.strictEqual(createCount, 1,
            "should create only one event");

        calendar.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', function (assert) {
        assert.expect(1);

        var instanceNumber = 0;
        testUtils.patch(mixins.ParentedMixin, {
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
                    '<field name="name"/>'+
                    '<filter name="user_id" avatar_field="image"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
            },
        };

        var calendar = createView(params);
        calendar.destroy();

        var initialInstanceNumber = instanceNumber;
        instanceNumber = 0;

        calendar = createView(params);

        // call destroy function of controller to ensure that it correctly destroys everything
        calendar.__destroy();

        assert.strictEqual(instanceNumber, initialInstanceNumber + 3, "every widget must be destroyed exept the parent");

        calendar.destroy();

        testUtils.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('create an event (async dialog) [REQUIRE FOCUS]', function (assert) {
        assert.expect(3);

        var def = $.Deferred();
        testUtils.patch(Dialog, {
            open: function () {
                var _super = this._super.bind(this);
                def.then(_super);
                return this;
            },
        });
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

        // create an event
        var $cell = calendar.$('.fc-day-grid .fc-row:eq(2) .fc-day:eq(2)');
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");

        assert.strictEqual($('.modal').length, 0,
            "should not have opened the dialog yet");

        def.resolve();

        assert.strictEqual($('.modal').length, 1,
            "should have opened the dialog");
        assert.strictEqual($('.modal input')[0], document.activeElement,
            "should focus the input in the dialog");

        calendar.destroy();
        testUtils.unpatch(Dialog);
    });

    QUnit.test('calendar is configured to hide the groupby menu', function (assert) {
        assert.expect(2);

        var archs = {
            'event,1,calendar': '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday"> '+
                    '<field name="name"/>'+
            '</calendar>',
            'event,false,search': '<search></search>',
        };

        var actions = [{
            id: 1,
            name: 'some action',
            res_model: 'event',
            type: 'ir.actions.act_window',
            views: [[1, 'calendar']]
        }];

        var actionManager = createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
        });

        actionManager.doAction(1);
        var $groupBy = actionManager.controlPanel.$('span.fa.fa-bars');
        assert.strictEqual($groupBy.length, 1, 'just making sure we have the groupby menu');
        assert.ok(!$groupBy.is(':visible'), 'groupby menu should not be visible');
        actionManager.destroy();
    });

    QUnit.test('timezone does not affect current day', function (assert) {
        assert.expect(2);

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar date_start="start_date">'+
                    '<field name="name"/>'+
            '</calendar>',
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
        $sidebar.find('.ui-datepicker-current-day').prev().click();

        assert.strictEqual($sidebar.find('.ui-datepicker-current-day').text(), "11", "should highlight the selected day");

        calendar.destroy();
    });

    QUnit.test('form_view_id attribute works (for creating events)', function (assert) {
        assert.expect(1);

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month" '+
                'form_view_id="42">'+
                    '<field name="name"/>'+
            '</calendar>',
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
                    return $.Deferred().reject('None shall pass!');
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
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");
        var $input = $('.modal-body input:first');
        $input.val("It's just a fleshwound").trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');

        calendar.destroy();
    });

    QUnit.test('calendar fallback to form view id in action if necessary', function (assert) {
        assert.expect(1);

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month"> '+
                    '<field name="name"/>'+
            '</calendar>',
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
                    return $.Deferred().reject('None shall pass!');
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
        testUtils.triggerMouseEvent($cell, "mousedown");
        testUtils.triggerMouseEvent($cell, "mouseup");
        var $input = $('.modal-body input:first');
        $input.val("It's just a fleshwound").trigger('input');
        $('.modal button.btn:contains(Create)').trigger('click');

        calendar.destroy();
    });

    QUnit.test('fullcalendar initializes with right locale', function (assert) {
        assert.expect(1);

        var initialLocale = moment.locale();
        // This will set the locale to zz
        moment.defineLocale('zz', {
            longDateFormat: {
                L: 'DD/MM/YYYY'
            },
            weekdaysShort: ["zz1.", "zz2.", "zz3.", "zz4.", "zz5.", "zz6.", "zz7."],
        });

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch: '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="week"> '+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            viewOptions: {
                initialDate: initialDate,
                action: {views: [{viewID: 1, type: 'kanban'}, {viewID: 43, type: 'form'}]}
            },

        });

        assert.strictEqual(calendar.$('.fc-day-header:first').text(), "zz1. 11/12",
            'The day should be in the given locale specific format');

        moment.locale(initialLocale);

        calendar.destroy();
    });

});

});
