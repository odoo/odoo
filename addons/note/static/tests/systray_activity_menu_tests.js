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
                records: [],
            },
        };
    }
});

QUnit.test('note activity menu widget: create note from activity menu', function (assert) {
    assert.expect(8);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return $.when(self.data['mail.activity.menu']['records']);
            }
            if (route === '/note/new') {
                return $.when();
            }
            return this._super(route, args);
        },
    });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$el.hasClass('o_mail_systray_item'), 'should be the instance of widget');

    // toggle quick create for note
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), false, 'ActivityMenu should have Add new note CTA');
    activityMenu.$('.o_note_show').click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), true, 'ActivityMenu should hide CTA when entering a new note');
    assert.strictEqual(activityMenu.$('.o_note').hasClass('d-none'), false, 'ActivityMenu should display input for new note');

    // creating quick note without date
    activityMenu.$("input.o_note_input").val("New Note");
    activityMenu.$(".o_note_save").click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), false, 'ActivityMenu add note button should be displayed');
    assert.strictEqual(activityMenu.$('.o_note').hasClass('d-none'), true, 'ActivityMenu add note input should be hidden');

    // creating quick note with date
    activityMenu.$('.o_note_show').click();
    activityMenu.$('input.o_note_input').val("New Note");
    activityMenu.$('.o_note_set_datetime').click();
    activityMenu.$(".o_note_save").click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass('d-none'), false, 'ActivityMenu add note button should be displayed');
    assert.strictEqual(activityMenu.$('.o_note').hasClass('d-none'), true, 'ActivityMenu add note input should be hidden');
    activityMenu.destroy();
});
});
});
