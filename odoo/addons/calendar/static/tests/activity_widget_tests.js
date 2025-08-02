/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { serializeDate } from "@web/core/l10n/dates";
import { ListController } from "@web/views/list/list_controller";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

const { DateTime } = luxon;

QUnit.module("activity widget");

QUnit.test("list activity widget: reschedule button in dropdown", async (assert) => {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].create({
        icon: "fa-calendar",
        name: "Meeting",
    });
    const tomorrow = serializeDate(DateTime.now().plus({ days: 1 }));
    const attendeeId = pyEnv["calendar.attendee"].create({ partner_id: resPartnerId });
    const meetingId = pyEnv["calendar.event"].create({
        res_model: "calendar.event",
        name: "meeting1",
        start: tomorrow,
        attendee_ids: [attendeeId],
    });
    const activityId_1 = pyEnv["mail.activity"].create({
        name: "OXP",
        activity_type_id: activityTypeId,
        date_deadline: tomorrow,
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
            super.setup();
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
    await contains(".o-mail-ActivityListPopoverItem-editbtn .fa-pencil", { count: 0 });
    await contains(".o-mail-ActivityListPopoverItem-editbtn .fa-calendar");
});
