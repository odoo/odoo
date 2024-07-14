/** @odoo-module **/

import { click, getFixture, patchDate, patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
const { DateTime } = luxon;
let target;

QUnit.module("Planning.planning_calendar_tests", ({ beforeEach }) => {
    beforeEach(() => {
        patchDate(2021, 5, 22, 8, 0, 0);
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("planning calendar view: copy previous week", async function (assert) {
        assert.expect(6);
        const serverData = {
            models: {
                "planning.slot": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Note", type: "text" },
                        color: { string: "Color", type: "integer" },
                        display_name: { string: "Name", type: "char" },
                        start: { string: "Start Date", type: "datetime" },
                        stop: { string: "Stop Date", type: "datetime" },
                        resource_id: { string: "Assigned to", type: "many2one", relation: "resource.resource" },
                        role_id: { string: "Role", type: "many2one", relation: "role" },
                        state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["draft", "Draft"],
                                ["published", "Published"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            name: "First Record",
                            start: DateTime.now().toFormat("yyyy-MM-dd HH':00:00'"),
                            stop: DateTime.now().plus({hours:4}).toFormat("yyyy-MM-dd HH':00:00'"),
                            resource_id: 1,
                            color: 7,
                            role_id: 1,
                            state: "draft",
                        },
                        {
                            id: 2,
                            name: "Second Record",
                            start: DateTime.now().plus({days:2}).toFormat("yyyy-MM-dd HH':00:00'"),
                            stop: DateTime.now().plus({hours:4, days:2}).toFormat("yyyy-MM-dd HH':00:00'"),
                            resource_id: 2,
                            color: 9,
                            role_id: 2,
                            state: "published",
                        },
                    ],
                    methods: {
                        check_access_rights: () => Promise.resolve(true),
                    },
                },
                "resource.resource": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Chaganlal" },
                        { id: 2, name: "Maganlal" },
                    ],
                },
                role: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        color: { string: "Color", type: "integer" },
                    },
                    records: [
                        { id: 1, name: "JavaScript Developer", color: 1 },
                        { id: 2, name: "Functional Consultant", color: 2 },
                    ],
                },
            },
            actions: {
                1: {
                    id: 1,
                    name: "planning action",
                    res_model: "planning.slot",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "calendar"],
                        [false, "list"],
                    ],
                },
            },
            views: {
                "planning.slot,false,calendar": `
                    <calendar class="o_planning_calendar_test"
                        event_open_popup="true"
                        date_start="start"
                        date_stop="stop"
                        color="color"
                        mode="week"
                        js_class="planning_calendar">
                            <field name="resource_id" />
                            <field name="role_id" filters="1" color="color"/>
                            <field name="state"/>
                    </calendar>`,
                "planning.slot,false,list":
                    '<list js_class="planning_tree"><field name="resource_id"/></list>',
                "planning.slot,false,search": `<search />`,
            },
        };

        const mockRPC = (route, args) => {
            if (args.method === "action_copy_previous_week") {
                assert.step("copy_previous_week()");
                return Promise.resolve({});
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);

        patchWithCleanup(webClient.env.services.action, {
            async doAction(action) {
                assert.deepEqual(
                    action,
                    "planning.planning_send_action",
                    "should open 'Send Planning By Email' form view"
                );
            },
        });

        await click(target.querySelector(".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_button_copy_previous_week"));
        assert.verifySteps(["copy_previous_week()"], "verify action_copy_previous_week() invoked.");

        // deselect "Maganlal" from Assigned to
        await click(target.querySelector(".o_calendar_filter_item[data-value='2'] > input"));
        assert.containsN(target, ".fc-event", 1, "should display 1 events on the week");

        await click(target.querySelector(".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_button_send_all"));

        // Switch the view and verify the notification
        assert.containsOnce(target, ".o_notification_body");
        await click(target, ".o_switch_view.o_list");
        await nextTick();
        assert.doesNotHaveClass(target.querySelector(".o_action_manager"), "o_notification_body");
    });
});
