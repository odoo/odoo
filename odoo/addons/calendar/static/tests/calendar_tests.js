/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module(
    "calendar",
    {
        beforeEach: function () {
            target = getFixture();
            serverData = {
                models: {
                    event: {
                        fields: {
                            partner_ids: {
                                string: "Partners",
                                type: "many2many",
                                relation: "partner",
                            },
                        },
                        records: [
                            {
                                id: 14,
                                partner_ids: [1, 2],
                            },
                        ],
                    },
                    partner: {
                        fields: {
                            name: { string: "Name", type: "char" },
                        },
                        records: [
                            {
                                id: 1,
                                name: "Jesus",
                            },
                            {
                                id: 2,
                                name: "Mahomet",
                            },
                        ],
                    },
                },
            };
            setupViewRegistries();
        },
    },
    function () {
        QUnit.test("Many2ManyAttendee: basic rendering", async function (assert) {
            await makeView({
                type: "form",
                resModel: "event",
                serverData,
                resId: 14,
                arch: `
                    <form>
                        <field name="partner_ids" widget="many2manyattendee"/>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "get_attendee_detail") {
                        assert.step(args.method);
                        assert.strictEqual(
                            args.model,
                            "res.partner",
                            "the method should only be called on res.partner"
                        );
                        assert.deepEqual(
                            args.args[0],
                            [1, 2],
                            "the partner ids should be passed as argument"
                        );
                        assert.deepEqual(
                            args.args[1],
                            [14],
                            "the event id should be passed as argument"
                        );
                        return Promise.resolve([
                            { id: 1, name: "Jesus", status: "accepted", color: 0 },
                            { id: 2, name: "Mahomet", status: "tentative", color: 0 },
                        ]);
                    }
                },
            });

            assert.hasClass(
                target.querySelector('.o_field_widget[name="partner_ids"] div'),
                "o_field_tags"
            );
            assert.containsN(
                target,
                '.o_field_widget[name="partner_ids"] .o_tag',
                2,
                "there should be 2 tags"
            );
            const badges = target.querySelectorAll('.o_field_widget[name="partner_ids"] .o_tag');
            assert.strictEqual(
                badges[0].textContent.trim(),
                "Jesus",
                "the tag should be correctly named"
            );
            assert.hasClass(
                badges[0].querySelector(".attendee_tag_status"),
                "o_attendee_status_accepted",
                "Jesus should attend the meeting"
            );
            assert.strictEqual(
                badges[1].textContent.trim(),
                "Mahomet",
                "the tag should be correctly named"
            );
            assert.hasClass(
                badges[1].querySelector(".attendee_tag_status"),
                "o_attendee_status_tentative",
                "Mohamet should still confirm his attendance to the meeting"
            );
            assert.containsOnce(badges[0], "img", "should have img tag");
            assert.hasAttrValue(
                badges[0].querySelector("img"),
                "data-src",
                "/web/image/partner/1/avatar_128",
                "should have correct avatar image"
            );
            assert.verifySteps(["get_attendee_detail"]);
        });
        QUnit.test("Many2ManyAttendee: remove own attendee", async function (assert) {
            await makeView({
                type: "form",
                resModel: "event",
                serverData,
                resId: 14,
                arch: `
                    <form>
                        <field name="partner_ids" widget="many2manyattendee"/>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "get_attendee_detail") {
                        return Promise.resolve([
                            { id: 1, name: "Jesus", status: "accepted", color: 0 },
                            { id: 2, name: "Mahomet", status: "tentative", color: 0 },
                        ]);
                    }
                },
            });
            assert.containsN(
                target,
                '.o_field_widget[name="partner_ids"] .o_tag',
                2,
                "there should be 2 tags"
            );

            // Attendee must be able to uninvite itself from the event.
            const deleteButtons = target.querySelectorAll('.o_field_widget[name="partner_ids"] .o_delete');
            await Promise.all([
                click(deleteButtons[1]),
                click(target.querySelector(".o_form_button_save")),
            ])
            // Ensure that there is only one attendee after removing it and saving the event.
            assert.containsN(
                target,
                '.o_field_widget[name="partner_ids"] .o_tag',
                1,
                "there should be 1 tag after attendee removal"
            );
        });
    },
);
