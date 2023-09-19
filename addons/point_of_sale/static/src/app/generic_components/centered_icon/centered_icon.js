/** @odoo-module */

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
        <div t-attf-class="{{props.class}} d-flex flex-column align-items-center justify-content-center h-100 w-100  text-muted">
            <i t-attf-class="fa {{props.icon}}" role="img" />
            <h3 t-if="props.text" t-esc="props.text" class="mt-2"/>
        </div>
    `;
}
