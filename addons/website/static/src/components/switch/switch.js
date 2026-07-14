/** @odoo-module **/

import { Component, xml } from "@odoo/owl";

const NO_OP = () => {};

export class Switch extends Component {
    static props = {
        value: Boolean,
        extraClasses: String,
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        onChange: { Function, optional: true },
    };
    static defaultProps = {
        onChange: NO_OP,
    };
    static template = xml`
    <label t-att-class="'o_switch' + extraClasses">
        <input type="checkbox" t-att-checked="props.value" t-att-disabled="props.disabled" t-on-change="(ev) => props.onChange(ev.target.checked)"/>
        <span/>
        <span t-if="props.label" t-esc="props.label" class="ms-2"/>
    </label>
    `;

    setup() {
        this.extraClasses = this.props.extraClasses ? ` ${this.props.extraClasses}` : '';
    }
}
