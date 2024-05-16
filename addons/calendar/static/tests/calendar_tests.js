/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;
const uid = -1;

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
                '.o_field_widget[name="partner_ids"] .badge',
                2,
                "there should be 2 tags"
            );
            const badges = target.querySelectorAll('.o_field_widget[name="partner_ids"] .badge');
            assert.strictEqual(
                badges[0].textContent.trim(),
                "Jesus",
                "the tag should be correctly named"
            );
            assert.hasClass(
                badges[0].querySelector("img"),
                "o_attendee_border_accepted",
                "Jesus should attend the meeting"
            );
            assert.strictEqual(
                badges[1].textContent.trim(),
                "Mahomet",
                "the tag should be correctly named"
            );
            assert.hasClass(
                badges[1].querySelector("img"),
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

        QUnit.debug("Land on the same date when going back", async function(assert) {
            assert.expect(0);
            serverData = {
                models: {
                    'calendar.event': {
                        fields: {
                            id: {string: "ID", type: "integer"},
                            user_id: {string: "user", type: "many2one", relation: 'user'},
                            partner_id: {string: "user", type: "many2one", relation: 'partner', related: 'user_id.partner_id'},
                            name: {string: "name", type: "char"},
                            start_date: {string: "start date", type: "date"},
                            stop_date: {string: "stop date", type: "date"},
                            start: {string: "start datetime", type: "datetime"},
                            stop: {string: "stop datetime", type: "datetime"},
                            allday: {string: "allday", type: "boolean"},
                            partner_ids: {string: "attendees", type: "one2many", relation: 'partner'},
                            type: {string: "type", type: "integer"},
                        },
                        records: [
                            {id: 5, user_id: uid, partner_id: 4, name: "event 1", start: "2016-12-13 15:55:05", stop: "2016-12-15 18:55:05", allday: false, partner_ids: [4], type: 2},
                            {id: 6, user_id: uid, partner_id: 5, name: "event 2", start: "2016-12-18 08:00:00", stop: "2016-12-18 09:00:00", allday: false, partner_ids: [4], type: 3}
                        ],
                        check_access_rights: function () {
                            return Promise.resolve(true);
                        }
                    },
                    'appointment.type': {
                        fields: {},
                        records: [],
                    },
                    user: {
                        fields: {
                            id: {string: "ID", type: "integer"},
                            display_name: {string: "Displayed name", type: "char"},
                            partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                            image_1920: {string: "image", type: "integer"},
                        },
                        records: [
                            {id: 4, display_name: "user 4", partner_id: 4},
                        ]
                    },
                    partner: {
                        fields: {
                            id: {string: "ID", type: "integer"},
                            display_name: {string: "Displayed name", type: "char"},
                            image_1920: {string: "image", type: "integer"},
                        },
                        records: [
                            {id: 4, display_name: "partner 4", image_1920: 'DDD'},
                            {id: 5, display_name: "partner 5", image_1920: 'DDD'},
                        ]
                    },
                    filter_partner: {
                        fields: {
                            id: {string: "ID", type: "integer"},
                            user_id: {string: "user", type: "many2one", relation: 'user'},
                            partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                            partner_checked: {string: "checked", type: "boolean"},
                        },
                        records: [
                            {id: 3, user_id: uid, partner_id: 4, partner_checked: true}
                        ]
                    },
                },
                views: {
                    "calendar.event,false,form": `
                        <form>
                            <field name="name" />
                            <field name="allday" />
                            <group attrs="{'invisible': [['allday', '=', True]]}">
                                <field name="start" />
                                <field name="stop" />
                            </group>
                            <group attrs="{'invisible': [['allday', '=', False]]}">
                                <field name="start_date" />
                                <field name="stop_date" />
                            </group>
                        </form>
                    `,
                },
            };

            await makeView({
                type: "calendar",
                resModel: 'calendar.event',
                serverData,
                arch:
                '<calendar class="o_calendar_test" '+
                    'js_class="attendee_calendar" '+
                    'date_start="start" '+
                    'date_stop="stop" '+
                    'attendee="partner_ids">'+
                        '<field name="name"/>'+
                        '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
                '</calendar>',
                mockRPC: async function (route, args, method) {
                    console.log("ROUTE: ", route);
                    console.log("ARGS: ", args);
                    console.log("METHOD: ", method);
                    console.log(route === "/web/dataset/call_kw/calendar.event/get_views")
                    if(args.kwargs && args.kwargs.views){
                        console.log("HERE: ", args.kwargs.views[0]);
                    }
                    if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                        return Promise.resolve([]);
                    } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                        return Promise.resolve(true);
                    } 
                    else if (route === "/web/dataset/call_kw/calendar.event/get_views" && args.kwargs && args.kwargs.views && args.kwargs.views[0][1] === "form"){
                        
                        await makeView({
                            type: "calendar",
                            resModel: "calendar.event",
                            serverData,
                            arch: `
                                <form>
                                    <field name="name" />
                                    <field name="allday" />
                                    <group attrs="{'invisible': [['allday', '=', True]]}">
                                        <field name="start" />
                                        <field name="stop" />
                                    </group>
                                    <group attrs="{'invisible': [['allday', '=', False]]}">
                                        <field name="start_date" />
                                        <field name="stop_date" />
                                    </group>
                                </form>
                            `
                        })
                        // return Promise.resolve({
                        //     "result": {
                        //         "views": {
                        //             "form": `
                        //                 <form>
                        //                     <group>
                        //                         <field name="name" />
                        //                         <field name="start" />
                        //                         <field name="stop" />
                        //                         <field name="user_id" />
                        //                     </group>
                        //                 </form>
                        //             `,
                        //             "search": `<search />`,
                        //         }
                        //     }
                        // })
                    }
                },
            });

        })
    }
);
