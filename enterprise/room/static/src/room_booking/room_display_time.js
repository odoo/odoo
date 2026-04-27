/** @odoo-module **/

import { useInterval } from "@room/room_booking/useInterval";

import { Component, useState, xml } from "@odoo/owl";

export class RoomDisplayTime extends Component {
    static template = xml`<div class="d-flex flex-column justify-content-center"><span class="display-6" t-out="state.currentTime.toFormat('T')"/><span class="smaller" t-out="state.currentTime.toFormat('DDDD')"/></div>`;
    static props = {};

    setup() {
        this.state = useState({ currentTime: luxon.DateTime.now() });
        // Update the current time every second
        useInterval(() => (this.state.currentTime = luxon.DateTime.now()), 1000);
    }
}
