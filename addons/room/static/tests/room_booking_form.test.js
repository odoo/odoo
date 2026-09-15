import { expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import {
    defineRoomModels,
    mountRoomBookingView,
} from "@room/../tests/room_test_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

const SCHEDULE_SEL = ".btn.rounded-pill i.fa-calendar-plus";
const DAY_SEL = ".o_room_scheduler > div > div:last-child";
const slotSel = (slot) => `#slot${slot}`;

defineRoomModels();

/**
 * Assert that the given slots are correctly displayed in the view.
 * The only distinction between slots is their (text-)background color.
 * Slots are expected to be strings formatted as "hhmm".
 * @param {Object} slots
 * @param {Array<string>} [slots.bookedSlots]
 * @param {Array<string>} [slots.freeSlots]
 * @param {Array<string>} [slots.selectedSlots]
 * @param {Array<string>} [slots.selectableSlots]
 */

function assertSlots(slots) {
    slots.bookedSlots?.forEach((slot) =>
        expect(`${slotSel(slot)} > .bg-secondary`).toHaveCount(1),
    );
    slots.freeSlots?.forEach((slot) =>
        expect(`${slotSel(slot)} > .bg-success`).toHaveCount(1),
    );
    slots.selectedSlots?.forEach((slot) =>
        expect(`${slotSel(slot)} > .text-bg-primary`).toHaveCount(1),
    );
    slots.selectableSlots?.forEach((slot) =>
        expect(`${slotSel(slot)} > .text-bg-success`).toHaveCount(1),
    );
}

test("Room Booking Form - No existing booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => []);
    mockDate("2023-06-17 10:35:00", 0);
    await mountRoomBookingView();

    await contains(SCHEDULE_SEL).click();
    const slotsList = queryAll(".o_room_scheduler_slots .col");
    expect(slotsList[0]).toHaveText("10:35 AM");
    expect(slotsList[1]).toHaveText("11:00 AM");
    expect(slotsList[slotsList.length - 1]).toHaveText("11:30 PM");
    expect(".col > .bg-success").toHaveCount(slotsList.length, {
        message: "All slots should be free",
    });

    await contains(slotSel("2000")).click();
    assertSlots({
        freeSlots: ["1035", "1930"],
        selectedSlots: ["2000"],
        selectableSlots: ["2030", "0000"],
    });
    expect(`${slotSel("2030")} .badge`).toHaveText("0:30");
    expect(`${slotSel("0000")} .badge`).toHaveText("4:00");

    await contains(slotSel("2100")).click();
    assertSlots({
        freeSlots: ["1035", "1930"],
        selectedSlots: ["2000", "2030", "2100"],
        selectableSlots: ["2130", "0000"],
    });
    expect(`${slotSel("2130")} .badge`).toHaveText("1:30");
    expect(`${slotSel("0000")} .badge`).toHaveText("4:00");

    await contains(slotSel("2130")).click();
    assertSlots({
        freeSlots: ["1035", "1930"],
        selectedSlots: ["2000", "2030", "2100", "2130"],
        selectableSlots: ["2200", "0000"],
    });
    expect(`${slotSel("2200")} .badge`).toHaveText("2:00");
    expect(`${slotSel("0000")} .badge`).toHaveText("4:00");

    await contains(slotSel("1930")).click();
    assertSlots({
        freeSlots: ["1035", "1900"],
        selectedSlots: ["1930", "2000", "2100", "2130"],
        selectableSlots: ["2200", "0000"],
    });
    expect(`${slotSel("2200")} .badge`).toHaveText("2:30");
    expect(`${slotSel("0000")} .badge`).toHaveText("4:30");

    await contains(slotSel("1930")).click();
    expect(".col > .bg-success").toHaveCount(slotsList.length, {
        message: "All slots should be free",
    });

    await contains(slotSel("2000")).click();
    assertSlots({
        freeSlots: ["1035", "1930"],
        selectedSlots: ["2000"],
        selectableSlots: ["2030", "2130", "0000"],
    });

    await contains(slotSel("2130")).click();
    assertSlots({
        freeSlots: ["1035", "1930"],
        selectedSlots: ["2000", "2030", "2100", "2130"],
        selectableSlots: ["2200", "0000"],
    });

    await contains(slotSel("2130")).click();
    assertSlots({
        freeSlots: ["1035", "1930"],
        selectedSlots: ["2000"],
        selectableSlots: ["2030", "2100", "2200"],
    });
    expect(`${slotSel("2200")} .badge`).toHaveText("2:00");
    expect(`${slotSel("0000")} .badge`).toHaveText("4:00");

    await contains(slotSel("2000")).click();
    expect(".col > .bg-success").toHaveCount(slotsList.length, {
        message: "All slots should be free",
    });
});

