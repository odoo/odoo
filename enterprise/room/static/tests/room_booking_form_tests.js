/** @odoo-module **/

import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";

import { mountRoomBookingView } from "@room/../tests/room_booking_tests_utils";

import { click, editInput, nextTick, patchDate } from "@web/../tests/helpers/utils";
import {
    makeFakeDialogService,
    makeFakeNotificationService,
    makeFakePwaService,
} from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

/**
 * Assert that the given slots are correctly displayed in the view.
 * The only distinction between slots is their (text-)background color.
 * Slots are expected to be strings formatted as "hhmm".
 * @param {QUnit.assert} assert
 * @param {HTMLElement} target
 * @param {Object} slots
 * @param {Array} slots.bookedSlots
 * @param {Array} slots.freeSlots
 * @param {Array} slots.selectedSlots
 * @param {Array} slots.selectableSlots
 */
const assertSlots = (assert, target, slots) => {
    slots.bookedSlots?.forEach((slot) => {
        assert.containsOnce(target, `#slot${slot} > .bg-secondary`);
    });
    slots.freeSlots?.forEach((slot) => {
        assert.containsOnce(target, `#slot${slot} > .bg-success`);
    });
    slots.selectedSlots?.forEach((slot) => {
        assert.containsOnce(target, `#slot${slot} > .text-bg-primary`);
    });
    slots.selectableSlots?.forEach((slot) => {
        assert.containsOnce(target, `#slot${slot} > .text-bg-success`);
    });
};

/**
 * Click on a slot in the view and waits for the next tick.
 * @param {HTMLElement} target
 * @param {string} slot ("hhmm" format).
 * @returns {Promise}
 */
const clickOnSlot = async (target, slot) => {
    click(target, `#slot${slot}`);
    await nextTick();
};

/**
 * Click on the schedule button and waits for the next tick.
 * @param {HTMLElement} target
 * @returns {Promise}
 * */
const clickSchedule = async (target) => {
    click(target, ".btn.rounded-pill i.fa-calendar-plus-o");
    await nextTick();
};

