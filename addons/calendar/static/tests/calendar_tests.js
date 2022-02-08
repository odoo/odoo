/** @odoo-module **/

import FormView from 'web.FormView';
import testUtils from "web.test_utils";

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
                    assert.deepEqual(args.args[1], [14],
                        "the event id should be passed as argument");
                    return Promise.resolve([
                        {id: 1, name: "Jesus", status: "accepted", color: 0},
                        {id: 2, name: "Mahomet", status: "tentative", color: 0},
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
        assert.hasClass(form.$('.o_field_widget[name="partner_ids"] .badge:first img'),'o_attendee_border_accepted',
            "Jesus should attend the meeting");
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] .badge[data-id="2"]').text().trim(), "Mahomet",
            "the tag should be correctly named");
        assert.hasClass(form.el.querySelector('.o_field_widget[name="partner_ids"] .badge[data-id="2"] img'), 'o_attendee_border_tentative',
            "Mohamet should still confirm his attendance to the meeting");
        assert.hasClass(form.el.querySelector('.o_field_many2manytags'), 'avatar',
            "should have avatar class");
        assert.containsOnce(form, '.o_field_many2manytags.avatar.o_field_widget .badge:first img',
            "should have img tag");
        assert.hasAttrValue(form.$('.o_field_many2manytags.avatar.o_field_widget .badge:first img'),
            'data-src',
            '/web/image/partner/1/avatar_128',
            "should have correct avatar image");

        form.destroy();
    });

    QUnit.test('many2manyattendee widget: long event rendering', async function (assert) {
        assert.expect(13);
        const longEventData = {
            event: {
                fields: {
                    partner_ids: {string: "Partners", type: "many2many", relation: "partner"},
                },
                records: [{
                    id: 14,
                    partner_ids: [1, 2, 3, 4, 5, 6, 7, 8],
                }],
            },
            partner: {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: Array(8).fill(0).map((_, index) => {
                    return {
                        id: index + 1,
                        name: `Test user ${index + 1}`
                    }
                })
            },
        };
        const form = await createView({
            View: FormView,
            model: 'event',
            data: longEventData,
            res_id: 14,
            arch:
                `<form>
                    <field name="partner_ids" widget="many2manyattendee" options="{'isPopover': True}"/>
                </form>`,
            mockRPC: function (route, args) {
                if (args.method === 'get_attendee_detail') {
                    return Promise.resolve(
                        longEventData.partner.records.map(item => {
                            return {
                                id: item.id,
                                name: item.name,
                                status: 'accepted',
                                color: 0
                            }
                        })
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        const expandButton = form.$("div.show.multicollapse a[type='button']");
        const collapseButton = form.$("div.multicollapse:not(.show) a[type='button']")
        assert.containsN(form, '.o_field_widget[name="partner_ids"] .badge:not(.collapse)', 5,
            "there should be 5 shown badges");
        assert.containsN(form, '.o_field_widget[name="partner_ids"] .badge', 8, "there should be 8 badges in total");
        assert.strictEqual(expandButton.text().trim(), "8 attendees");
        assert.strictEqual(expandButton.parent().find('i').text().trim(), '8 accepted');
        assert.strictEqual(collapseButton.text().trim(), "8 attendees");
        form.$('.o_field_widget[name="partner_ids"] .badge').each((index, element) => {
            assert.strictEqual($(element).text().trim(), longEventData.partner.records[index].name)
        })
    });
});