test("Room Booking Form - Existing bookings", async () => {
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
            stop_datetime: "2023-06-17 12:26:00",
        },
        {
            id: 3,
            name: "Booking 3",
            start_datetime: "2023-06-17 15:00:00",
            stop_datetime: "2023-06-17 15:15:00",
        },
        {
            id: 4,
            name: "Booking 4",
            start_datetime: "2023-06-17 15:45:00",
            stop_datetime: "2023-06-17 16:00:00",
        },
    ]);
    mockDate("2023-06-17 10:35:00", 0);
    await mountRoomBookingView();

    await contains(SCHEDULE_SEL).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1500", "1530"],
        freeSlots: ["1035", "1230"],
    });
    // There should be only 5 booked slots
    expect(".col > .bg-secondary").toHaveCount(5);
    await contains(slotSel("1100")).click();
    expect(".col > .bg-secondary").toHaveCount(5);
    expect(".col > .text-bg-primary").toHaveCount(0);

    await contains(slotSel("1300")).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1530"],
        selectedSlots: ["1300"],
        selectableSlots: ["1330", "1500"],
    });

    await contains(slotSel("1530")).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1530"],
        selectedSlots: ["1300"],
        selectableSlots: ["1330", "1500"],
    });

    await contains(slotSel("1500")).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1530"],
        selectedSlots: ["1300", "1330", "1400", "1430", "1500"],
    });

    await contains(slotSel("1800")).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1500", "1530"],
        selectedSlots: ["1800"],
        selectableSlots: ["1830", "0000"],
    });

    await contains(slotSel("1900")).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1500", "1530"],
        selectedSlots: ["1800", "1830", "1900"],
        selectableSlots: ["1930", "0000"],
    });

    await contains(slotSel("1300")).click();
    assertSlots({
        bookedSlots: ["1100", "1130", "1200", "1530"],
        selectedSlots: ["1300"],
        selectableSlots: ["1330", "1500"],
    });
});

test("Room Booking Form - Create a Booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => []);
    onRpc("/room/room_test/booking/create", async (request) => {
        const { params: args } = await request.json();
        expect(args).toEqual({
            name: "Meeting",
            start_datetime: "2023-06-17 11:00:00",
            stop_datetime: "2023-06-17 12:00:00",
        });
        return true;
    });
    mockDate("2023-06-17 10:35:00", 0);
    await mountRoomBookingView();

    await contains(SCHEDULE_SEL).click();
    await contains("input[placeholder='Booking Name']").edit("Meeting");
    await contains(slotSel("1100")).click();
    await contains(slotSel("1200")).click();
    await contains(".o_room_scheduler > div:last-child .btn-primary").click();
    expect(".fa-check-circle.fa-3x").toHaveCount(1);
});

test("Room Booking Form - Editing booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
        {
            id: 2,
            name: "Booking 2",
            start_datetime: "2023-06-17 13:00:00",
            stop_datetime: "2023-06-17 14:00:00",
        },
    ]);
    onRpc("/room/room_test/booking/2/update", async (request) => {
        const { params: args } = await request.json();
        expect(args).toEqual({
            name: "Edited Meeting",
            start_datetime: "2023-06-17 14:00:00",
            stop_datetime: "2023-06-17 15:00:00",
        });
        return true;
    });
    mockDate("2023-06-17 10:35:00", 0);
    await mountRoomBookingView();

    await contains(".o_room_sidebar .list-group-item:first-child").click();
    expect("input[placeholder='Booking Name']").toHaveValue("Booking 1");
    assertSlots({ bookedSlots: ["1330"], selectedSlots: ["1200", "1230", "1300"] });

    await contains(".o_room_sidebar .list-group-item:last-child").click();
    expect("input[placeholder='Booking Name']").toHaveValue("Booking 2");
    assertSlots({
        bookedSlots: ["1200", "1230"],
        selectedSlots: ["1300", "1330", "1400"],
    });

    await contains("input[placeholder='Booking Name']").edit("Edited Meeting");
    await contains(slotSel("1300")).click();
    await contains(slotSel("1400")).click();
    await contains(slotSel("1500")).click();
    await contains(".o_room_scheduler > div:last-child .btn-primary").click();
    expect(".fa-check-circle.fa-3x").toHaveCount(1);
});

