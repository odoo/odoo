import { luxon } from "@web/core/l10n/luxon";
import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { advanceTime, freezeTime, mockDate, runAllTimers } from "@odoo/hoot-mock";
import {
    defineRoomModels,
    mountRoomBookingView,
} from "@room/../tests/room_test_helpers";
import {
    asyncStep,
    contains,
    onRpc,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

import {
    INACTIVITY_TIMEOUT,
    REFRESH_INTERVAL,
} from "@room/room_booking/room_booking_view/room_booking_view";

const { DateTime, Duration } = luxon;

function assertDisplayedTime(expectedTime) {
    expect(".o_room_top").toHaveText(
        DateTime.fromSQL(expectedTime).toFormat("T\nDDDD"),
    );
}

/**
 * Assert that the room status is the expected one (right background color, right "busy" or "free"
 * status (icon), expected remaining time if there is an ongoing booking, and correct number of
 * bookings in the sidebar)
 *
 * @param {Object | false} remainingTime: remaining time of the current booking or false if no booking
 * @param {number} nbBookings: number of bookings in the sidebar
 */
function assertRoomStatus(remainingTime, nbBookings) {
    if (remainingTime) {
        const time = Duration.fromObject(remainingTime).toFormat("hh:mm:ss");
        // Ignore second digits as it will be affected by mocked time being advanced
        expect(".o_room_remaining_time").toHaveText(
            new RegExp(`^${time.slice(0, -2)}\\d\\d$`),
        );
        expect(".o_room_booking_main > div").toHaveStyle(
            "background-image: linear-gradient(#FF0000DD, #FF0000DD)",
            { inline: true },
        );
        expect("i.fa-calendar-xmark.fa-3x").toHaveCount(1);
    } else {
        expect(".o_room_remaining_time").toHaveCount(0);
        expect(".o_room_booking_main > div").toHaveStyle(
            "background-image: linear-gradient(#00FF00DD, #00FF00DD)",
            { inline: true },
        );
        expect("i.fa-check-circle.fa-3x").toHaveCount(1);
    }
    expect(".o_room_sidebar .list-group-item").toHaveCount(nbBookings);
}

const QUICK_BOOK_SEL = ".btn-dark i.fa-rocket";

defineRoomModels();

test("Room Booking View - no meeting scheduled", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => []);
    mockDate("2023-06-17 13:00:00", 0);
    await mountRoomBookingView();

    assertDisplayedTime("2023-06-17 13:00:00");
    assertRoomStatus(false, 0);
    expect(".o_room_sidebar p.o_test_description").toHaveClass("text-danger");
});

test("Room Booking View - ongoing meeting", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-17 12:00:00",
        },
    ]);
    mockDate("2023-06-17 11:15:00", 0);
    await mountRoomBookingView();

    assertDisplayedTime("2023-06-17 11:15:00");
    assertRoomStatus({ minutes: 44, seconds: 59 }, 1);
});

test("Room Booking View - Quick Booking", async () => {
    const buttonsSelector = "input[placeholder='Booking Name'] + div button";
    let expectedCreateArgs;
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-17 12:00:00",
        },
    ]);
    onRpc("/room/room_test/booking/create", async (request) => {
        const { params: args } = await request.json();
        expect(args).toEqual(expectedCreateArgs);
        return 10;
    });
    onRpc("/room/room_test/booking/10/delete", async () => {
        await notifyView("booking/delete", [{ id: 10 }]);
        asyncStep("delete_booking");
        return true;
    });
    mockDate("2023-06-17 09:59:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    await contains(QUICK_BOOK_SEL).click();
    await contains("input[placeholder='Booking Name']").edit("Meeting");
    expect(buttonsSelector).toHaveCount(3);

    // Last button should book the room for 1 hour, and name should have been reset to default
    expectedCreateArgs = {
        name: "Meeting",
        start_datetime: "2023-06-17 09:59:00",
        stop_datetime: "2023-06-17 10:59:00",
    };
    await contains(`${buttonsSelector}:last-child`).click();
    await contains(
        ".o_room_sidebar .list-group-item:first-child .fa-trash-can",
    ).click();
    await contains(".modal-footer button:contains('Delete')").click();
    await runAllTimers();
    await waitForSteps(["delete_booking"]);

    mockDate("2023-06-17 10:25:00", 0);
    await contains(QUICK_BOOK_SEL).click();
    expect(buttonsSelector).toHaveCount(2);

    expectedCreateArgs = {
        name: "Public Booking",
        start_datetime: "2023-06-17 10:25:00",
        stop_datetime: "2023-06-17 10:55:00",
    };
    await contains(`${buttonsSelector}:last-child`).click();
    await contains(
        ".o_room_sidebar .list-group-item:first-child .fa-trash-can",
    ).click();
    await contains(".modal-footer button:contains('Delete')").click();
    await waitForSteps(["delete_booking"]);

    mockDate("2023-06-17 10:43:00", 0);
    await contains(QUICK_BOOK_SEL).click();
    expect(buttonsSelector).toHaveCount(1);

    expectedCreateArgs = {
        name: "Public Booking",
        start_datetime: "2023-06-17 10:43:00",
        stop_datetime: "2023-06-17 10:58:00",
    };
    await contains(buttonsSelector).click();
    await contains(
        ".o_room_sidebar .list-group-item:first-child .fa-trash-can",
    ).click();
    await contains(".modal-footer button:contains('Delete')").click();
    await waitForSteps(["delete_booking"]);

    mockDate("2023-06-17 10:59:00", 0);
    await contains(QUICK_BOOK_SEL).click();
    expect(buttonsSelector).toHaveCount(0);
});

