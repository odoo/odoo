import { Component, onWillStart, xml } from "@odoo/owl";

export class Img extends Component {
    static props = {
        src: String,
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        alt: { type: String, optional: true },
        attrs: { type: Object, optional: true },
    };
    static template = xml`<img t-att-src="props.src" t-att-class="props.class" t-att-style="props.style" t-att-alt="props.alt" t-att="props.attrs"/>`;
    setup() {
        onWillStart(async () => this.loadImage());
    }

    loadImage() {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve({ status: "loaded" });
            img.onerror = () => resolve({ status: "error" });
            img.src = this.props.src;
        });
    }
}
