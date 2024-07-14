/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { serializeDate } from "@web/core/l10n/dates";
import { ListController } from "@web/views/list/list_controller";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";
const { DateTime } = luxon;

QUnit.module("activity (patch)");

QUnit.test("list activity widget: sign button in dropdown", async (assert) => {
    const pyEnv = await startServer();
    const activityTypeId = pyEnv["mail.activity.type"].create({});
    const activityId = pyEnv["mail.activity"].create({
        display_name: "Sign a new contract",
        activity_category: "sign_request",
        date_deadline: serializeDate(DateTime.now().plus({ days: 1 })), // tomorrow
        can_write: true,
        state: "planned",
        user_id: pyEnv.currentUserId,
        create_uid: pyEnv.currentUserId,
        activity_type_id: activityTypeId,
    });
    pyEnv["res.users"].write([pyEnv.currentUserId], {
        activity_ids: [activityId],
        activity_state: "today",
        activity_summary: "Sign a new contract",
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
    assert.strictEqual($(".o-mail-ListActivity-summary")[0].innerText, "Sign a new contract");

    await click(".o-mail-ActivityButton"); // open the popover
    await contains(".o-mail-ActivityListPopoverItem-markAsDone", { count: 0 });
    await contains(".o-mail-ActivityListPopoverItem-requestSign");
});
