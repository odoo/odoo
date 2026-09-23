/** @odoo-module native */
import { Component, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Counter extends Component {
    static selector = "#wrapwrap h1";
    static template = xml`
        <div class="btn btn-primary" t-on-click="increment">
            Counter. Value=<t t-out="state.value"/>
        </div>`;
    static props = {};

    setup() {
        this.state = useState({ value: 1 });
        this.notification = useService("notification");
    }

    increment(ev) {
        ev.stopPropagation();
        this.state.value++;
        this.notification.add(`Example of a service: ${this.state.value}`);
    }
}
