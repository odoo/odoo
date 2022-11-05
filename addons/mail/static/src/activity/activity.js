/** @odoo-module */

import { Component, useState } from "@odoo/owl";

const { DateTime } = luxon;

export class Activity extends Component {
    static template = "mail.activity";
    static props = ["data"];

    setup() {
        this.state = useState({
            showDetails: false,
        });
        const today = DateTime.now().startOf("day");
        const date = DateTime.fromISO(this.props.data.date_deadline);
        this.delay = date.diff(today, "days").days;
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }
}
