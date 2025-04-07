import { listenStoreFetch, start, waitStoreFetch } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";

import { defineHrAttendanceModels } from "@hr_attendance/../tests/hr_attendance_test_helpers";

defineHrAttendanceModels();
describe.current.tags("desktop");

test("attendance fetched with other init data", async () => {
    const initParams = [
        "failures",
        "systray_get_activities",
        "init_messaging",
        "/hr_attendance/user_data",
    ];
    listenStoreFetch(initParams, {
        async onRpc(request) {
            const { params } = await request.json();
            // Ensure all the params are present at the same time on the same RPC.
            expect(params.fetch_params).toEqual(initParams);
        },
    });
    await start();
    await waitStoreFetch(initParams);
});
