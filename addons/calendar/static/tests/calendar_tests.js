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
    QUnit.test("many2manyattendee widget: basic rendering", async function (assert) {
        assert.expect(12);

        var form = await createView({
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
                    return Promise.resolve([
                        [1, "Jesus", "accepted", 0],
                        [2, "Mahomet", "tentative", 0],
                    ]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.hasClass(form.$('.o_field_widget[name="partner_ids"]'), 'o_field_many2manytags');
        assert.containsN(form, '.o_field_widget[name="partner_ids"] .badge', 2,
            "there should be 2 tags");
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge:first').text().trim(), "Jesus",
            "the tag should be correctly named");
        assert.hasClass(form.$('.o_field_widget[name="partner_ids"] .badge:first .o_calendar_invitation'),'accepted',
            "Jesus should attend the meeting");
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge[data-id="2"]').text().trim(), "Mahomet",
            "the tag should be correctly named");
        assert.hasClass(form.el.querySelector('.o_field_widget[name="partner_ids"] .badge[data-id="2"] .o_calendar_invitation'), 'tentative',
            "Mohamet should still confirm his attendance to the meeting");
        assert.hasClass(form.el.querySelector('.o_field_many2manytags'), 'avatar',
            "should have avatar class");
        assert.containsOnce(form, '.o_field_many2manytags.avatar.o_field_widget .badge:first img',
            "should have img tag");
        assert.hasAttrValue(form.$('.o_field_many2manytags.avatar.o_field_widget .badge:first img'),
            'data-src',
            '/web/image/partner/1/image_128',
            "should have correct avatar image");

        form.destroy();
    });
});
});
