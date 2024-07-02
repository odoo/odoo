//-----------------------------------------------------------------------------
// ! PRODUCTION CODE: DO NOT TOUCH
//-----------------------------------------------------------------------------

import { Component, useState, xml } from "@odoo/owl";

export class Counter extends Component {
    static props = {};
    static template = xml`
        <button
            class="btn o-counter"
            t-on-click="onClick"
            t-on-input="onInput"
        >
            Count: <input type="text" t-att-value="state.count" />
        </button>
    `;

    setup() {
        this.state = useState({ count: 0 });
    }

    onClick() {
        this.state.count++;
    }

    /**
     * @param {InputEvent} ev
     */
    onInput(ev) {
        this.state.count = Number(ev.target.value) || 0;
    }
}
