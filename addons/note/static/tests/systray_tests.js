odoo.define('note.systray_tests', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');
var systray = require('mail.systray');
var testUtils = require('web.test_utils');
var createBusService = require('mail.testUtils').createBusService;

QUnit.module('note', {}, function () {

QUnit.module("ActivityMenu", {
    beforeEach: function () {
        this.services = [ChatManager, createBusService()];
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
    var activityMenu = new systray.ActivityMenu();
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
    assert.ok(activityMenu.$el.hasClass('o_mail_navbar_item'), 'should be the instance of widget');

    // toggle quick create for note
    var step = 1;
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass("hidden"), false, 'ActivityMenu should have Add new note CTA');
    activityMenu.$('.o_note_show').click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass("hidden"), true, 'ActivityMenu should hide CTA when entering a new note');
    assert.strictEqual(activityMenu.$('.o_note').hasClass("hidden"), false, 'ActivityMenu should display input for new note');

    // creating quick note without date
    activityMenu.$("input.o_note_input").val("New Note");
    activityMenu.$(".o_note_save").click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass("hidden"), false, 'ActivityMenu add note button should be displayed');
    assert.strictEqual(activityMenu.$('.o_note').hasClass("hidden"), true, 'ActivityMenu add note input should be hidden');

    // creating quick note with date
    step = 2;
    activityMenu.$('.o_note_show').click();
    activityMenu.$('input.o_note_input').val("New Note");
    activityMenu.$('.o_note_set_datetime').click();
    activityMenu.$(".o_note_save").click();
    assert.strictEqual(activityMenu.$('.o_note_show').hasClass("hidden"), false, 'ActivityMenu add note button should be displayed');
    assert.strictEqual(activityMenu.$('.o_note').hasClass("hidden"), true, 'ActivityMenu add note input should be hidden');
    activityMenu.destroy();
});
});
});
