/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';
import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

import testUtils from 'web.test_utils';

QUnit.module('note', {}, function () {
QUnit.module("ActivityMenu", {
    beforeEach() {
        beforeEach(this);

        Object.assign(this.data, {
            'mail.activity.menu': {
                fields: {
                    name: { type: "char" },
                    model: { type: "char" },
                    type: { type: "char" },
                    planned_count: { type: "integer" },
                    today_count: { type: "integer" },
                    overdue_count: { type: "integer" },
                    total_count: { type: "integer" }
                },
                records: [],
            },
            'note.note': {
                fields: {
                    memo: { type: 'char' },
                },
                records: [],
            }
        });
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('note activity menu widget: create note from activity menu', async function (assert) {
    assert.expect(15);
    var self = this;

    const { widget } = await start({
        data: this.data,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return Promise.resolve(self.data['mail.activity.menu'].records);
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
                return Promise.resolve();
            }
            return this._super(route, args);
        },
    });

    const activityMenu = new ActivityMenu(widget);
    await activityMenu.appendTo($('#qunit-fixture'));
    assert.hasClass(activityMenu.$el, 'o_mail_systray_item',
        'should be the instance of widget');
    assert.strictEqual(activityMenu.$('.o_notification_counter').text(), '0',
        "should not have any activity notification initially");

    // toggle quick create for note
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    assert.containsOnce(activityMenu, '.o_no_activity',
        "should not have any activity preview");
    assert.doesNotHaveClass(activityMenu.$('.o_note_show'), 'd-none',
        'ActivityMenu should have Add new note CTA');
    await testUtils.dom.click(activityMenu.$('.o_note_show'));
    assert.hasClass(activityMenu.$('.o_note_show'), 'd-none',
        'ActivityMenu should hide CTA when entering a new note');
    assert.doesNotHaveClass(activityMenu.$('.o_note'), 'd-none',
        'ActivityMenu should display input for new note');

    // creating quick note without date
    await testUtils.fields.editInput(activityMenu.$("input.o_note_input"), "New Note");
    await testUtils.dom.click(activityMenu.$(".o_note_save"));
    assert.strictEqual(activityMenu.$('.o_notification_counter').text(), '1',
        "should increment activity notification counter after creating a note");
    assert.containsOnce(activityMenu, '.o_mail_preview[data-res_model="note.note"]',
        "should have an activity preview that is a note");
    assert.strictEqual(activityMenu.$('.o_activity_filter_button[data-filter="today"]').text().trim(),
        "1 Today",
        "should display one note for today");

    assert.doesNotHaveClass(activityMenu.$('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.hasClass(activityMenu.$('.o_note'), 'd-none',
        'ActivityMenu add note input should be hidden');

    // creating quick note with date
    await testUtils.dom.click(activityMenu.$('.o_note_show'));
    activityMenu.$('input.o_note_input').val("New Note");
    await testUtils.dom.click(activityMenu.$(".o_note_save"));
    assert.strictEqual(activityMenu.$('.o_notification_counter').text(), '2',
        "should increment activity notification counter after creating a second note");
    assert.strictEqual(activityMenu.$('.o_activity_filter_button[data-filter="today"]').text().trim(),
        "2 Today",
        "should display 2 notes for today");
    assert.doesNotHaveClass(activityMenu.$('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.hasClass(activityMenu.$('.o_note'), 'd-none',
        'ActivityMenu add note input should be hidden');
    widget.destroy();
});
});
