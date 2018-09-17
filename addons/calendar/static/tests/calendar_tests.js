odoo.define('calendar.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require("web.test_utils");

var createView = testUtils.createView;

QUnit.module('calendar', {
    beforeEach: function () {
        this.data = {
            event: {
                fields: {
                    partner_ids: {string: "Partners", type: "many2many", relation: "partner"},
                },
                records: [{
                    id: 14,
                    partner_ids: [1, 2],
                }],
            },
            partner: {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [{
                    id: 1,
                    name: "Jesus",
                }, {
                    id: 2,
                    name: "Mahomet",
                }],
            },
        };
    },
}, function () {
    QUnit.test("many2manyattendee widget: basic rendering", function (assert) {
        assert.expect(9);

        var form = createView({
            View: FormView,
            model: 'event',
            data: this.data,
            res_id: 14,
            arch:
                '<form>' +
                    '<field name="partner_ids" widget="many2manyattendee"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'get_attendee_detail') {
                    assert.strictEqual(args.model, 'res.partner',
                        "the method should only be called on res.partner");
                    assert.deepEqual(args.args[0], [1, 2],
                        "the partner ids should be passed as argument");
                    assert.strictEqual(args.args[1], 14,
                        "the event id should be passed as argument");
                    return $.when([
                        [1, "Jesus", "accepted", 0],
                        [2, "Mahomet", "needsAction", 0],
                    ]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(form.$('.o_field_widget[name="partner_ids"]').hasClass('o_field_many2manytags'));
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge').length, 2,
            "there should be 2 tags");
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge:first').text().trim(), "Jesus",
            "the tag should be correctly named");
        assert.ok(form.$('.o_field_widget[name="partner_ids"] .badge:first .o_calendar_invitation').hasClass('accepted'),
            "Jesus should attend the meeting");
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge[data-id="2"]').text().trim(), "Mahomet",
            "the tag should be correctly named");
        assert.ok(form.$('.o_field_widget[name="partner_ids"] .badge[data-id="2"] .o_calendar_invitation').hasClass('needsAction'),
            "Mohamet should still confirm his attendance to the meeting");

        form.destroy();
    });
});
});
