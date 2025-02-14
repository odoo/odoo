import { Component, xml } from "@odoo/owl";

export class DocLoadingIndicator extends Component {
    static template = xml`
        <div t-if="!props.isLoaded" class="o-doc-load-wrapper o-fade-in position-relative h-100 w-100 bg-2 rounded">
            <div class="o-doc-load-activity position-absolute h-100"></div>
        </div>
        <div t-else="" t-att-class="props.class">
            <t t-slot="default"/>
        </div>
    `;

    static components = {};
    static props = {
        isLoaded: { type: Boolean },
        class: { type: String, optional: true },
        slots: true,
    };

    static defaultProps = {
        class: "",
    };
}