test("Room Booking View - Booking Started", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-17 12:00:00",
        },
    ]);
    mockDate("2023-06-17 10:59:00", 0);
    freezeTime();
    await mountRoomBookingView();

    assertRoomStatus(false, 1);

    mockDate("2023-06-17 11:00:00", 0);
    await advanceTime(REFRESH_INTERVAL);
    assertRoomStatus({ minutes: 59, seconds: 59 }, 1);
    // Make sure there is no error with the following intervals
    await runAllTimers();
});

test("Room Booking View - Booking Ended", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 10:00:00",
            stop_datetime: "2023-06-17 11:00:00",
        },
    ]);
    mockDate("2023-06-17 10:59:59", 0);
    await mountRoomBookingView();

    assertRoomStatus({ seconds: 0 }, 1);
    mockDate("2023-06-17 11:00:00", 0);
    await advanceTime(REFRESH_INTERVAL);
    assertRoomStatus(false, 0);
    // Make sure there is no error with the following intervals
    await runAllTimers();
});

test("Room Booking View - Day Change", async () => {
    freezeTime();
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-18 10:00:00",
            stop_datetime: "2023-06-18 11:00:00",
        },
    ]);
    mockDate("2023-06-17 23:59:59", 0);
    await mountRoomBookingView();

    expect(".o_room_sidebar h6:first-of-type:contains('Today')").toHaveCount(1);
    expect(".o_room_sidebar h6").toHaveCount(2);
    mockDate("2023-06-18 00:00:00", 0);

    await advanceTime(REFRESH_INTERVAL);
    expect(".o_room_sidebar h6:first-of-type").toHaveText("Today");
    expect(".o_room_sidebar h6").toHaveCount(1);
});

test("Room Booking View - Inactivity reset", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => []);
    mockDate("2023-06-17 10:00:00", 0);
    freezeTime();
    await mountRoomBookingView();

    await contains(QUICK_BOOK_SEL).click();
    await advanceTime(INACTIVITY_TIMEOUT);
    await contains(QUICK_BOOK_SEL).click();
    await advanceTime(INACTIVITY_TIMEOUT - 1);
    // Writing the title should reset the timeout
    await press("s");
    await advanceTime(INACTIVITY_TIMEOUT - 1);
    expect(".fa-check-circle.fa-3x").toHaveCount(0);

    // Clicking anywhere should reset the timeout
    await contains(".o_room_booking_main").click();
    await advanceTime(INACTIVITY_TIMEOUT - 1);
    expect(".fa-check-circle.fa-3x").toHaveCount(0);

    // Make sure timeout still occurs
    await advanceTime(1);
    expect(".fa-check-circle.fa-3x").toHaveCount(1);
});

test("Room Booking View - Consecutive Bookings", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 10:00:00",
            stop_datetime: "2023-06-17 11:00:00",
        },
        {
            id: 2,
            name: "Booking 2",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-17 12:00:00",
        },
    ]);
    freezeTime();
    mockDate("2023-06-17 10:59:59", 0);
    await mountRoomBookingView();

    assertRoomStatus({ seconds: 1 }, 2);

    mockDate("2023-06-17 11:00:00", 0);
    await advanceTime(REFRESH_INTERVAL);
    assertRoomStatus({ minutes: 59, seconds: 59 }, 1);

    // Make sure next interval does not remove current booking
    await advanceTime(REFRESH_INTERVAL);
    assertRoomStatus({ minutes: 59, seconds: 58 }, 1);
});

