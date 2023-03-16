/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { ListController } from "@web/views/list/list_controller";

QUnit.module("activity widget");

QUnit.test("list activity widget: reschedule button in dropdown", async (assert) => {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].create({
        icon: "fa-calendar",
        name: "Meeting",
    });
    const attendeeId = pyEnv["calendar.attendee"].create({ partner_id: resPartnerId });
    const meetingId = pyEnv["calendar.event"].create({
        res_model: "calendar.event",
        name: "meeting1",
        start: moment().add(1, "day").format("YYYY-MM-DD"), // tomorrow
        attendee_ids: [attendeeId],
    });
    const activityId_1 = pyEnv["mail.activity"].create({
        name: "OXP",
        activity_type_id: activityTypeId,
        date_deadline: moment().add(1, "day").format("YYYY-MM-DD"), // tomorrow
        state: "planned",
        can_write: true,
        res_id: resPartnerId,
        res_model: "res.partner",
        calendar_event_id: meetingId,
    });
    pyEnv["res.users"].write([pyEnv.currentUserId], {
        activity_ids: [activityId_1],
        activity_state: "today",
        activity_summary: "OXP",
        activity_type_id: activityTypeId,
    });
    const views = {
        "res.users,false,list": `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { openView } = await start({ serverData: { views } });
    patchWithCleanup(ListController.prototype, {
        setup() {
            this._super();
            const selectRecord = this.props.selectRecord;
            this.props.selectRecord = (...args) => {
                assert.step(`select_record ${JSON.stringify(args)}`);
                return selectRecord(...args);
            };
        },
    });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    assert.strictEqual($(".o-mail-ListActivity-summary")[0].innerText, "OXP");

    await click(".o-mail-ActivityButton"); // open the popover
    assert.containsNone($, ".o-mail-ActivityListPopoverItem-editbtn .fa-pencil");
    assert.containsOnce($, ".o-mail-ActivityListPopoverItem-editbtn .fa-calendar");
});
