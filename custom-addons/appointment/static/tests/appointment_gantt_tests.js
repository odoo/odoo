/** @odoo-module */

import { patchDate } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { dragPill, getGridContent } from "@web_gantt/../tests/helpers";
import { getServerModels } from "./appointment_tests_common";

// minimalist version of the appointment gantt view
const ganttViewArch = `
    <gantt date_start="start" date_stop="stop" js_class="appointment_booking_gantt"
           default_group_by="partner_ids">

        <field name="appointment_attended"/>
        <field name="appointment_type_id"/>
        <field name="partner_id"/>
        <field name="partner_ids"/>
        <field name="user_id"/>

        <templates>
            <div t-name="gantt-popover">
                <ul>
                    <li>Name: <t t-out="gantt_pill_contact_name"/></li>
                    <li>Phone: <t t-out="gantt_pill_contact_phone"/></li>
                    <li>Email: <t t-out="gantt_pill_contact_email"/></li>
                </ul>
            </div>
        </templates>

    </gantt>`;

let serverData;
/** @type {HTMLElement} */
QUnit.module("appointment.GanttView", {
    beforeEach() {
        patchDate(2022, 0, 3, 8, 0, 0);

        setupViewRegistries();

        const models = getServerModels();
        models["calendar.event"].records[0].appointment_type_id = 1;
        models["calendar.event"].records[1].appointment_type_id = 1;
        models["calendar.event"].records[2].appointment_type_id = 1;
        serverData = {
            models: models,
            views: {
                "foo,false,gantt": `<gantt/>`,
                "foo,false,search": `<search/>`,
            },
        };
    },
});

QUnit.test("empty default group gantt rendering", async (assert) => {
    const partners = ["Partner 1", "Partner 214", "Partner 216"];
    const partnerEvents = [
        ["Event 3", "Event 1"],
        ["Event 2", "Event 3", "Event 1"],
        ["Event 2", "Event 3"],
    ];
    await makeView({
        type: "gantt",
        resModel: "calendar.event",
        serverData,
        mockRPC: function (route, args) {
            if (
                args.model === "calendar.event" &&
                args.method === "write" &&
                args.args[0][0] === 2 &&
                "partner_ids" in args.args[1]
            ) {
                const methodArgs = args.args[1];
                assert.strictEqual(methodArgs.start, "2022-01-21 22:00:00");
                assert.strictEqual(methodArgs.stop, "2022-01-21 23:00:00");
                const [unlinkCommand, linkCommand] = methodArgs.partner_ids;
                assert.strictEqual(unlinkCommand[0], 3);
                assert.strictEqual(unlinkCommand[1], 214);
                assert.strictEqual(linkCommand[0], 4);
                assert.strictEqual(linkCommand[1], 1);

                assert.step("write partners and date");
            } else if (
                args.model === "calendar.event" &&
                args.method === "write" &&
                args.args[0][0] === 2 &&
                "user_id" in args.args[1]
            ) {
                assert.strictEqual(args.args[1].user_id, 1);

                assert.step("write user id");
            } else if (args.model === "calendar.event" && args.method === "get_gantt_data") {
                assert.step("get_gantt_data");
            }
        },
        arch: ganttViewArch,
    });
    const { rows } = getGridContent();
    for (let pid = 0; pid < partners.length; pid++) {
        assert.strictEqual(rows[pid].title, partners[pid]);
        for (let eid = 0; eid < partnerEvents[pid].length; eid++) {
            assert.strictEqual(rows[pid].pills[eid].title, partnerEvents[pid][eid]);
        }
    }

    const { drop, moveTo } = await dragPill("Event 2", { nth: 1 });
    await moveTo({ row: 1, column: 21, part: 2 });
    await drop();
    assert.verifySteps([
        "get_gantt_data",
        "write partners and date",
        "write user id",
        "get_gantt_data",
    ]);
});
