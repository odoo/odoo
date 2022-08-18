/** @odoo-module **/

const { Component, xml } = owl;

const NO_OP = () => {};

export class Switch extends Component {
    setup() {
        this.extraClasses = this.props.extraClasses ? ` ${this.props.extraClasses}` : '';
    }
}
Switch.props = {
    value: Boolean,
    extraClasses: String,
    label: {type: String, optional: true},
    onChange: { Function, optional: true },
};
Switch.defaultProps = {
    onChange: NO_OP,
};
Switch.template = xml`
<label t-att-class="'o_switch' + extraClasses">
    <input type="checkbox" t-att-checked="props.value" t-on-change="(ev) => props.onChange(ev.target.checked)"/>
    <span/>
    <span t-if="props.label" t-esc="props.label" class="ms-2"/>
</label>
`;
