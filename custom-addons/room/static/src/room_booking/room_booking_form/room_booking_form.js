/** @odoo-module **/

import { scrollTo } from "@web/core/utils/scrolling";

import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";

export class RoomBookingForm extends Component {
    static template = "room.RoomBookingForm";
    static props = {
        createBooking: Function,
        bookings: Object,
        bookingToEdit: { type: Object, optional: true },
        cancel: Function,
        editBooking: Function,
        bookingName: { type: String, optional: true },
    };

    setup() {
        this.root = useRef("root");
        // If editing the current booking, show the current date as start otherwise the start
        // time slot would be hidden and we would not be able to change the start date
        this.state = useState({
            selectedDay: this.props.bookingToEdit
                ? luxon.DateTime.max(
                      this.props.bookingToEdit.interval.start.startOf("day"),
                      this.today,
                  )
                : this.today,
            bookingStart: this.props.bookingToEdit
                ? luxon.DateTime.max(this.props.bookingToEdit.interval.start, luxon.DateTime.now())
                : undefined,
            bookingEnd: this.props.bookingToEdit?.interval.end,
            bookingName: this.props.bookingToEdit?.name || this.props.bookingName,
        });

        /**
         * View the selected booking to edit
         */
        onWillUpdateProps((nextProps) => {
            if (nextProps.bookingToEdit !== this.props.bookingToEdit) {
                // If editing the current booking, show the current date as start otherwise the
                // start time slot would be hidden and we would not be able to change the start
                // date
                this.state.selectedDay = luxon.DateTime.max(
                    nextProps.bookingToEdit.interval.start.startOf("day"),
                    this.today,
                );
                this.state.bookingStart = luxon.DateTime.max(
                    nextProps.bookingToEdit.interval.start,
                    luxon.DateTime.now(),
                );
                this.state.bookingEnd = nextProps.bookingToEdit.interval.end;
                this.state.bookingName = nextProps.bookingToEdit.name;
            }
        });

        /**
         * Show the selected start or the "8am" slot at the top of the scheduler when changing day
         */
        useEffect(
            () => {
                const slot = this.root.el.querySelector(
                    `#slot${
                        this.state.bookingStart?.startOf("day").equals(this.state.selectedDay)
                            ? this.state.bookingStart.toFormat("HHmm")
                            : "0800"
                    }`,
                );
                if (slot) {
                    scrollTo(slot, { isAnchor: true });
                }
            },
            () => [this.state.selectedDay],
        );
    }

    //----------------------------------------------------------------------
    // Formats
    //----------------------------------------------------------------------

    get dayFormat() {
        return { weekday: "short", day: "numeric" };
    }

    get durationFormat() {
        return "h:mm";
    }

    get monthFormat() {
        return { year: "numeric", month: "long" };
    }

    get timeFormat() {
        return luxon.DateTime.TIME_SIMPLE;
    }

    //----------------------------------------------------------------------
    // Getters
    //----------------------------------------------------------------------

    /**
     * Return the bookings grouped by date.
     * This getter is a fix allowing the view to be reactive to booking updates received through
     * the bus.
     */
    get bookingsByDate() {
        return this.computeBookingsByDate(this.props.bookings, this.props.bookingToEdit?.id);
    }

    /**
     * Return the formatted month of the selected week.
     */
    get formattedMonth() {
        return this.weekInterval.toLocaleString(this.monthFormat);
    }

