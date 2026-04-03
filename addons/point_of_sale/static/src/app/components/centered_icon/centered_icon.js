import { Component, xml } from "@odoo/owl";

export class CenteredIcon extends Component {
    static props = {
        icon: String,
        icon_class: { type: String, optional: true },
        text: { type: String, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };
    static template = xml`
        <div t-attf-class="{{this.props.class}} d-flex flex-column align-items-center justify-content-center">
            <i t-attf-class="oi {{this.props.icon_class}}" t-att-data-icon="this.props.icon" role="img" />
            <h3 t-if="this.props.text" t-out="this.props.text" class="w-75 mt-2 text-center"/>
        </div>
    `;
}
