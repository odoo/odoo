/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Activity } from "./activity";

export class ActivityList extends Component {
    static template = "mail.activity_list";
    static props = ["activities"];
    static components = { Activity };

    setup() {
        this.state = useState({
            isOpen: true,
        });
    }

    toggleList() {
        this.state.isOpen = !this.state.isOpen;
    }
}
