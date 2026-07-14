import { beforeEach, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    allowTranslations,
    contains,
    defineModels,
    fields,
    models,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    check_in = fields.Datetime();
    check_out = fields.Datetime();
    break_duration = fields.Float();
    can_edit = fields.Boolean();
    in_location = fields.Char();
    out_location = fields.Char();
}

defineModels([HrAttendance]);
defineMailModels();

beforeEach(() => {
    allowTranslations();
    patchWithCleanup(localization, {
        dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
        locale: "en-US",
        timeFormat: "HH:mm:ss",
    });
});

test("the attendance review keeps its dropdown open when using a datetime field", async () => {
    mockService("lazy_session", () => ({
        getValue(key, callback) {
            if (key === "attendance_check_in_ability") {
                callback(true);
            } else if (key === "attendance_state") {
                callback("checked_in");
            } else {
                callback(false);
            }
        },
    }));
    onRpc("/hr_attendance/attendance_user_data", () => ({
        id: 7,
        name: "Test Employee",
        attendance_state: "checked_in",
        last_attendance_worked_hours: 7,
        break_today: 1,
        today_attendance_ids: [{
            id: 42,
            check_in: "2026-08-27 09:00:00",
            check_out: "2026-08-27 17:00:00",
            worked_hours: 7,
            break_duration: 1,
            can_edit: true,
            in_location: false,
            out_location: false,
        }],
    }));

    await mountWithCleanup(ActivityMenu);

    await contains("button:has(i[aria-label='Attendance'])").click();
    await waitFor(".o_att_today_wrap [data-field]");
    expect(".o_att_today_wrap [data-field]").toHaveCount(2);
    await contains(".o_att_today_wrap [data-field='check_in']").click();
    await waitFor(".o_datetime_picker");
    expect(".o_att_today_wrap").toHaveCount(1);
});

test("the displayed total sums the rounded attendance durations", () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    const attendances = [
        {
            id: 42,
            check_in: "2026-07-13 09:00:00",
            check_out: "2026-07-13 09:00:31",
            worked_hours: 31 / 3600,
        },
        {
            id: 43,
            check_in: "2026-07-13 10:00:00",
            check_out: "2026-07-13 10:00:31",
            worked_hours: 31 / 3600,
        },
    ];
    attendanceMenu.state = {
        activeAttendance: attendances[0],
        employee: {
            break_management_enabled: false,
            last_attendance_worked_hours: 0,
        },
        attendances,
    };
    const details = attendanceMenu.attendanceDetails;

    expect(details.sessions.map((session) => session.durationLabel)).toEqual(["0:01", "0:01"]);
    expect(details.totalDisplay).toBe("0:02");
});

test("the displayed break total sums the reviewed attendance breaks", () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    const attendance = {
        id: 42,
        check_in: "2026-07-13 14:00:00",
        check_out: "2026-07-13 19:45:00",
        break_duration: 2,
        worked_hours: 3.75,
    };
    attendanceMenu.state = {
        activeAttendance: attendance,
        employee: {
            break_management_enabled: true,
            break_today: 2,
            last_attendance_worked_hours: 0,
        },
        attendances: [attendance],
    };
    const details = attendanceMenu.attendanceDetails;

    expect(details.breakDisplay).toBe("2:00");
    expect(details.breakDurationLabel).toBe("2:00");
});

test("opening the systray only edits the latest attendance from today", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        employee: null,
        attendances: [],
        activeAttendance: null,
    };
    attendanceMenu.setStreamAvailable = () => {};
    attendanceMenu.searchReadEmployee = async () => {
        attendanceMenu.state.attendances = [{ id: 42, can_edit: true }];
    };
    attendanceMenu.startInlineEdit = (attendance) => expect.step(`edit ${attendance.id}`);

    await attendanceMenu.beforeDropdownOpen();

    expect(attendanceMenu.state.activeAttendance.id).toBe(42);
    expect.verifySteps(["edit 42"]);
});

test("opening the timesheet systray does not wait for attendance review data", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        checkedIn: true,
        showTimesheetsSystray: true,
    };
    attendanceMenu.setStreamAvailable = () => {};
    attendanceMenu.searchReadEmployee = async () => expect.step("refresh");

    await attendanceMenu.beforeDropdownOpen();

    expect.verifySteps([]);
});

test("a readonly attendance can be selected after saving the edited attendance", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        activeAttendance: { id: 42 },
        editingAttendanceId: 42,
        attendances: [
            { id: 42, can_edit: true },
            { id: 43, can_edit: false },
        ],
    };
    attendanceMenu.attendanceRecord = { dirty: true };
    attendanceMenu.saveAttendanceRecord = async () => {
        expect.step("save");
        attendanceMenu.attendanceRecord.dirty = false;
        return true;
    };

    await attendanceMenu.selectAttendance(43);

    expect(attendanceMenu.state.activeAttendance.id).toBe(43);
    expect(attendanceMenu.state.editingAttendanceId).toBe(null);
    expect.verifySteps(["save"]);
});

