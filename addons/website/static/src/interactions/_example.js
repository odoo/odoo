import { useState } from "@web/owl2/utils";
// import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// -----------------------------------------------------------------------------
// Example of mounted component
// -----------------------------------------------------------------------------
export class Counter extends Component {
    static selector = "#wrapwrap h1";
    static template = xml`
        <div class="btn btn-primary" t-on-click="this.increment">
            Counter. Value=<t t-out="this.state.value"/>
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

/*
registry.category("public.interactions").add("website.counter", Counter);
*/
