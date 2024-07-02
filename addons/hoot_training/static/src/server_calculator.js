//-----------------------------------------------------------------------------
// ! PRODUCTION CODE: DO NOT TOUCH
//-----------------------------------------------------------------------------

import { Component, useRef, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ServerCalculator extends Component {
    static props = {};
    static template = xml`
        <div t-ref="inputs">
            <input />
            <input />
        </div>
        <button t-on-click="add">+</button>
        <button t-on-click="mult">*</button>
        <ul class="results">
            <t t-foreach="results" t-as="result" t-key="result_index">
                <li t-esc="result" />
            </t>
        </ul>
    `;

    setup() {
        this.inputsRef = useRef("inputs");
        this.orm = useService("orm");
        this.results = useState([]);
    }

    async add() {
        const response = await fetch(`/calculator/add`, {
            body: JSON.stringify(this.getValues()),
            headers: { "Content-Type": "application/json" },
        });
        const { result } = await response.json();

        this.results.push(result);
    }

    getValues() {
        return [...(this.inputsRef.el?.querySelectorAll("input") || [])].map(
            (i) => Number(i.value) || 0
        );
    }

    async mult() {
        const result = await this.orm.call("ir.calculator", "multiply", this.getValues());

        this.results.push(result);
    }
}
