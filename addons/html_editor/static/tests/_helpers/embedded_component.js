import { Component, useRef, useState, xml } from "@odoo/owl";

export class Counter extends Component {
    static props = [];
    static template = xml`
        <span t-ref="root" class="counter" t-on-click="increment">Counter:<t t-esc="state.value"/></span>`;

    state = useState({ value: 0 });
    ref = useRef("root");

    increment() {
        this.state.value++;
    }
}

export function embedding(name, Component, getProps) {
    return {
        name,
        Component,
        getProps,
    };
}
