/** @odoo-module **/

import { useInterval } from "@room/room_booking/useInterval";

import { Component, onWillUpdateProps, useState, xml } from "@odoo/owl";

export class RoomBookingRemainingTime extends Component {
    static template = xml`
        <div class="o_room_remaining_time rounded py-3 bg-black-25 display-4 text-center text-white"
             t-out="state.remainingTime.toFormat('hh:mm:ss')"/>
    `;
    static props = {
        endTime: { type: Object },
    };

    setup() {
        this.state = useState({ remainingTime: this.props.endTime.diffNow() });
        // Update the remaining time every second
        useInterval(() => {
            const remainingTime = this.props.endTime.diffNow();
            // Prevent flicker (could show -1s for a split second)
            if (remainingTime >= 0) {
                this.state.remainingTime = remainingTime;
            }
        }, 1000);
        // When there are 2 consecutive bookings, make sure the remaining time is updated
        // immediately (because the booking title and sidebar update immediately)
        onWillUpdateProps((nextProps) => {
            this.state.remainingTime = nextProps.endTime.diffNow();
        });
    }
}
