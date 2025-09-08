import { Component, useState } from "@odoo/owl";

export class Counter extends Component {
    static template = "awesome_dashboard.Counter";

    setup() {
        this.state = useState({ value: 1 });
    }

    increment() {
        this.state.value++;
    }

    decrement() {
        this.state.value--;
    }
}