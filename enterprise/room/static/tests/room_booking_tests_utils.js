/** @odoo-module **/

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";
import {
    waitNotifications,
    waitUntilSubscribe,
} from "@bus/../tests/helpers/websocket_event_deferred";

import { RoomBookingView } from "@room/room_booking/room_booking_view/room_booking_view";

import { browser } from "@web/core/browser/browser";
import { getFixture, mount, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

/**
 * Freeze the intervals and return a method allowing to execute them
 * when needed
 */
const mockInterval = () => {
    const intervals = [];
    patchWithCleanup(browser, {
        setInterval(fn, delay = 0) {
            intervals.push(fn);
        },
        clearInterval() {},
    });
    return () => {
        for (const fn of intervals) {
            fn();
        }
    };
};

/**
 * Helper to mount the Room Booking View
 * @param {Function} mockRPC: mockRPC used to create the test env
 * @param {boolean} useBus: whether to set up the bus service or not
 * @returns {Promise<{target: HTMLElement, execIntervals: Function, notifyView: Function}>}
 */
export const mountRoomBookingView = async (mockRPC, useBus) => {
    const execIntervals = mockInterval();
    const target = getFixture();
    let env;
    let notifyView;
    if (useBus) {
        const pyEnv = await getPyEnv();
        // Logout to use the bus service as a public user
        pyEnv.logout();
        // Subscription to the bus will be done by the component in `mount`.
        // We need to wait for the subscription to be done before sending notifications.
        const busSubscriptionPromise = waitUntilSubscribe("room_booking#room_test");
        /**
         * Send a notification to the view through the bus and wait for the notification to
         * be received.
         * @params {string} notificationType (create/update/delete)
         * @params {Array} bookings
         */
        notifyView = async (notificationType, bookings) => {
            notificationType = "room#1/" + notificationType;
            await busSubscriptionPromise;
            pyEnv["bus.bus"]._sendone("room_booking#room_test", notificationType, bookings);
            await waitNotifications([env, notificationType, bookings]);
            await nextTick();
        };
    }
    env = await makeTestEnv({ mockRPC });
    // Dialog service is mocked so delete bookings directly instead of showing a confirmation modal
    patchWithCleanup(RoomBookingView.prototype, {
        deleteBooking(bookingId) {
            this.removeBooking(bookingId);
        },
    });
    await mount(RoomBookingView, target, {
        env,
        props: {
            id: 1,
            description: "<p class='text-danger o_test_description'>Room's description</p>",
            name: "Test Room",
            accessToken: "room_test",
            bookableBgColor: "#00FF00",
            bookedBgColor: "#FF0000",
        },
    });
    return { target, execIntervals, notifyView };
};
