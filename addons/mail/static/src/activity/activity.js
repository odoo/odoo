/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class Activity extends Component {
    static template = "mail.activity";
    static props = ["data", "reload?"];

    setup() {
        this.orm = useService("orm");
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

    async unlink() {
        await this.orm.unlink("mail.activity", [this.props.data.id]);
        if (this.props.reload) {
            this.props.reload();
        }
    }
}