test("Room Booking View - Receiving new booking through bus", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 10:00:00",
            stop_datetime: "2023-06-17 11:00:00",
        },
        {
            id: 2,
            name: "Booking 2",
            start_datetime: "2023-06-17 14:00:00",
            stop_datetime: "2023-06-17 15:00:00",
        },
    ]);
    mockDate("2023-06-17 08:30:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    assertRoomStatus(false, 2);

    await notifyView("booking/create", [
        {
            id: 3,
            name: "Booking 3",
            start_datetime: "2023-06-17 13:00:00",
            stop_datetime: "2023-06-17 13:30:00",
        },
    ]);
    assertRoomStatus(false, 3);
    expect(".o_room_sidebar .list-group-item:eq(1)").toHaveText(/Booking 3/);

    await notifyView("booking/create", [
        {
            id: 4,
            name: "Booking 4",
            start_datetime: "2023-06-17 08:30:00",
            stop_datetime: "2023-06-17 09:00:00",
        },
    ]);
    expect(".o_room_sidebar .list-group-item:eq(0)").toHaveText(/Booking 4/);
    assertRoomStatus({ minutes: 29, seconds: 59 }, 4);

    await notifyView("booking/create", [
        {
            id: 5,
            name: "Booking 5",
            start_datetime: "2023-06-17 07:00:00",
            stop_datetime: "2023-06-17 07:30:00",
        },
    ]);
    expect(".o_room_sidebar .list-group-item:contains('Booking 5')").toHaveCount(0);
});

test("Room Booking View - Receiving booking update through bus", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 10:00:00",
            stop_datetime: "2023-06-17 11:00:00",
        },
    ]);
    mockDate("2023-06-17 10:30:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    assertRoomStatus({ minutes: 29, seconds: 59 }, 1);

    await notifyView("booking/update", [
        {
            id: 1,
            name: "Booking 1 rescheduled",
            start_datetime: "2023-06-17 11:30:00",
            stop_datetime: "2023-06-17 12:00:00",
        },
    ]);
    assertRoomStatus(false, 1);
    expect(".o_room_sidebar .list-group-item").toHaveText(/Booking 1 rescheduled/s);

    await notifyView("booking/update", [
        {
            id: 2,
            name: "Ended to Current",
            start_datetime: "2023-06-17 10:00:00",
            stop_datetime: "2023-06-17 11:00:00",
        },
    ]);
    expect(".o_room_sidebar .list-group-item:eq(0)").toHaveText(/Ended to Current/);
    assertRoomStatus({ minutes: 29, seconds: 59 }, 2);

    await notifyView("booking/update", [
        {
            id: 2,
            name: "Ended to Current",
            start_datetime: "2023-06-17 10:00:00",
            stop_datetime: "2023-06-17 11:30:00",
        },
    ]);
    assertRoomStatus({ minutes: 59, seconds: 59 }, 2);

    await notifyView("booking/update", [
        {
            id: 1,
            name: "Booking 1 in the past",
            start_datetime: "2023-06-17 09:00:00",
            stop_datetime: "2023-06-17 09:30:00",
        },
    ]);
    await advanceTime(REFRESH_INTERVAL);
    assertRoomStatus({ minutes: 59, seconds: 59 }, 1);
});

test("Room Booking View - Receiving booking deletion through bus", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-17 12:00:00",
        },
        {
            id: 2,
            name: "Booking 2",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
    ]);
    mockDate("2023-06-17 11:15:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    assertRoomStatus({ minutes: 44, seconds: 59 }, 2);

    await notifyView("booking/delete", [{ id: 1 }]);
    assertRoomStatus(false, 1);
    expect(".o_room_sidebar .list-group-item").toHaveText(/Booking 2/);

    await notifyView("booking/delete", [{ id: 2 }]);
    assertRoomStatus(false, 0);
});

test("Room Booking View - Booking spanning several days", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-19 11:00:00",
        },
    ]);
    mockDate("2023-06-18 10:00:00", 0);
    await mountRoomBookingView();

    assertDisplayedTime("2023-06-18 10:00:00");
    assertRoomStatus({ hours: 24, minutes: 59, seconds: 59 }, 1);

    mockDate("2023-06-19 10:00:00", 0);
    await advanceTime(REFRESH_INTERVAL);
    assertDisplayedTime("2023-06-19 10:00:00");
    assertRoomStatus({ minutes: 59, seconds: 59 }, 1);

    mockDate("2023-06-19 12:00:00", 0);
    await runAllTimers();
    assertDisplayedTime("2023-06-19 12:00:00");
    assertRoomStatus(false, 0);
});
