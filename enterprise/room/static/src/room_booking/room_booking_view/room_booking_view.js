/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";
import { registry } from "@web/core/registry";
import { RoomBookingForm } from "@room/room_booking/room_booking_form/room_booking_form";
import { RoomBookingRemainingTime } from "@room/room_booking/room_booking_remaining_time";
import { RoomDisplayTime } from "@room/room_booking/room_display_time";
import { useInterval } from "@room/room_booking/useInterval";
import { useService } from "@web/core/utils/hooks";

import {
    Component,
    markup,
    onWillStart,
    onWillUnmount,
    useExternalListener,
    useState,
} from "@odoo/owl";

// Time (in ms, so 2 minutes) after which the user is considered inactive
// and the app goes back to the main screen
const INACTIVITY_TIMEOUT = 120000;

/**
 * Format a booking received from the server to the format used in the room booking view
 * @param {Object} booking
 * @param {Number} booking.id
 * @param {String} booking.name
 * @param {String} booking.start_datetime
 * @param {String} booking.stop_datetime
 */
function formatServerBooking(booking) {
    return {
        id: booking.id,
        name: booking.name,
        interval: luxon.Interval.fromDateTimes(
            deserializeDateTime(booking.start_datetime),
            deserializeDateTime(booking.stop_datetime),
        ),
    };
}

export class RoomBookingView extends Component {
    static components = {
        RoomBookingForm,
        RoomBookingRemainingTime,
        RoomDisplayTime,
    };
    static template = "room.RoomBookingView";
    static props = {
        accessToken: String,
        bookableBgColor: String,
        bookedBgColor: String,
        description: String,
        id: Number,
        name: String,
    };

    setup() {
        this.manageRoomUrl = `/room/${this.props.accessToken}`;
        this.pwaService = useService("pwa");
        this.state = useState({
            bookings: [],
            bookingName: undefined,
            bookingToEdit: undefined,
            currentBooking: null,
            currentDate: this.now.startOf("day"),
            scheduleBooking: false,
            scheduleBookingQuickCreate: false,
            showInstallPwaButton: !isDisplayStandalone() && this.pwaService.isSupportedOnBrowser,
        });
        // Show bookings updates in live
        this.busService = this.env.services.bus_service;
        this.busService.addChannel("room_booking#" + this.props.accessToken);
        this.busService.subscribe(`room#${this.props.id}/booking/create`, (bookings) =>
            bookings.forEach((booking) => this.addBooking(formatServerBooking(booking))),
        );
        this.busService.subscribe(`room#${this.props.id}/booking/delete`, (bookings) =>
            bookings.forEach((booking) => this.removeBooking(booking.id)),
        );
        this.busService.subscribe(`room#${this.props.id}/booking/update`, (bookings) =>
            bookings.forEach((booking) => this.udpateBooking(formatServerBooking(booking))),
        );
        this.busService.subscribe(`room#${this.props.id}/reload`, (url) => redirect(url));
        this.notificationService = useService("notification");
        this.dialogService = useService("dialog");
        this.ui = useService("ui");
        onWillStart(this.loadBookings);

        // Every second, check if a booking started/ended
        useInterval(this.refreshBookingView.bind(this), 1000);

        // If the user is inactive for more than the  INACTIVITY_TIMEOUT, reset the view
        ["pointerdown", "keydown"].forEach((event) =>
            useExternalListener(window, event, () => {
                browser.clearTimeout(this.inactivityTimer);
                this.inactivityTimer = browser.setTimeout(() => {
                    this.resetBookingForm();
                }, INACTIVITY_TIMEOUT);
            }),
        );
        onWillUnmount(() => browser.clearTimeout(this.inactivityTimer));
    }

    //----------------------------------------------------------------------
    // Formats
    //----------------------------------------------------------------------

    get timeFormat() {
        return luxon.DateTime.TIME_SIMPLE;
    }

    get dateFormat() {
        return luxon.DateTime.DATE_HUGE;
    }

    //----------------------------------------------------------------------
    // Getters
    //----------------------------------------------------------------------

    /**
     * Return the background color of the main view which depends on the
     * room's availability
     */
    get bgColor() {
        return (
            (this.state.currentBooking ? this.props.bookedBgColor : this.props.bookableBgColor) +
            "DD"
        );
    }

    /**
     * Return the next booking
     * @returns {Object} booking
     */
    get nextBooking() {
        return this.state.currentBooking ? this.state.bookings[1] : this.state.bookings[0];
    }

    get now() {
        return luxon.DateTime.now();
    }

    /**
     * @returns {string} Raw HTML of the description
     */
    get roomDescription() {
        return markup(this.props.description);
    }

    //----------------------------------------------------------------------
    // Methods
    //----------------------------------------------------------------------

