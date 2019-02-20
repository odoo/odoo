odoo.define('note.systray.ActivityMenuTests', function (require) {
"use strict";

var ActivityMenu = require('mail.systray.ActivityMenu');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

QUnit.module('note', {}, function () {

QUnit.module("ActivityMenu", {
    beforeEach: function () {
        this.services = mailTestUtils.getMailServices();
        this.data = {
            'mail.activity.menu': {
                fields: {
                    name: { type: "char" },
                    model: { type: "char" },
                    type: { type: "char" },
                    planned_count: { type: "integer"},
                    today_count: { type: "integer"},
                    overdue_count: { type: "integer"},
                    total_count: { type: "integer"}
                },
                records: [],
            },
            'note.note': {
                fields: {
                    memo: { type: 'char' },
                },
                records: [],
            }
        };
    }
});

QUnit.test('note activity menu widget: create note from activity menu', function (assert) {
    assert.expect(15);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return $.when(self.data['mail.activity.menu'].records);
            }
            if (route === '/note/new') {
                if (args.date_deadline) {
                    var note = {
                        id: 1,
                        memo: args.note,
                        date_deadline: args.date_deadline
                    };
                    self.data['note.note'].records.push(note);
                    if (_.isEmpty(self.data['mail.activity.menu'].records)) {
                        self.data['mail.activity.menu'].records.push({
                            name: "Note",
                            model: "note.note",
                            type: "activity",
                            planned_count: 0,
                            today_count: 0,
                            overdue_count: 0,
                            total_count: 0,
                        });
                    }
                    self.data['mail.activity.menu'].records[0].today_count++;
                    self.data['mail.activity.menu'].records[0].total_count++;
                }
                return $.when();
            }
            return this._super(route, args);
        },
    });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$el.hasClass('o_mail_systray_item'),
        'should be the instance of widget');
    assert.strictEqual(activityMenu.$('.o_notification_counter').text(), '0',
        "should not have any activity notification initially");

    // toggle quick create for note
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$('.o_no_activity').length, 1,
        "should not have any activity preview");
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), false,
        'ActivityMenu should have Add new note CTA');
    activityMenu.$('.o_note_show').click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), true,
        'ActivityMenu should hide CTA when entering a new note');
    assert.strictEqual(activityMenu.$('.o_note').hasClass('d-none'), false,
        'ActivityMenu should display input for new note');

    // creating quick note without date
    activityMenu.$("input.o_note_input").val("New Note");
    activityMenu.$(".o_note_save").click();
    assert.strictEqual(activityMenu.$('.o_notification_counter').text(), '1',
        "should increment activity notification counter after creating a note");
    assert.strictEqual(activityMenu.$('.o_mail_preview[data-res_model="note.note"]').length, 1,
        "should have an activity preview that is a note");
    assert.strictEqual(activityMenu.$('.o_activity_filter_button[data-filter="today"]').text().trim(),
        "1 Today",
        "should display one note for today");

    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), false,
        'ActivityMenu add note button should be displayed');
    assert.strictEqual(activityMenu.$('.o_note').hasClass('d-none'), true,
        'ActivityMenu add note input should be hidden');

    // creating quick note with date
    activityMenu.$('.o_note_show').click();
    activityMenu.$('input.o_note_input').val("New Note");
    activityMenu.$(".o_note_save").click();
    assert.strictEqual(activityMenu.$('.o_notification_counter').text(), '2',
        "should increment activity notification counter after creating a second note");
    assert.strictEqual(activityMenu.$('.o_activity_filter_button[data-filter="today"]').text().trim(),
        "2 Today",
        "should display 2 notes for today");
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), false,
        'ActivityMenu add note button should be displayed');
    assert.strictEqual(activityMenu.$('.o_note').hasClass('d-none'), true,
        'ActivityMenu add note input should be hidden');
    activityMenu.destroy();
});
});
});
