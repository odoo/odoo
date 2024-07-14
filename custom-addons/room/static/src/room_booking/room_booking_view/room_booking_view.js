/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
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

export class RoomBookingView extends Component {
    static components = {
        RoomBookingForm,
        RoomBookingRemainingTime,
        RoomDisplayTime,
    };
    static props = {
        accessToken: String,
        bookableBgColor: String,
        bookedBgColor: String,
        description: String,
        id: Number,
        name: String,
    };
    static template = "room.RoomBookingView";

    setup() {
        this.manageRoomUrl = `/room/${this.props.accessToken}`;
        this.state = useState({
            bookings: [],
            bookingName: undefined,
            bookingToEdit: undefined,
            currentBooking: null,
            currentDate: this.now.startOf("day"),
            scheduleBooking: false,
            scheduleBookingQuickCreate: false,
        });
        // If there are several rooms opened at the same time using the same
        // browser profile, they will all receive every room notification
        // leading to incorrect states. We advise the user to close the other
        // tabs.
        this.multiTab = useService("multi_tab");
        this.showMultiTabWarning = !this.multiTab.isOnMainTab();
        // Show bookings updates in live
        this.busService = this.env.services.bus_service;
        this.busService.addChannel("room_booking#" + this.props.accessToken);
        this.busService.subscribe("booking/create", (bookings) => {
            bookings.forEach((booking) => this.addBooking(booking));
        });
        this.busService.subscribe("booking/delete", (bookings) => {
            bookings.forEach((booking) => this.removeBooking(booking.id));
        });
        this.busService.subscribe("booking/update", (bookings) => {
            bookings.forEach((booking) => this.udpateBooking(booking));
        });
        this.busService.subscribe("reload", (url) => redirect(url));
        this.rpc = useService("rpc");
        this.notificationService = useService("notification");
        this.dialogService = useService("dialog");
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
            confirm: () => this.rpc(`${this.manageRoomUrl}/booking/${bookingId}/delete`),
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
    editBooking(bookingId, name, start, end) {
        this.rpc(`${this.manageRoomUrl}/booking/${bookingId}/update`, {
            name,
            start_datetime: serializeDateTime(start),
            stop_datetime: serializeDateTime(end),
        });
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

    /**
     * Load the existing bookings for the room.
     * New bookings will be received through the busService.
     */
    async loadBookings() {
        const bookings = await this.rpc(`${this.manageRoomUrl}/get_existing_bookings`);
        for (const booking of bookings) {
            this.addBooking(booking);
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
     * Schedule a booking for the given time range
     * @param {String} name
     * @param {luxon.DateTime} start
     * @param {luxon.DateTime} end
     */
    scheduleBooking(name, start, end) {
        this.resetBookingForm();
        this.rpc(`${this.manageRoomUrl}/booking/create`, {
            name: name || _t("Public Booking"),
            start_datetime: serializeDateTime(start),
            stop_datetime: serializeDateTime(end),
        });
    }

    //----------------------------------------------------------------------
    // Bus Methods
    //----------------------------------------------------------------------

    /**
     * Add a booking to the list of bookings, keeping the list sorted by start date
     * @param {Object} newBooking
     * @param {Number} newBooking.id
     * @param {String} newBooking.start_datetime
     * @param {String} newBooking.stop_datetime
     * @param {String} newBooking.name
     */
    addBooking(newBooking) {
        newBooking = {
            id: newBooking.id,
            name: newBooking.name,
            interval: luxon.Interval.fromDateTimes(
                deserializeDateTime(newBooking.start_datetime),
                deserializeDateTime(newBooking.stop_datetime),
            ),
        };
        // Do not add bookings that are already finished
        if (newBooking.interval.end < this.now) {
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
        // Leave form view if booking being edited has been deleted
        if (this.state.bookingToEdit?.id === bookingId) {
            this.resetBookingForm();
            this.notificationService.add(_t("The booking you were editing has been deleted."));
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
