import { Component, useProps, t, xml } from "@odoo/owl";

const NO_OP = () => {};

export class Switch extends Component {
    props = useProps({
        value: t.boolean().optional(),
        extraClasses: t.string().optional(),
        disabled: t.boolean().optional(),
        id: t.string().optional(),
        labelIcon: t.string().optional(),
        labelIconClass: t.string().optional(),
        label: t.string().optional(),
        description: t.string().optional(),
        onChange: t.function().optional(() => NO_OP),
    });
    static template = xml`
    <label class="o_switch" t-att-class="this.props.extraClasses" t-att-for="this.props.id">
        <input type="checkbox"
                name="switch"
                t-att-id="this.props.id"
                class="visually-hidden"
                t-att-checked="this.props.value"
                t-att-disabled="this.props.disabled"
                t-on-change="(ev) => this.props.onChange(ev.target.checked)"
                t-on-keyup="this.onKeyup"/>
        <span class="oi oi-filled"/>
        <i t-if="this.props.labelIcon" class="oi ms-2" t-att-class="this.props.labelIconClass" t-att-data-icon="this.props.labelIcon"/>
        <span t-if="this.props.label" t-out="this.props.label" class="ms-2"/>
        <span t-if="this.props.description" class="text-muted ms-2" t-out="this.props.description"/>
    </label>
    `;

    /**
     * @param {KeyboardEvent} ev
     */
    onKeyup(ev) {
        // "Enter" is not a default on checkboxes, but as the switch doesn't
        // look like a checkbox anymore, we support it.
        if (ev.key === "Enter") {
            ev.currentTarget.checked = !ev.currentTarget.checked;
            this.props.onChange(ev.currentTarget.checked);
        }
    }
}