test("the selected attendance can be collapsed", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        activeAttendance: { id: 42 },
        attendanceReviewExpanded: true,
        editingAttendanceId: 42,
        attendances: [{ id: 42, can_edit: true }],
    };
    attendanceMenu.attendanceRecord = { dirty: false };

    await attendanceMenu.selectAttendance(42);

    expect(attendanceMenu.state.activeAttendance.id).toBe(42);
    expect(attendanceMenu.state.attendanceReviewExpanded).toBe(false);
    expect(attendanceMenu.state.editingAttendanceId).toBe(null);
    expect(attendanceMenu.attendanceRecord).toBe(null);

    await attendanceMenu.selectAttendance(42);

    expect(attendanceMenu.state.activeAttendance.id).toBe(42);
    expect(attendanceMenu.state.attendanceReviewExpanded).toBe(true);
    expect(attendanceMenu.state.editingAttendanceId).toBe(42);
});

test("refresh stops editing when attendance access is lost", () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    const activeAttendance = { id: 42, can_edit: true };
    const employee = {
        id: 7,
        attendance_state: "checked_out",
        today_attendance_ids: [
            {
                id: 42,
                can_edit: false,
                check_in: "2026-07-13 09:00:00",
            },
        ],
    };
    attendanceMenu.state = {
        activeAttendance,
        editingAttendanceId: 42,
        attendances: [],
    };

    attendanceMenu._searchReadEmployeeFill(employee);

    expect(attendanceMenu.state.activeAttendance.id).toBe(42);
    expect(attendanceMenu.state.activeAttendance).not.toBe(activeAttendance);
    expect(attendanceMenu.state.editingAttendanceId).toBe(null);
    expect(attendanceMenu.attendanceRecord).toBe(null);
});

test("attendance record save validates, saves and refreshes the display", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.searchReadEmployee = async () => expect.step("refresh");
    const record = {
        async checkValidity(options) {
            expect(options.displayNotification).toBe(true);
            expect.step("valid");
            return true;
        },
        async save() {
            expect.step("save");
            return true;
        },
    };

    expect(await attendanceMenu.saveAttendanceRecord(record)).toBe(true);
    expect.verifySteps(["valid", "save", "refresh"]);
});

test("a rejected attendance record save reports the error", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.notification = {
        add(message) {
            expect(message).toBe("The attendance overlaps another entry.");
            expect.step("notified");
        },
    };
    const record = {
        checkValidity: async () => true,
        save() {
            throw new Error("The attendance overlaps another entry.");
        },
    };

    expect(await attendanceMenu.saveAttendanceRecord(record)).toBe(false);
    expect.verifySteps(["notified"]);
});

test("check-out saves pending attendance changes", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        checkedIn: true,
        editingAttendanceId: 42,
    };
    attendanceMenu.attendanceRecord = { dirty: true };
    attendanceMenu.state.deviceTrackingEnabled = false;
    attendanceMenu.saveAttendanceRecord = async () => {
        expect.step("save attendance");
        return true;
    };
    attendanceMenu.dropdown = { close: () => expect.step("close") };
    attendanceMenu.checking = async () => expect.step("check out");

    await attendanceMenu.signInOut();

    expect.verifySteps(["save attendance", "close", "check out"]);
});

test("check-out is not toggled again when editing already closed the attendance", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        checkedIn: true,
        editingAttendanceId: 42,
    };
    attendanceMenu.attendanceRecord = { dirty: true };
    attendanceMenu.saveAttendanceRecord = async () => {
        attendanceMenu.state.checkedIn = false;
        expect.step("save attendance");
        return true;
    };
    attendanceMenu.dropdown = { close: () => expect.step("close") };
    attendanceMenu.checking = async () => expect.step("unexpected toggle");

    await attendanceMenu.signInOut();

    expect.verifySteps(["save attendance", "close"]);
    expect(attendanceMenu._attendanceInProgress).toBe(false);
});

test("a failed attendance save re-enables check-in/out", async () => {
    const attendanceMenu = Object.create(ActivityMenu.prototype);
    attendanceMenu.state = {
        checkedIn: true,
        editingAttendanceId: 42,
    };
    attendanceMenu.attendanceRecord = { dirty: true };
    attendanceMenu.saveAttendanceRecord = async () => false;
    attendanceMenu.checking = async () => expect.step("unexpected check out");

    await attendanceMenu.signInOut();

    expect.verifySteps([]);
    expect(attendanceMenu._attendanceInProgress).toBe(false);
});
