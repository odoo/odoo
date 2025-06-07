import { Component, xml } from "@odoo/owl";

export class CenteredIcon extends Component {
    static props = {
        icon: String,
        text: { type: String, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };
    static template = xml`
        <div t-attf-class="{{props.class}} d-flex flex-column align-items-center justify-content-center">
            <i t-attf-class="fa {{props.icon}}" role="img" />
            <h3 t-if="props.text" t-esc="props.text" class="w-75 mt-2 text-center"/>
        </div>
    `;
}