    /**
     * Compute the slots to display given the selected date, booking start and booking end.
     * Each slot represents an interval of 30 minutes.
     * Slots are objects with the following properties:
     * - {luxon.DateTime} start: start datetime of the slot
     * - {Boolean} isInSelectedInterval: if the slot is between the selected start and end dates
     * - {Boolean} canBeEndDate: if the slot can be selected as the end date
     * - {Boolean} isBooked: if the slot is already booked
     * - {String} description: Description to show in the slot the duration of the booking for
     *            the slots that can be selected as end date
     */
    get slots() {
        const intervals = [];
        const isToday = this.state.selectedDay.equals(this.today);
        // If the day selected is the current day, the first slot starts at the current time
        if (isToday) {
            let firstSlotTime = luxon.DateTime.now();
            if (this.state.bookingStart && this.state.bookingStart < firstSlotTime) {
                // Make sure that the selected start is shown
                firstSlotTime = this.state.bookingStart;
            }
            intervals.push(
                luxon.Interval.fromDateTimes(
                    firstSlotTime,
                    firstSlotTime
                        .plus({ minutes: 30 - (firstSlotTime.minute % 30) })
                        .startOf("minute"),
                ),
            );
        }
        // Fill with remaining intervals of the day, or with all intervals of the day
        const remainingInterval = luxon.Interval.fromDateTimes(
            intervals[0]?.end || this.state.selectedDay,
            this.state.selectedDay.plus({ day: 1 }),
        );
        intervals.push(...remainingInterval.splitBy({ minutes: 30 }));

        const bookings = this.bookingsByDate[this.state.selectedDay.toISODate()] || [];
        let bookingIdx = 0;
        let isBooked = false;
        let isInSelectedInterval = false;
        let canBeEndDate = false;
        // Bookings created from backend could span several days, so we need to make
        // sure that all slots between the start and end are marked as selected,
        // even if the start is not in the selected day
        if (
            this.props.bookingToEdit &&
            this.props.bookingToEdit.interval.start < this.state.selectedDay &&
            this.props.bookingToEdit.interval.end > this.state.selectedDay
        ) {
            isInSelectedInterval = true;
            canBeEndDate = true;
        }
        const slots = [];
        for (const interval of intervals) {
            const slot = {
                start: interval.start,
                isInSelectedInterval,
                canBeEndDate,
            };
            if (this.state.bookingEnd && interval.contains(this.state.bookingEnd)) {
                // Slot is the selected end (first condition in case start and stop are
                // in the same slot)
                isInSelectedInterval = false;
            } else if (this.state.bookingStart && interval.contains(this.state.bookingStart)) {
                // Slot is the selected start
                slot.isInSelectedInterval = true;
                // Following slots until the next booking can be selected as end date
                canBeEndDate = true;
                // Following slots until the selected end date are in the selected interval
                isInSelectedInterval = Boolean(this.state.bookingEnd);
            } else if (canBeEndDate && !isInSelectedInterval) {
                // Show the duration of the booking if this slot was used as end date
                slot.description = interval.start
                    .diff(this.state.bookingStart)
                    .toFormat(this.durationFormat);
            }
            if (bookings[bookingIdx]?.overlaps(interval) && !isBooked) {
                // Slot contains the start of a booking
                isBooked = true;
                canBeEndDate = false;
            }
            slot.isBooked = isBooked;
            if (isBooked && interval.end >= bookings[bookingIdx].end) {
                // Slot contains the end of the booking
                isBooked = false;
                bookingIdx++;
            }
            slots.push(slot);
        }
        // Add midnight slot if the last time slot can be used as end of the booking
        if (this.state.bookingStart && canBeEndDate) {
            const midnight = this.state.selectedDay.plus({ day: 1 });
            const isEnd = this.state.bookingEnd?.equals(midnight);
            slots.push({
                start: midnight,
                canBeEndDate,
                isInSelectedInterval: isEnd,
                description: isEnd
                    ? false
                    : midnight.diff(this.state.bookingStart).toFormat(this.durationFormat),
            });
        }
        return slots;
    }

    get today() {
        return luxon.DateTime.now().startOf("day");
    }

    get weekInterval() {
        return luxon.Interval.fromDateTimes(
            this.state.selectedDay.startOf("week"),
            this.state.selectedDay.endOf("week"),
        );
    }

    /**
     * Return the days (as intervals) of the selected week
     */
    get weekIntervalDays() {
        return this.weekInterval.splitBy({ day: 1 });
    }

