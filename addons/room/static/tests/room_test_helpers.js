import {
    busModels,
    waitNotifications,
    waitUntilSubscribe,
} from "@bus/../tests/bus_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { animationFrame, runAllTimers } from "@odoo/hoot-dom";
import {
    defineModels,
    getMockEnv,
    logout,
    makeMockEnv,
    makeMockServer,
    mountWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";

import { RoomBookingView } from "@room/room_booking/room_booking_view/room_booking_view";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

export function defineRoomModels() {
    return defineModels(roomModels);
}

export const roomModels = { ...webModels, ...busModels, ...mailModels };

export class RoomBookingViewTest extends RoomBookingView {
    static template = "room.roomBookingViewTest";
}

/**
 * Helper to mount the Room Booking View
 * @param {boolean} useBus: whether to set up the bus service or not
 * @returns {Promise<{
 *     env: import("@web/env").OdooEnv,
 *     notifyView: (notificationType: string, bookings: Array<any>) => Promise<void> | null
 * }>}
 */
export async function mountRoomBookingView(useBus) {
    let env;
    let notifyView;
    if (useBus) {
        const { env: pyEnv } = await makeMockServer();
        // Logout to use the bus service as a public user
        logout();
        // Subscription to the bus will be done by the component in `mount`.
        // We need to wait for the subscription to be done before sending notifications.
        const busSubscriptionPromise = waitUntilSubscribe("room_booking#room_test");
        /**
         * Send a notification to the view through the bus and wait for the notification to
         * be received.
         */
        notifyView = async (notificationType, bookings) => {
            notificationType = "room#1/" + notificationType;
            await busSubscriptionPromise;
            pyEnv["bus.bus"]._sendone(
                "room_booking#room_test",
                notificationType,
                bookings,
            );
            await runAllTimers();
            await waitNotifications([env, notificationType, bookings]);
            await animationFrame();
        };
    }
    prepareRegistry();
    env = getMockEnv() || (await makeMockEnv());
    await mountWithCleanup(RoomBookingViewTest, {
        env,
        props: {
            id: 1,
            description:
                "<p class='text-danger o_test_description'>Room's description</p>",
            name: "Test Room",
            accessToken: "room_test",
            bookableBgColor: "#00FF00",
            bookedBgColor: "#FF0000",
        },
    });
    return { env, notifyView };
}

function prepareRegistry() {
    registry.category("main_components").remove("mail.ChatHub");
    registry.category("main_components").remove("discuss.CallInvitations");
    registry.category("main_components").remove("bus.ConnectionAlert");
    const REQUIRED_SERVICES = [
        "bus_service",
        "bus.parameters",
        "multi_tab",
        "legacy_multi_tab",
        "worker_service",
        "title",
        "orm",
        "field",
        "name",
        "home_menu",
        "enterprise_subscription",
        "menu",
        "action",
        "notification",
        "dialog",
        "popover",
        "hotkey",
        "localization",
        "company",
        "view",
        "overlay",
        "ui",
        "effect",
        "pwa",
    ];
    Object.keys(serviceRegistry.content).forEach((e) => {
        if (!REQUIRED_SERVICES.includes(e)) {
            serviceRegistry.remove(e);
        }
    });
}
