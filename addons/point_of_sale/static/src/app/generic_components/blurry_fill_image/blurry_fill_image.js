import { Component, xml } from "@odoo/owl";

export class BlurryFillImage extends Component {
    static props = {
        imageUrl: String,
        style: { type: String, optional: true },
    };
    static defaultProps = {
        style: "min-height: 6rem; max-height: 6rem;",
    };
    static template = xml`
        <div t-if="props.imageUrl" t-att-style="props.style" class="blurry-fill-image-frame">
            <div class="blur" t-attf-style="background-image: url('{{props.imageUrl}}')" />
            <img t-att-src="props.imageUrl"/>
        </div>
    `;
}