QUnit.module("Room Booking Form", (hooks) => {
    hooks.beforeEach(async () => {
        addBusServicesToRegistry();
        registry.category("services").add("dialog", makeFakeDialogService());
        registry.category("services").add("notification", makeFakeNotificationService());
        registry.category("services").add("pwa", makeFakePwaService());
        registry.category("services").add("ui", uiService);
    });

    // Test view flow with no existing bookings
    QUnit.test("Room Booking Form - No existing booking", async (assert) => {
        const mockRPC = async (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        await clickSchedule(target);
        // First slot is now
        const slotsList = target.querySelectorAll(".o_room_scheduler_slots .col");
        assert.strictEqual(slotsList[0].innerText, "10:35 AM");
        // Second slot is the next half hour
        assert.strictEqual(slotsList[1].innerText, "11:00 AM");
        // Last slot is 11:30 PM (midnight is added when a start date is selected)
        assert.strictEqual(slotsList[slotsList.length - 1].innerText, "11:30 PM");
        // All slots should be free
        assert.containsN(target, ".col > .bg-success", slotsList.length);

        // Click on a slot to select a start date (8PM)
        await clickOnSlot(target, "2000");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1930"],
            selectedSlots: ["2000"],
            selectableSlots: ["2030", "0000"],
        });
        assert.containsOnce(target, "#slot2030:contains('0:30')");
        assert.containsOnce(target, "#slot0000:contains('4:00')");

        // Click on another slot to select a stop date (9PM)
        await clickOnSlot(target, "2100");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1930"],
            selectedSlots: ["2000", "2030", "2100"],
            selectableSlots: ["2130", "0000"],
        });
        // Duration of selectable slots should not have changed
        assert.containsOnce(target, "#slot2130:contains('1:30')");
        assert.containsOnce(target, "#slot0000:contains('4:00')");

        // Click on another slot to select another stop date
        await clickOnSlot(target, "2130");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1930"],
            selectedSlots: ["2000", "2030", "2100", "2130"],
            selectableSlots: ["2200", "0000"],
        });
        assert.containsOnce(target, "#slot2200:contains('2:00')");
        assert.containsOnce(target, "#slot0000:contains('4:00')");

        // Click on another slot to select another start date
        await clickOnSlot(target, "1930");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1900"],
            selectedSlots: ["1930", "2000", "2100", "2130"],
            selectableSlots: ["2200", "0000"],
        });
        assert.containsOnce(target, "#slot2200:contains('2:30')");
        assert.containsOnce(target, "#slot0000:contains('4:30')");

        // Click on selected start to deselect start and stop
        await clickOnSlot(target, "1930");
        // Every slot should appear as free
        assert.containsN(target, ".col > .bg-success", slotsList.length);

        // Click on a slot to select a start date
        await clickOnSlot(target, "2000");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1930"],
            selectedSlots: ["2000"],
            selectableSlots: ["2030", "2130", "0000"],
        });
        // Click on a slot to select a stop date
        await clickOnSlot(target, "2130");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1930"],
            selectedSlots: ["2000", "2030", "2100", "2130"],
            selectableSlots: ["2200", "0000"],
        });
        // Click on selected stop date to deselect it
        await clickOnSlot(target, "2130");
        assertSlots(assert, target, {
            freeSlots: ["1035", "1930"],
            selectedSlots: ["2000"],
            selectableSlots: ["2030", "2100", "2200"],
        });
        // Duration of selectable slots should not have changed
        assert.containsOnce(target, "#slot2200:contains('2:00')");
        assert.containsOnce(target, "#slot0000:contains('4:00')");

        // Click on selected start to deselect it
        await clickOnSlot(target, "2000");
        // Every slot should appear as free
        assert.containsN(target, ".col > .bg-success", slotsList.length);
    });

    // Test view flow with existing bookings
    QUnit.test("Room Booking Form - Existing bookings", async (assert) => {
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
                        stop_datetime: "2023-06-17 11:26:00",
                    },
                    {
                        id: 3,
                        name: "Booking 3",
                        start_datetime: "2023-06-17 14:00:00",
                        stop_datetime: "2023-06-17 14:15:00",
                    },
                    {
                        id: 4,
                        name: "Booking 4",
                        start_datetime: "2023-06-17 14:45:00",
                        stop_datetime: "2023-06-17 15:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        await clickSchedule(target);
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1500", "1530"],
            freeSlots: ["1035", "1230"],
        });
        // There should be only 5 booked slots
        assert.containsN(target, ".col > .bg-secondary", 5);
        // Nothing happens when clicking on a booked slot
        await clickOnSlot(target, "1100");
        // There should still be 5 booked slots
        assert.containsN(target, ".col > .bg-secondary", 5);
        // No slot should have been selected
        assert.containsNone(target, ".col > .text-bg-primary");
        // Select a start slot between 2 bookings
        await clickOnSlot(target, "1300");
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1530"],
            selectedSlots: ["1300"],
            selectableSlots: ["1330", "1500"],
        });
        // Clicking on a slot that is booked does nothing
        await clickOnSlot(target, "1530");
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1530"],
            selectedSlots: ["1300"],
            selectableSlots: ["1330", "1500"],
        });
        // Select the end slot (first booked slot that follows the selected start that should be selectable)
        await clickOnSlot(target, "1500");
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1530"],
            selectedSlots: ["1300", "1330", "1400", "1430", "1500"],
        });
        // Click on a free slot after the next booked slot (should select it as start)
        await clickOnSlot(target, "1800");
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1500", "1530"],
            selectedSlots: ["1800"],
            selectableSlots: ["1830", "0000"],
        });
        // Select a stop date
        await clickOnSlot(target, "1900");
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1500", "1530"],
            selectedSlots: ["1800", "1830", "1900"],
            selectableSlots: ["1930", "0000"],
        });
        // Click on a free slot before the previous booked slot (should reset end)
        await clickOnSlot(target, "1300");
        assertSlots(assert, target, {
            bookedSlots: ["1100", "1130", "1200", "1530"],
            selectedSlots: ["1300"],
            selectableSlots: ["1330", "1500"],
        });
    });

    // Test booking creation flow
    QUnit.test("Room Booking Form - Create a Booking", async (assert) => {
        assert.expect(2);
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [];
            } else if (route === "/room/room_test/booking/create") {
                assert.deepEqual(args, {
                    name: "Meeting",
                    start_datetime: "2023-06-17 10:00:00",
                    stop_datetime: "2023-06-17 11:00:00",
                });
                return true;
            }
        };

        patchDate(2023, 5, 17, 10, 35, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        await clickSchedule(target);
        await editInput(target, "input[placeholder='Booking Name']", "Meeting");
        await clickOnSlot(target, "1100");
        await clickOnSlot(target, "1200");
        // Mocked RPC will assert that the booking data is correct
        click(target, ".o_room_scheduler > div:last-child .btn-primary");
        await nextTick();
        // Should come back to main view (no notification has been sent so the
        // sidebar won't be updated)
        assert.containsOnce(target, ".fa-check-circle.fa-3x");
    });

    // Test booking edition flow
    QUnit.test("Room Booking Form - Editing booking", async (assert) => {
        assert.expect(13);
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
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
                ];
            } else if (route === "/room/room_test/booking/2/update") {
                assert.deepEqual(args, {
                    name: "Edited Meeting",
                    start_datetime: "2023-06-17 13:00:00",
                    stop_datetime: "2023-06-17 14:00:00",
                });
                return true;
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        click(target, ".o_room_sidebar .list-group-item:first-child");
        await nextTick();
        // Check that the slots of the booking to edit are selected
        assert.strictEqual(
            target.querySelector("input[placeholder='Booking Name']").value,
            "Booking 1",
        );
        assertSlots(assert, target, {
            bookedSlots: ["1330"],
            selectedSlots: ["1200", "1230", "1300"],
        });
        // Click on the other booking in the sidebar to make sure the view is updated
        click(target, ".o_room_sidebar .list-group-item:last-child");
        await nextTick();
        // Check that the title and the slots have been updated accordingly
        assert.strictEqual(
            target.querySelector("input[placeholder='Booking Name']").value,
            "Booking 2",
        );
        assertSlots(assert, target, {
            bookedSlots: ["1200", "1230"],
            selectedSlots: ["1300", "1330", "1400"],
        });
        // Change title, start and end date
        await editInput(target, "input[placeholder='Booking Name']", "Edited Meeting");
        await clickOnSlot(target, "1300");
        await clickOnSlot(target, "1400");
        await clickOnSlot(target, "1500");
        // Mocked RPC will assert that the data is correct
        click(target, ".o_room_scheduler > div:last-child .btn-primary");
        await nextTick();
        // Should come back to main view (no notification has been sent so the
        // sidebar won't be updated)
        assert.containsOnce(target, ".fa-check-circle.fa-3x");
    });

    // Test flow of the editing the current booking (first slot shown is now and should be selected,
    // and extending it should not update the start date)
    QUnit.test("Room Booking Form - Edit Current Booking", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Current Booking",
                        start_datetime: "2023-06-17 13:00:00",
                        stop_datetime: "2023-06-17 14:00:00",
                    },
                ];
            } else if (route === "/room/room_test/booking/1/update") {
                assert.deepEqual(args, {
                    name: "Extended Booking",
                    start_datetime: "2023-06-17 13:00:00",
                    stop_datetime: "2023-06-17 15:00:00",
                });
                return true;
            }
        };
        patchDate(2023, 5, 17, 14, 35, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        click(target, ".o_room_sidebar .list-group-item:first-child");
        await nextTick();
        // Check that the first slot is now and is selected
        assert.containsOnce(target, "#slot1435 > .text-bg-primary");
        // Extend the meeting
        await clickOnSlot(target, "1600");
        await editInput(target, "input[placeholder='Booking Name']", "Extended Booking");
        // The start is the current slot, but it should not be considered as a new start
        click(target, ".o_room_scheduler > div:last-child .btn-primary");
        await nextTick();
        // Should come back to main view
        assert.containsOnce(target, ".fa-calendar-times-o.fa-3x");
    });

    // Test reception of a new booking while the view is opened (slots should update accordingly)
    QUnit.test("Room Booking Form - Receiving new booking", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { notifyView, target } = await mountRoomBookingView(mockRPC, true);
        await clickSchedule(target);
        assert.containsN(target, ".col > .bg-success", 27);
        // Send a new booking notification
        await notifyView("booking/create", [
            {
                id: 1,
                name: "Booking 1",
                start_datetime: "2023-06-17 11:00:00",
                stop_datetime: "2023-06-17 12:00:00",
            },
        ]);
        await nextTick();
        // Slots should appear as booked
        assertSlots(assert, target, {
            bookedSlots: ["1200", "1230"],
        });
        // Other slots should remain free
        assert.containsN(target, ".col > .bg-success", 25);
    });

    // Test reception of a deleted booking while the view is opened (slots should update accordingly)
    QUnit.test("Room Booking Form - Receiving deleted booking", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 11:00:00",
                        stop_datetime: "2023-06-17 12:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { notifyView, target } = await mountRoomBookingView(mockRPC, true);
        await clickSchedule(target);
        // Make sure slots are marked as taken
        assertSlots(assert, target, {
            bookedSlots: ["1200", "1230"],
        });
        // Send notification of booking deletion
        await notifyView("booking/delete", [{ id: 1 }]);
        // Check that the slots have been freed
        assertSlots(assert, target, {
            freeSlots: ["1200", "1230"],
        });
    });

    // Test reception of a booking update while the view is opened (slots should update accordingly)
    QUnit.test("Room Booking Form - Receiving updated booking", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 11:00:00",
                        stop_datetime: "2023-06-17 12:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { notifyView, target } = await mountRoomBookingView(mockRPC, true);
        await clickSchedule(target);
        // Make sure slots are booked
        assertSlots(assert, target, {
            bookedSlots: ["1200", "1230"],
        });
        // Send notification of booking update
        await notifyView("booking/update", [
            {
                id: 1,
                start_datetime: "2023-06-17 12:00:00",
                stop_datetime: "2023-06-17 13:00:00",
                name: "Booking 1",
            },
        ]);
        // Check that the booked slots have changed
        assertSlots(assert, target, {
            bookedSlots: ["1300", "1330"],
            freeSlots: ["1200", "1230"],
        });
    });

    // Test correct behavior of the day selector (slots should update when changing date)
    QUnit.test("Room Booking Form - Day Selector", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 11:00:00",
                        stop_datetime: "2023-06-17 12:00:00",
                    },
                    {
                        id: 2,
                        name: "Booking 2",
                        start_datetime: "2023-06-18 12:00:00",
                        stop_datetime: "2023-06-18 13:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { target } = await mountRoomBookingView(mockRPC);
        await clickSchedule(target);
        const daySelector = target.querySelector(".o_room_scheduler > div > div:last-child");
        // Selected day is today by default
        assert.containsOnce(daySelector, "button.btn-primary:contains('17')");
        assertSlots(assert, target, {
            bookedSlots: ["1200", "1230"],
            freeSlots: ["1300"],
        });
        // Next day should not appear disabled and should load booking of next day
        click(daySelector, "button.btn-primary + button:enabled");
        await nextTick();
        assert.containsOnce(daySelector, "button.btn-primary:contains('18')");
        // Check that slots updated (and that morning slots are shown)
        assertSlots(assert, target, {
            bookedSlots: ["1300"],
            freeSlots: ["0000", "0030", "1200"],
        });
        // Click on next week
        click(daySelector, ".oi-chevron-right");
        await nextTick();
        assert.containsOnce(daySelector, "button.btn-primary:contains('25')");
        // Check that slots updated
        assertSlots(assert, target, {
            freeSlots: ["1200", "1300"],
        });
        // Click on the first booking in the sidebar
        click(target, ".o_room_sidebar .list-group-item:first-child");
        await nextTick();
        // Should come back to today
        assert.containsOnce(daySelector, "button.btn-primary:contains('17')");
        assertSlots(assert, target, {
            selectedSlots: ["1200", "1230", "1300"],
        });
    });

    // Check that the form is closed when the booking being edited is deleted by another user
    QUnit.test("Room Booking Form - Delete booking being edited", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/room/room_test/get_existing_bookings") {
                return [
                    {
                        id: 1,
                        name: "Booking 1",
                        start_datetime: "2023-06-17 11:00:00",
                        stop_datetime: "2023-06-17 12:00:00",
                    },
                ];
            }
        };
        patchDate(2023, 5, 17, 10, 35, 0);
        const { notifyView, target } = await mountRoomBookingView(mockRPC, true);
        click(target, ".o_room_sidebar .list-group-item:first-child");
        await nextTick();
        assertSlots(assert, target, {
            selectedSlots: ["1200", "1230"],
        });
        // Notify view that booking has been deleted
        await notifyView("booking/delete", [{ id: 1 }]);
        // Make sure we left the booking form
        assert.containsOnce(target, ".fa-check-circle.fa-3x");
    });
});
