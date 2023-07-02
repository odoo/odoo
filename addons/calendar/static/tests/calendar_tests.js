/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { makeFakeDialogService } from '@web/../tests/helpers/mock_services';
import { clickAllDaySlot, FAKE_FILTER_SECTIONS } from "@web/../tests/views/calendar/helpers";

const serviceRegistry = registry.category("services");
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
                            name: {
                                string: "Name",
                                type: "char",
                            },
                            start: {
                                string: "date",
                                type: "date",
                                readonly: true
                            },
                        },
                        records: [
                            {
                                id: 14,
                                partner_ids: [1, 2],
                                name: "Event Mock",
                            },
                        ],
                        methods: {
                            check_access_rights() {
                                return Promise.resolve(true);
                            },
                        },
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
                views: {
                    "event,1,form": `
                        <form>
                            <h1>My custom form view for quick create</h1>
                            <field name="name"/>
                        </form>
                    `
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
                badges[0].querySelector('img'),
                "o_attendee_border_accepted",
                "Jesus should attend the meeting"
            );
            assert.strictEqual(
                badges[1].textContent.trim(),
                "Mahomet",
                "the tag should be correctly named"
            );
            assert.hasClass(
                badges[1].querySelector('img'),
                "o_attendee_border_tentative",
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

        /**
         *  Currently JS tests are run after all addons are installed. This test fails due to a patch made in appointment
         *  and to prevent mocking things from an external module in this test, we decided to skip it until the test
         *  strategy is changed.
         * */
        QUnit.skip("Calendar quick create form view id is correctly being rendered", async (assert) => {
            assert.expect(1);
            serviceRegistry.add('dialog', makeFakeDialogService((className, props) => {
                assert.equal(props.viewId, 1);
                return () => {};
            }), { force: true });

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar js_class="attendee_calendar" date_start="start" date_stop="stop" all_day="allday"
                        date_delay="duration"
                        scales="month" quick_add="0" quick_create_form_view_id="1" color="partner_ids">
                        <field name="name"/>
                        <field name="partner_ids" color="partner_ids" filters="1"/>
                    </calendar>
                `,
                mockRPC(route, args) {
                    if (args.method === "get_attendee_detail") {
                        return Promise.resolve([
                            { id: 1, name: "Jesus", status: "accepted", color: 0 },
                            { id: 2, name: "Mahomet", status: "tentative", color: 0 },
                        ]);
                    }
                    if(route === '/web/dataset/call_kw/calendar.filters/search_read') {
                        return Promise.resolve(FAKE_FILTER_SECTIONS);
                    }
                }
            });
            const date = target.querySelector(".fc-day-grid td");
            await clickAllDaySlot(target, date.dataset.date);
            const datepicker = document.querySelector("#ui-datepicker-div");
            if (datepicker) {
                datepicker.remove();
            }
        });
    }
);
