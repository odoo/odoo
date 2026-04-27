/** @odoo-module **/

import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";

import { mountRoomBookingView } from "@room/../tests/room_booking_tests_utils";

import {
    click,
    editInput,
    mockTimeout,
    nextTick,
    patchDate,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import {
    makeFakeDialogService,
    makeFakeNotificationService,
    makeFakePwaService,
} from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

/**
 * Assert that the current time displayed on the view is the expected one
 */
const assertDisplayedTime = (assert, target, expectedTime) => {
    assert.containsOnce(
        target,
        `.o_room_top:contains('${luxon.DateTime.fromSQL(expectedTime).toFormat("TDDDD")}')`,
    );
};

/**
 * Assert that the room status is the expected one (right background color, right "busy" or "free"
 * status (icon), expected remaining time if there is an ongoing booking, and correct number of
 * bookings in the sidebar)
 * @param {Object} assert
 * @param {HTMLElement} target
 * @param {Object|boolean} remainingTime: remaining time of the current booking or false if no booking
 * @param {number} nbBookings: number of bookings in the sidebar
 */
const assertRoomStatus = (assert, target, remainingTime, nbBookings) => {
    if (remainingTime) {
        assert.strictEqual(
            target.querySelector(".o_room_remaining_time").innerText,
            luxon.Duration.fromObject(remainingTime).toFormat("hh:mm:ss"),
        );
        // Check that the room uses the busy background color as there is an ongoing booking
        assert.hasAttrValue(
            target.querySelector(".o_room_booking_main > div"),
            "style",
            "background-image: linear-gradient(#FF0000DD, #FF0000DD)",
        );
        // Check that the "Booked" icon is shown
        assert.containsOnce(target, "i.fa-calendar-times-o.fa-3x");
    } else {
        assert.containsNone(target, ".o_room_remaining_time");
        // Check that the room uses the available background color as there is no ongoing booking
        assert.hasAttrValue(
            target.querySelector(".o_room_booking_main > div"),
            "style",
            "background-image: linear-gradient(#00FF00DD, #00FF00DD)",
        );
        // Check that the "available" icon is shown
        assert.containsOnce(target, "i.fa-check-circle.fa-3x");
    }
    assert.containsN(target, ".o_room_sidebar .list-group-item", nbBookings);
};

/**
 * Click on the quick book button and wait for the next tick.
 * @param {HTMLElement} target
 * @returns {Promise}
 */
const clickQuickBook = async (target) => {
    click(target, ".btn-dark i.fa-rocket");
    await nextTick();
};

QUnit.module("Room Booking View", (hooks) => {
    hooks.beforeEach(async () => {
        addBusServicesToRegistry();
        registry.category("services").add("dialog", makeFakeDialogService());
        registry.category("services").add("notification", makeFakeNotificationService());
        registry.category("services").add("pwa", makeFakePwaService());
        registry.category("services").add("ui", uiService);
    });

    // Test UI when there is no meeting scheduled
    QUnit.test("Room Booking View - no meeting scheduled", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [];
            }
        };
        patchDate(2023, 5, 17, 13, 0, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        assertDisplayedTime(assert, target, "2023-06-17 13:00:00");
        assertRoomStatus(assert, target, false, 0);
        // Check that room description is shown and formatted
        assert.containsOnce(target, ".o_room_sidebar p.o_test_description.text-danger");
    });

    // Test UI when there is an ongoing meeting
    QUnit.test("Room Booking View - ongoing meeting", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 10:00:00",
                        stop_datetime: "2023-06-17 11:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 11, 15, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        assertDisplayedTime(assert, target, "2023-06-17 11:15:00");
        assertRoomStatus(assert, target, { minutes: 44, seconds: 59 }, 1);
    });

    // Test quick booking flow
    QUnit.test("Room Booking View - Quick Booking", async (assert) => {
        assert.expect(7);
        let expectedCreateArgs;
        const buttonsSelector = "input[placeholder='Booking Name'] + div button";
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 10:00:00",
                        stop_datetime: "2023-06-17 11:00:00",
                    },
                ];
            } else if (route === "/room/room_test/booking/create") {
                assert.deepEqual(args, expectedCreateArgs);
                return true;
            }
        };
        patchDate(2023, 5, 17, 9, 59, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        await clickQuickBook(target);
        await editInput(target, "input[placeholder='Booking Name']", "Meeting");
        // Next booking starts in more than 1h, show the 3 quick booking buttons
        assert.containsN(target, buttonsSelector, 3);
        // Last button should book the room for 1h
        expectedCreateArgs = {
            name: "Meeting",
            start_datetime: "2023-06-17 08:59:00",
            stop_datetime: "2023-06-17 09:59:00",
        };
        click(target, buttonsSelector + ":last-child");
        await nextTick();
        // delete the created booking
        await click(target, ".o_room_sidebar .list-group-item:first-child .fa-trash");
        await nextTick();
        patchDate(2023, 5, 17, 10, 25, 0);
        await clickQuickBook(target);
        // Next booking starts in less than 1h but more than 30 min, show 2 buttons
        assert.containsN(target, buttonsSelector, 2);
        // Last button should book the room for 30 min, and name should have been reset to default
        expectedCreateArgs = {
            name: "Public Booking",
            start_datetime: "2023-06-17 09:25:00",
            stop_datetime: "2023-06-17 09:55:00",
        };
        click(target, buttonsSelector + ":last-child");
        await nextTick();
        // delete the created booking
        await click(target, ".o_room_sidebar .list-group-item:first-child .fa-trash");
        await nextTick();
        patchDate(2023, 5, 17, 10, 43, 0);
        await clickQuickBook(target);
        // Next booking starts in less than 30 min but more than 15 min, show 1 button
        assert.containsOnce(target, buttonsSelector);
        // Only button should book the room for 15 min
        expectedCreateArgs = {
            name: "Public Booking",
            start_datetime: "2023-06-17 09:43:00",
            stop_datetime: "2023-06-17 09:58:00",
        };
        click(target, buttonsSelector);
        await nextTick();
        // delete the created booking
        await click(target, ".o_room_sidebar .list-group-item:first-child .fa-trash");
        await nextTick();
        patchDate(2023, 5, 17, 10, 59, 0);
        await clickQuickBook(target);
        // Next booking starts in less than 15 min, show no button
        assert.containsNone(target, buttonsSelector);
    });

    // Check that the UI adapts correctly when going from no ongoing booking to ongoing booking
    QUnit.test("Room Booking View - Booking Started", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 10:00:00",
                        stop_datetime: "2023-06-17 11:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 59, 0);
        const { execIntervals, target } = await mountRoomBookingView(mockRPC);
        assertRoomStatus(assert, target, false, 1);

        patchDate(2023, 5, 17, 11, 0, 0);
        await nextTick();
        execIntervals();
        await nextTick();
        assertRoomStatus(assert, target, { minutes: 59, seconds: 59 }, 1);
        // Make sure there is no error with the following intervals
        execIntervals();
        await nextTick();
    });

    // Check that the UI adapts correctly when going from ongoing booking to no ongoing booking
    QUnit.test("Room Booking View - Booking Ended", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 09:00:00",
                        stop_datetime: "2023-06-17 10:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 59, 59);
        const { execIntervals, target } = await mountRoomBookingView(mockRPC);
        assertRoomStatus(assert, target, { seconds: 0 }, 1);
        patchDate(2023, 5, 17, 11, 0, 0);
        await nextTick();
        execIntervals();
        await nextTick();
        assertRoomStatus(assert, target, false, 0);
        // Make sure there is no error with the following intervals
        execIntervals();
        await nextTick();
    });

    // Check that the UI adapts correctly when the date changes
    QUnit.test("Room Booking View - Day Change", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-18 09:00:00",
                        stop_datetime: "2023-06-18 10:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 23, 59, 59);
        const { execIntervals, target } = await mountRoomBookingView(mockRPC);
        // Today should be shown even if there is no booking planned today
        assert.strictEqual(
            target.querySelector(".o_room_sidebar h6:first-of-type").innerText,
            "Today",
        );
        // Since today is shown and since there is a booking planned tomorrow,
        // there should be 2 dates shown in the sidebar
        assert.containsN(target, ".o_room_sidebar h6", 2);
        patchDate(2023, 5, 18, 0, 0, 0);
        await nextTick();
        execIntervals();
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_room_sidebar h6:first-of-type").innerText,
            "Today",
        );
        // Only date shown in the sidebar is today
        assert.containsOnce(target, ".o_room_sidebar h6", 1);
    });

    // Check that after some inactivity, the main view displaying the room status is shown
    // (see INACTIVITY_TIMEOUT @room/static/src/js/views/room_booking_view.js)
    QUnit.test("Room Booking View - Inactivity reset", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [];
            }
        };
        const inactivity_timeout = 120000;
        const { advanceTime } = mockTimeout();
        patchDate(2023, 5, 17, 10, 0, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        await clickQuickBook(target);
        await advanceTime(inactivity_timeout);
        await clickQuickBook(target);
        await advanceTime(inactivity_timeout - 1);
        // Writing the title should reset the timeout
        triggerEvent(target, "", "keydown", { key: "s" });
        await advanceTime(inactivity_timeout - 1);
        assert.containsNone(target, ".fa-check-circle.fa-3x");
        // Clicking anywhere should reset the timeout
        click(target, ".o_room_booking_main");
        await advanceTime(inactivity_timeout - 1);
        assert.containsNone(target, ".fa-check-circle.fa-3x");
        // Make sure timeout still occurs
        await advanceTime(1);
        assert.containsOnce(target, "i.fa-check-circle.fa-3x");
    });

    // Check that the UI adapts correctly when a booking ends but is followed immediately by another
    QUnit.test("Room Booking View - Consecutive Bookings", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 09:00:00",
                        stop_datetime: "2023-06-17 10:00:00",
                    },
                    {
                        id: 2,
                        name: "Booking 2",
                        start_datetime: "2023-06-17 10:00:00",
                        stop_datetime: "2023-06-17 11:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 59, 59);
        const { execIntervals, target } = await mountRoomBookingView(mockRPC);
        assertRoomStatus(assert, target, { seconds: 0 }, 2);
        patchDate(2023, 5, 17, 11, 0, 0);
        await nextTick();
        execIntervals();
        await nextTick();
        assertRoomStatus(assert, target, { minutes: 59, seconds: 59 }, 1);
        // Make sure next interval does not remove current booking
        execIntervals();
        await nextTick();
        assertRoomStatus(assert, target, { minutes: 59, seconds: 59 }, 1);
    });

    // Check that the UI adapts correctly when a new booking notification is received
    QUnit.test("Room Booking View - Receiving new booking through bus", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 09:00:00",
                        stop_datetime: "2023-06-17 10:00:00",
                    },
                    {
                        id: 2,
                        name: "Booking 2",
                        start_datetime: "2023-06-17 13:00:00",
                        stop_datetime: "2023-06-17 14:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 8, 30, 0);
        const { notifyView, target } = await mountRoomBookingView(mockRPC, true);
        assertRoomStatus(assert, target, false, 2);
        // Send a new booking notification (for later today)
        await notifyView("booking/create", [
            {
                id: 3,
                name: "Booking 3",
                start_datetime: "2023-06-17 12:00:00",
                stop_datetime: "2023-06-17 12:30:00",
            },
        ]);
        assertRoomStatus(assert, target, false, 3);
        // Check that the booking is at the right place in the sidebar
        assert.containsOnce(
            target,
            ".o_room_sidebar .list-group-item:nth-child(2):contains('Booking 3')",
        );
        // Send a new booking notification (for now)
        await notifyView("booking/create", [
            {
                id: 4,
                name: "Booking 4",
                start_datetime: "2023-06-17 07:30:00",
                stop_datetime: "2023-06-17 08:00:00",
            },
        ]);
        assert.containsOnce(
            target,
            ".o_room_sidebar .list-group-item:first-child:contains('Booking 4')",
        );
        assertRoomStatus(assert, target, { minutes: 29, seconds: 59 }, 4);
        // Send a new booking notification (for in the past - can be done from backend)
        await notifyView("booking/create", [
            {
                id: 5,
                name: "Booking 5",
                start_datetime: "2023-06-17 06:00:00",
                stop_datetime: "2023-06-17 06:30:00",
            },
        ]);
        assert.containsNone(target, ".o_room_sidebar .list-group-item:contains('Booking 5')");
    });

    // Check that the UI adapts correctly when a notification of a booking update is received
    QUnit.test("Room Booking View - Receiving booking update through bus", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 09:00:00",
                        stop_datetime: "2023-06-17 10:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 30, 0);
        const { execIntervals, notifyView, target } = await mountRoomBookingView(mockRPC, true);
        assertRoomStatus(assert, target, { minutes: 29, seconds: 59 }, 1);
        // Send notification to reschedule booking later and change its name
        await notifyView("booking/update", [
            {
                id: 1,
                name: "Booking 1 rescheduled",
                start_datetime: "2023-06-17 10:30:00",
                stop_datetime: "2023-06-17 11:00:00",
            },
        ]);
        assertRoomStatus(assert, target, false, 1);
        assert.containsOnce(
            target,
            ".o_room_sidebar .list-group-item:contains('Booking 1 rescheduled')",
        );
        // Send notification to reschedule now a booking that already ended (i.e. we update
        // a booking that is not in the list of bookings of the view)
        await notifyView("booking/update", [
            {
                id: 2,
                name: "Ended to Current",
                start_datetime: "2023-06-17 09:00:00",
                stop_datetime: "2023-06-17 10:00:00",
            },
        ]);
        assert.containsOnce(
            target,
            ".o_room_sidebar .list-group-item:contains('Ended to Current')",
        );
        // Check remaining time is correct to make sure it will be updated at the next step
        assertRoomStatus(assert, target, { minutes: 29, seconds: 59 }, 2);
        // Send a notification to extend the current meeting
        await notifyView("booking/update", [
            {
                id: 2,
                name: "Ended to Current",
                start_datetime: "2023-06-17 09:00:00",
                stop_datetime: "2023-06-17 10:30:00",
            },
        ]);
        // There should still be 2 meetings
        assertRoomStatus(assert, target, { minutes: 59, seconds: 59 }, 2);
        // Send notification to reschedule a meeting in the past (it makes no sense but it should
        // not crash the view)
        await notifyView("booking/update", [
            {
                id: 1,
                name: "Booking 1 in the past",
                start_datetime: "2023-06-17 08:00:00",
                stop_datetime: "2023-06-17 08:30:00",
            },
        ]);
        await execIntervals();
        await nextTick();
        assertRoomStatus(assert, target, { minutes: 59, seconds: 59 }, 1);
    });

    // Check that the UI adapts correctly when a notification of a booking deletion is received
    QUnit.test("Room Booking View - Receiving booking deletion through bus", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
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
                ];
            }
        };
        patchDate(2023, 5, 17, 11, 15, 0);
        const { notifyView, target } = await mountRoomBookingView(mockRPC, true);
        await nextTick();
        assertRoomStatus(assert, target, { minutes: 44, seconds: 59 }, 2);
        // send notification to delete the current booking
        await notifyView("booking/delete", [{ id: 1 }]);
        assertRoomStatus(assert, target, false, 1);
        assert.containsOnce(target, ".o_room_sidebar .list-group-item:contains('Booking 2')");
        // send notification to delete the remaining booking
        await notifyView("booking/delete", [{ id: 2 }]);
        assertRoomStatus(assert, target, false, 0);
    });

    // Check that the UI behaves correctly when a booking spans several days (can be done from
    // the backend)
    QUnit.test("Room Booking View - Booking spanning several days", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 10:00:00",
                        stop_datetime: "2023-06-19 10:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 18, 10, 0, 0);
        const { execIntervals, target } = await mountRoomBookingView(mockRPC);
        // Even if the booking started yesterday, it should be in the sidebar
        assertDisplayedTime(assert, target, "2023-06-18 10:00:00");
        assertRoomStatus(assert, target, { hours: 24, minutes: 59, seconds: 59 }, 1);
        patchDate(2023, 5, 19, 10, 0, 0);
        await nextTick();
        execIntervals();
        await nextTick();
        assertDisplayedTime(assert, target, "2023-06-19 10:00:00");
        // Booking should still be in the sidebar
        assertRoomStatus(assert, target, { minutes: 59, seconds: 59 }, 1);
        patchDate(2023, 5, 19, 12, 0, 0);
        await nextTick();
        execIntervals();
        await nextTick();
        assertDisplayedTime(assert, target, "2023-06-19 12:00:00");
        // It shouldn't be in the sidebar anymore
        assertRoomStatus(assert, target, false, 0);
    });
});
