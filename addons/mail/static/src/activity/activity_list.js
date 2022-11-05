/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Activity } from "./activity";

export class ActivityList extends Component {
    setup() {
        this.state = useState({
            isOpen: true,
        });
    }

    toggleList() {
        this.state.isOpen = !this.state.isOpen;
    }
}

Object.assign(ActivityList, {
    components: { Activity },
    props: ["activities", "reload"],
    template: "mail.activity_list",
});