    /**
     * Shows a confirmation dialog to delete the given booking
     * @param {Number} bookingId
     */
    deleteBooking(bookingId) {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this booking?"),
            confirmLabel: _t("Delete"),
            confirm: () => rpc(`${this.manageRoomUrl}/booking/${bookingId}/delete`),
            cancel: () => {},
        });
    }

    /**
     * Edit the given booking with the given values
     * @param {Number} bookingId
     * @param {String} name
     * @param {luxon.DateTime} start
     * @param {luxon.DateTime} end
     */
    async editBooking(bookingId, name, start, end) {
        this.ui.block();
        await rpc(`${this.manageRoomUrl}/booking/${bookingId}/update`, {
            name,
            start_datetime: serializeDateTime(start),
            stop_datetime: serializeDateTime(end),
        });
        this.removeBooking(bookingId);
        this.addBooking({
            id: bookingId,
            interval: luxon.Interval.fromDateTimes(start, end),
            name,
        });
        this.ui.unblock();
        this.resetBookingForm();
    }

    endCurrentBooking() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure you want to end the current booking ?"),
            confirmLabel: _t("End Booking"),
            confirm: () => {
                const { id, name, interval } = this.state.currentBooking;
                this.editBooking(id, name, interval.start, this.now);
            },
            cancel: () => {},
        });
    }

    installPwa() {
        browser.open(
            `/scoped_app?app_id=room&path=${encodeURIComponent(browser.location.pathname.slice(1))}&app_name=${encodeURIComponent(this.props.name)}`,
        );
    }

    /**
     * Load the existing bookings for the room.
     * New bookings will be received through the busService.
     */
    async loadBookings() {
        const bookings = await rpc(`${this.manageRoomUrl}/get_existing_bookings`);
        for (const booking of bookings) {
            this.addBooking(formatServerBooking(booking));
        }
        this.refreshBookingView();
    }

    /**
     * Book the room for the given duration
     * @param {Number} duration (in minutes)
     */
    quickCreateBooking(duration) {
        this.scheduleBooking(
            this.state.bookingName,
            this.now,
            this.now.plus({ minutes: duration }),
        );
    }

    /**
     * Update the current status of the room (booked or available), and remove
     * the booking of the list of bookings if it is finished.
     */
    refreshBookingView() {
        // Check if current booking is finished
        if (this.state.currentBooking?.interval.end < this.now) {
            this.removeBooking(this.state.currentBooking.id);
        }
        const currentBooking =
            this.state.bookings[0]?.interval.start < this.now ? this.state.bookings[0] : null;
        // Check if next booking has started or if current booking has been rescheduled
        if (this.state.currentBooking?.interval.end !== currentBooking?.interval.end) {
            this.state.currentBooking = currentBooking;
        }
        // Update the currentDate that is used in the sidebar
        if (this.state.currentDate.day !== this.now.startOf("day").day) {
            this.state.currentDate = this.now.startOf("day");
        }
    }

    /**
     * Get back to the main view
     */
    resetBookingForm() {
        this.state.scheduleBooking = false;
        this.state.scheduleBookingQuickCreate = false;
        this.state.bookingToEdit = undefined;
        this.state.bookingName = undefined;
    }

    /**
     * Schedule a booking for the given time range, and reset the view to the main screen
     * @param {String} name
     * @param {luxon.DateTime} start
     * @param {luxon.DateTime} end
     */
    async scheduleBooking(name, start, end) {
        name = name || _t("Public Booking");
        this.ui.block();
        const bookingId = await rpc(`${this.manageRoomUrl}/booking/create`, {
            name,
            start_datetime: serializeDateTime(start),
            stop_datetime: serializeDateTime(end),
        });
        this.addBooking({
            id: bookingId,
            interval: luxon.Interval.fromDateTimes(start, end),
            name,
        });
        this.ui.unblock();
        this.resetBookingForm();
    }

    //----------------------------------------------------------------------
    // Bus Methods
    //----------------------------------------------------------------------

    /**
     * Add a booking to the list of bookings, keeping the list sorted by start date
     * @param {Object} newBooking
     * @param {Number} newBooking.id
     * @param {String} newBooking.name
     * @param {Luxon.Interval} newBooking.interval
     */
    addBooking(newBooking) {
        // Do not add bookings already added or already finished
        if (
            this.state.bookings.map((booking) => booking.id).includes(newBooking.id) ||
            newBooking.interval.end < this.now
        ) {
            return;
        }
        const newBookingInsertIdx = this.state.bookings.findIndex(
            (booking) => booking.interval.start > newBooking.interval.start,
        );
        if (newBookingInsertIdx === -1) {
            this.state.bookings.push(newBooking);
        } else {
            this.state.bookings.splice(newBookingInsertIdx, 0, newBooking);
        }
        // If the new booking has already started (eg. book now), refresh the view
        if (newBooking.interval.start < this.now) {
            this.refreshBookingView();
        }
    }

    /**
     * Remove a booking from the list of bookings
     * @param {Number} bookingId
     */
    removeBooking(bookingId) {
        const bookingIdx = this.state.bookings.findIndex((booking) => booking.id === bookingId);
        if (bookingIdx !== -1) {
            this.state.bookings.splice(bookingIdx, 1);
            // Refresh view if the booking deleted was the current one
            if (this.state.currentBooking?.id === bookingId) {
                this.refreshBookingView();
            }
        }
        // Leave form view if booking being edited has been deleted or updated by another user
        if (this.state.bookingToEdit?.id === bookingId && !this.ui.isBlocked) {
            this.resetBookingForm();
            this.notificationService.add(
                _t("The booking you were editing has been updated or deleted."),
            );
        }
    }

    /**
     * Update the given booking with the new values. For simplicity, the existing booking
     * is replaced by the new one so that order is maintained if the start date changed.
     * @param {Object} booking
     * @param {Number} booking.id
     * @param {String} booking.start_datetime
     * @param {String} booking.stop_datetime
     * @param {String} booking.name
     */
    udpateBooking(booking) {
        this.removeBooking(booking.id);
        this.addBooking(booking);
    }
}

registry.category("public_components").add("room.room_booking_view", RoomBookingView);
