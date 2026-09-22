import { expect, test } from "@odoo/hoot";
import { AttendanceActionHelper } from "@hr_attendance/views/attendance_helper_view";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

defineMailModels();

test.tags("desktop");
test("loading sample data asks before generating anything", async () => {
    patchWithCleanup(user, { hasGroup: async () => true });
    onRpc("has_demo_data", () => false);
    const dialog = {};
    mockService("dialog", {
        add(_component, props) {
            expect.step("asked");
            Object.assign(dialog, props);
            return () => {};
        },
    });
    mockService("action", {
        doAction(action) {
            expect.step(action);
        },
    });

    await mountWithCleanup(AttendanceActionHelper, { props: { noContentHelp: "" } });
    await contains("a", { text: "Load sample data" }).click();
    expect.verifySteps(["asked"], {
        message: "no fake record is created until the user agrees",
    });

    await dialog.confirm();
    expect.verifySteps(["hr_attendance.action_load_demo_data"]);
});