test("Room Booking Form - Edit Current Booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Current Booking",
            start_datetime: "2023-06-17 14:00:00",
            stop_datetime: "2023-06-17 15:00:00",
        },
    ]);
    onRpc("/room/room_test/booking/1/update", async (request) => {
        const { params: args } = await request.json();
        expect(args).toEqual({
            name: "Extended Booking",
            start_datetime: "2023-06-17 14:00:00",
            stop_datetime: "2023-06-17 16:00:00",
        });
        return true;
    });
    mockDate("2023-06-17 14:35:00", 0);
    await mountRoomBookingView();

    await contains(".o_room_sidebar .list-group-item:first-child").click();
    expect(`${slotSel("1435")} > .text-bg-primary`).toHaveCount(1);

    // Extend the meeting
    await contains(slotSel("1600")).click();
    await contains("input[placeholder='Booking Name']").edit("Extended Booking");
    // The start is the current slot, but it should not be considered as a new start
    await contains(".o_room_scheduler > div:last-child .btn-primary").click();
    expect(".fa-calendar-xmark.fa-3x").toHaveCount(1);
});

test("Room Booking Form - Receiving new booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => []);
    mockDate("2023-06-17 10:35:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    await contains(SCHEDULE_SEL).click();
    expect(".col > .bg-success").toHaveCount(27);
    await notifyView("booking/create", [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
    ]);
    await contains(SCHEDULE_SEL).click();
    assertSlots({ bookedSlots: ["1200", "1230"] });
    expect(".col > .bg-success").toHaveCount(25);
});

test("Room Booking Form - Receiving deleted booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
    ]);
    mockDate("2023-06-17 10:35:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    await contains(SCHEDULE_SEL).click();
    assertSlots({ bookedSlots: ["1200", "1230"] });
    await notifyView("booking/delete", [{ id: 1 }]);
    await contains(SCHEDULE_SEL).click();
    assertSlots({ freeSlots: ["1200", "1230"] });
});

test("Room Booking Form - Receiving updated booking", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
    ]);
    mockDate("2023-06-17 10:35:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    await contains(SCHEDULE_SEL).click();
    assertSlots({ bookedSlots: ["1200", "1230"] });
    await notifyView("booking/update", [
        {
            id: 1,
            start_datetime: "2023-06-17 13:00:00",
            stop_datetime: "2023-06-17 14:00:00",
            name: "Booking 1",
        },
    ]);
    await contains(SCHEDULE_SEL).click();
    assertSlots({ bookedSlots: ["1300", "1330"], freeSlots: ["1200", "1230"] });
});

test("Room Booking Form - Day Selector", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
        {
            id: 2,
            name: "Booking 2",
            start_datetime: "2023-06-18 13:00:00",
            stop_datetime: "2023-06-18 14:00:00",
        },
    ]);
    mockDate("2023-06-17 10:35:00", 0);
    await mountRoomBookingView();

    await contains(SCHEDULE_SEL).click();
    expect(`${DAY_SEL} button.btn-primary`).toHaveText(/17/);
    assertSlots({ bookedSlots: ["1200", "1230"], freeSlots: ["1300"] });

    await contains(`${DAY_SEL} button.btn-primary + button:enabled`).click();
    expect(`${DAY_SEL} button.btn-primary`).toHaveText(/18/);
    assertSlots({ bookedSlots: ["1300"], freeSlots: ["0000", "0030", "1200"] });

    await contains(`${DAY_SEL} .oi-chevron-right`).click();
    expect(`${DAY_SEL} button.btn-primary`).toHaveText(/25/);
    assertSlots({ freeSlots: ["1200", "1300"] });

    await contains(".o_room_sidebar .list-group-item:first-child").click();
    expect(`${DAY_SEL} button.btn-primary`).toHaveText(/17/);
    assertSlots({ selectedSlots: ["1200", "1230", "1300"] });
});

test("Room Booking Form - Delete booking being edited", async () => {
    onRpc("/room/room_test/get_existing_bookings", () => [
        {
            id: 1,
            name: "Booking 1",
            start_datetime: "2023-06-17 12:00:00",
            stop_datetime: "2023-06-17 13:00:00",
        },
    ]);
    mockDate("2023-06-17 10:35:00", 0);
    const { notifyView } = await mountRoomBookingView(true);

    await contains(".o_room_sidebar .list-group-item:first-child").click();
    assertSlots({ selectedSlots: ["1200", "1230"] });
    await notifyView("booking/delete", [{ id: 1 }]);
    expect(".fa-check-circle.fa-3x").toHaveCount(1);
});