    //----------------------------------------------------------------------
    // Methods
    //----------------------------------------------------------------------

    /**
     * Return the bookings grouped by date
     * @returns {Object} bookingsByDate
     */
    computeBookingsByDate(bookings, bookingToEditId) {
        return bookings.reduce((bookingsByDate, booking) => {
            // If editing a booking, do not consider it as booked
            if (bookingToEditId === booking.id) {
                return bookingsByDate;
            }
            const intervals = [];
            let { start, end } = booking.interval;
            if (start.startOf("day").equals(end.startOf("day"))) {
                intervals.push(booking.interval);
            } else {
                // Case a user creates a booking spanning multiple days from backend
                while (start.startOf("day") < end.startOf("day")) {
                    const nextDay = start.plus({ days: 1 }).startOf("day");
                    intervals.push(luxon.Interval.fromDateTimes(start, nextDay));
                    start = nextDay;
                }
                intervals.push(luxon.Interval.fromDateTimes(start, end));
            }
            for (const interval of intervals) {
                const date = interval.start.toISODate();
                if (!(date in bookingsByDate)) {
                    bookingsByDate[date] = [];
                }
                bookingsByDate[date].push(interval);
            }
            return bookingsByDate;
        }, {});
    }

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Create a new booking or edit the bookingToEdit if one is given.
     * If we are editing the ongoing booking and only changed the end date,
     * we keep the start date as it is (instead of replacing it with the
     * "selected" start which is the first slot since the real start slot is
     * not shown anymore)
     */
    confirm() {
        if (this.props.bookingToEdit) {
            this.props.editBooking(
                this.props.bookingToEdit.id,
                this.state.bookingName,
                this.props.bookingToEdit.interval.start < luxon.DateTime.now() &&
                    this.state.bookingStart < luxon.DateTime.now()
                    ? this.props.bookingToEdit.interval.start
                    : this.state.bookingStart,
                this.state.bookingEnd,
            );
        } else {
            this.props.createBooking(
                this.state.bookingName,
                this.state.bookingStart,
                this.state.bookingEnd,
            );
        }
    }

    /**
     * Show the slots for the week following the current one
     */
    onNextWeekClick() {
        this.state.selectedDay = this.state.selectedDay.plus({ week: 1 });
    }

    /**
     * Show the slots for the week preceding the current one
     */
    onPreviousWeekClick() {
        const day = this.state.selectedDay.minus({ week: 1 });
        this.state.selectedDay = day < this.today ? this.today : day;
    }

    /**
     * Handle a click on a slot.
     * @param {Object} slot
     * @param {luxon.DateTime} slot.start
     * @param {Boolean} slot.canBeEndDate
     * @param {Boolean} slot.isBooked
     */
    onSlotClick(slot) {
        if (!this.state.bookingStart) {
            if (!slot.isBooked) {
                // Select start date
                this.state.bookingStart = slot.start;
            }
        } else {
            if (slot.start.equals(this.state.bookingStart)) {
                // Clear selected dates
                this.state.bookingStart = null;
                this.state.bookingEnd = null;
            } else if (slot.canBeEndDate) {
                if (this.state.bookingEnd && slot.start.equals(this.state.bookingEnd)) {
                    // Clear selected end date
                    this.state.bookingEnd = null;
                } else {
                    // Select end date
                    this.state.bookingEnd = slot.start;
                }
            } else if (!slot.isBooked) {
                // Keep end date if choosing a start date before the current
                // one and if there is no booking between the two
                if (
                    !slot.start.hasSame(this.state.bookingStart, "day") ||
                    slot.start > this.state.bookingStart ||
                    this.bookingsByDate[this.state.selectedDay.toISODate()]?.some((booking) =>
                        booking.overlaps(
                            luxon.Interval.fromDateTimes(slot.start, this.state.bookingStart),
                        ),
                    )
                ) {
                    this.state.bookingEnd = null;
                }
                // Select other start
                this.state.bookingStart = slot.start;
            }
        }
    }
}
