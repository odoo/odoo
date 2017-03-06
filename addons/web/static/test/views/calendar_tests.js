odoo.define('web.calendar_tests', function (require) {
"use strict";

var CalendarView = require('web.CalendarView');
var testUtils = require('web.test_utils');
var session = require('web.session');

var createView = testUtils.createView;

var initialDate = new Date("2016-12-12T08:00:00Z");


function mock_check_access_rights(route, args) {
    if (args.method === "check_access_rights") {
        if (!args.model) throw new Error('"model" is undefined to call "check_access_rights"');
        return $.when(true);
    }
    return this._super(route, args);
}

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
                    start: {string: "start", type: "datetime"},
                    stop: {string: "stop", type: "datetime"},
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
                ]
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
        "event,false,form": {
            attrs: {},
            children: [
                {
                    attrs: {name: "name"},
                    children: [],
                    tag: 'field'
                },
                {
                    attrs: {name: "allday"},
                    children: [],
                    tag: 'field'
                },
                {
                    attrs: {name: "start"},
                    children: [],
                    tag: 'field'
                },
                {
                    attrs: {name: "stop"},
                    children: [],
                    tag: 'field'
                }
            ],
            tag: "form"
        },
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
                'scale_zoom="week" '+
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
            mockRPC: mock_check_access_rights,
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
        assert.ok($attendeesFilter.find('.o_form_field_many2one').length, "should display one2many search bar for 'attendees' filter");

        // test search bar in filter

        $sidebar.find('input.o_form_input').trigger('click');
        assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').length, 2, "should display 2 choices in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
        $('ul.ui-autocomplete li:first').trigger('click');
        assert.strictEqual($sidebar.find('.o_calendar_filter:has(h3:contains(attendees)) .o_calendar_filter_item').length, 4, "should display 4 filter items for 'attendees'");
        $sidebar.find('input.o_form_input').trigger('click');
        assert.strictEqual($('ul.ui-autocomplete li:not(.o_m2o_dropdown_option)').text(), "partner 4", "should display the last choice in one2many autocomplete"); // TODO: remove :not(.o_m2o_dropdown_option) because can't have "create & edit" choice
        $sidebar.find('.o_calendar_filter_item[data-id="1"] .o_remove').trigger('click');
        assert.ok($('.modal button.btn:contains(Ok)').length, "should display the confirm message");
        $('.modal button.btn:contains(Ok)').trigger('click');
        assert.strictEqual($sidebar.find('.o_calendar_filter:has(h3:contains(attendees)) .o_calendar_filter_item').length, 3, "click on remove then should display 3 filter items for 'attendees'");
        calendar.destroy();
    });

    QUnit.test('create and change events', function (assert) {
        assert.expect(19);

        var calendar = createView({
            View: CalendarView,
            model: 'event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'scale_zoom="week" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'all_day="allday" '+
                'mode="month" '+
                'readonly_form_view_id="1">'+
                    '<field name="name"/>'+
            '</calendar>',
            archs: archs,
            mockRPC: mock_check_access_rights,
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
        $('.modal button.btn:contains(Create)').trigger('click');

        assert.ok(calendar.$('.fc-event:contains(new event in quick create)').length, "should display the new record");
        assert.strictEqual(calendar.$('td.fc-event-container[colspan]').length, 2, "should the new record have only one day");

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

        assert.strictEqual(calendar.$('.fc-event-container .fc-event').length, 8, "should display 8 events");
        // move to next month
        calendar.$buttons.find('.o_calendar_button_next').click();

        assert.strictEqual(calendar.$('.fc-event-container .fc-event').length, 0, "should display 0 events");
        calendar.destroy();
    });

});

});
